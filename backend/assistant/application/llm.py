"""LLM client for non-agent uses (OCR, UOM classification, enrichment).

generate_text — uses PydanticAI Agent.run() for retries and provider resolution.
generate_with_image / generate_with_pdf — raw Anthropic SDK (multimodal APIs).
"""

import asyncio
import base64
import logging

from assistant.agents.core.model_registry import get_model_name
from shared.infrastructure.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_AVAILABLE,
    ANTHROPIC_MODEL,
)

logger = logging.getLogger(__name__)


def _get_anthropic_client():
    """Return sync Anthropic client for multimodal calls (image/PDF)."""
    if not ANTHROPIC_AVAILABLE:
        return None
    try:
        import anthropic

        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


async def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    model_id: str | None = None,
) -> str | None:
    """One-shot text generation using PydanticAI — retries, cost-aware.

    When model_id is provided, uses that model. Otherwise uses infra:synthesis.
    Automatically falls back to OpenRouter when Anthropic is overloaded.
    Returns None on failure (never raises).
    """
    try:
        from pydantic_ai import Agent

        from assistant.agents.core.model_registry import get_fallback_model

        model = model_id or get_model_name("infra:synthesis")
        agent: Agent[None, str] = Agent(model, system_prompt=system_instruction or "")
        try:
            result = await asyncio.wait_for(agent.run(prompt), timeout=30)
            return result.output
        except Exception as primary_err:
            err_str = str(primary_err).lower()
            is_overloaded = any(
                k in err_str for k in ("529", "overload", "service unavailable", "capacity")
            )
            if not is_overloaded:
                raise
            fallback = get_fallback_model(model)
            if not fallback:
                raise
            logger.info("generate_text: primary overloaded, trying fallback %s", fallback)
            result = await asyncio.wait_for(agent.run(prompt, model=fallback), timeout=30)
            return result.output
    except Exception as e:
        logger.warning("generate_text failed: %s", e)
        return None


_sync_pool = None
_sync_pool_lock = None


def _get_sync_pool():
    """Return the module-level thread pool for sync→async bridging.

    Lazily initialized so import-time has no side effects.
    Capped at 4 workers — enough for concurrent OCR/classification requests
    without unbounded thread growth.
    """
    global _sync_pool, _sync_pool_lock
    import concurrent.futures
    import threading

    if _sync_pool_lock is None:
        _sync_pool_lock = threading.Lock()
    with _sync_pool_lock:
        if _sync_pool is None:
            _sync_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=4,
                thread_name_prefix="llm-sync",
            )
    return _sync_pool


def generate_text_sync(
    prompt: str,
    system_instruction: str | None = None,
) -> str | None:
    """Synchronous generate_text for injection into sync-callable consumers.

    Used by product_intelligence and uom_classifier which accept a sync
    (prompt, system) -> str|None callable. Runs the async generate_text
    via asyncio.run() in a shared background thread pool (max 4 workers).
    """

    async def _inner():
        return await generate_text(prompt, system_instruction)

    try:
        future = _get_sync_pool().submit(asyncio.run, _inner())
        return future.result(timeout=35)
    except Exception as e:
        logger.warning("generate_text_sync failed: %s", e)
        return None


def _detect_media_type(image_bytes: bytes) -> str:
    """Detect image media type from bytes header."""
    if image_bytes[:4] == b"\x89PNG":
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def generate_with_image(
    prompt: str,
    image_bytes: bytes,
    system_instruction: str | None = None,
) -> str:
    """Generate from image via raw Anthropic SDK. Raises ValueError on failure."""
    client = _get_anthropic_client()
    if not client:
        raise ValueError("LLM not configured. Set ANTHROPIC_API_KEY in backend/.env")
    media_type = _detect_media_type(image_bytes)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    try:
        kwargs = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        if system_instruction:
            kwargs["system"] = system_instruction
        response = client.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        err = str(e).lower()
        if "rate" in err or "429" in err or "overloaded" in err:
            raise ValueError("Anthropic rate limit hit. Try again in a minute.") from e
        if "authentication" in err or "api_key" in err:
            raise ValueError("Invalid ANTHROPIC_API_KEY. Check backend/.env") from e
        if "model" in err or "invalid_request" in err or "not_found" in err or "400" in err:
            raise ValueError(
                f"Anthropic model error (model={ANTHROPIC_MODEL}): {e}. "
                "Check ANTHROPIC_MODEL in your environment."
            ) from e
        raise ValueError(f"Anthropic API error: {e}") from e


def generate_with_pdf(
    prompt: str,
    pdf_path: str,
    system_instruction: str | None = None,
) -> str:
    """Generate from PDF via Anthropic native PDF support. Raises ValueError on failure."""
    client = _get_anthropic_client()
    if not client:
        raise ValueError("LLM not configured. Set ANTHROPIC_API_KEY in backend/.env")
    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
    try:
        kwargs = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "betas": ["pdfs-2024-09-25"],
        }
        if system_instruction:
            kwargs["system"] = system_instruction
        response = client.beta.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        err = str(e).lower()
        if "rate" in err or "429" in err or "overloaded" in err:
            raise ValueError("Anthropic rate limit hit. Try again in a minute.") from e
        if "authentication" in err or "api_key" in err:
            raise ValueError("Invalid ANTHROPIC_API_KEY. Check backend/.env") from e
        if "model" in err or "invalid_request" in err or "not_found" in err or "400" in err:
            raise ValueError(
                f"Anthropic model error (model={ANTHROPIC_MODEL}): {e}. "
                "Check ANTHROPIC_MODEL in your environment."
            ) from e
        raise ValueError(f"Anthropic API error: {e}") from e
