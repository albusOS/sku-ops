"""LLM client for non-agent uses (OCR, UOM classification, enrichment).

generate_text         — PydanticAI Agent.run() with provider fallback.
generate_with_image   — OpenRouter (primary) or Anthropic SDK (fallback).
generate_with_pdf     — OpenRouter (primary) or Anthropic SDK (fallback).
"""

import asyncio
import base64
import concurrent.futures
import logging
import threading

import anthropic
from openai import OpenAI
from pydantic_ai import Agent

from assistant.agents.core.model_registry import get_fallback_model, get_model_name
from shared.infrastructure.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_AVAILABLE,
    ANTHROPIC_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_AVAILABLE,
    OPENROUTER_BASE_URL,
)

logger = logging.getLogger(__name__)

# Model used for multimodal calls (image / PDF parsing).
# OpenRouter uses the bare provider/model string; Anthropic SDK uses the bare model name.
_MULTIMODAL_OR_MODEL = "anthropic/claude-sonnet-4-6"


def _get_openrouter_client():
    """Return an OpenAI-compatible client pointed at OpenRouter."""
    if not OPENROUTER_AVAILABLE:
        return None
    try:
        return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    except ImportError:
        logger.warning("openai package not installed — cannot use OpenRouter for multimodal")
        return None


def _get_anthropic_client():
    """Return sync Anthropic client — fallback when OpenRouter is not configured."""
    if not ANTHROPIC_AVAILABLE:
        return None
    try:
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
    *,
    anthropic_direct: bool = False,
) -> str:
    """Generate from image.

    When anthropic_direct=True, always uses the Anthropic SDK (skips OpenRouter).
    Otherwise uses OpenRouter (primary) with Anthropic SDK fallback.
    Raises ValueError on failure.
    """
    media_type = _detect_media_type(image_bytes)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    if not anthropic_direct:
        or_client = _get_openrouter_client()
        if or_client:
            data_url = f"data:{media_type};base64,{image_data}"
            return _openrouter_vision(or_client, prompt, data_url, system_instruction)

    client = _get_anthropic_client()
    if not client:
        raise ValueError("LLM not configured. Set ANTHROPIC_API_KEY in backend/.env")
    return _anthropic_image(client, prompt, image_data, media_type, system_instruction)


def generate_with_pdf(
    prompt: str,
    pdf_path: str,
    system_instruction: str | None = None,
    *,
    anthropic_direct: bool = False,
) -> str:
    """Generate from PDF.

    When anthropic_direct=True, always uses the Anthropic SDK (skips OpenRouter).
    Otherwise uses OpenRouter (primary) with Anthropic SDK fallback.
    Raises ValueError on failure.
    """
    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    if not anthropic_direct:
        or_client = _get_openrouter_client()
        if or_client:
            data_url = f"data:application/pdf;base64,{pdf_data}"
            return _openrouter_vision(or_client, prompt, data_url, system_instruction)

    client = _get_anthropic_client()
    if not client:
        raise ValueError("LLM not configured. Set ANTHROPIC_API_KEY in backend/.env")
    return _anthropic_pdf(client, prompt, pdf_data, system_instruction)


# ---------------------------------------------------------------------------
# Provider-specific helpers
# ---------------------------------------------------------------------------


def _openrouter_vision(client, prompt: str, data_url: str, system: str | None) -> str:
    """Vision/PDF call via OpenRouter's OpenAI-compatible API."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompt},
            ],
        }
    )
    try:
        response = client.chat.completions.create(
            model=_MULTIMODAL_OR_MODEL,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        _raise_provider_error(e, "OpenRouter")


def _anthropic_image(
    client, prompt: str, image_data: str, media_type: str, system: str | None
) -> str:
    """Image call via raw Anthropic SDK."""
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
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        _raise_provider_error(e, "Anthropic")


def _anthropic_pdf(client, prompt: str, pdf_data: str, system: str | None) -> str:
    """PDF call via raw Anthropic SDK (native PDF beta)."""
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
        if system:
            kwargs["system"] = system
        response = client.beta.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        _raise_provider_error(e, "Anthropic")


def _raise_provider_error(e: Exception, provider: str) -> None:
    err = str(e).lower()
    if "rate" in err or "429" in err or "overloaded" in err:
        raise ValueError(f"{provider} rate limit hit. Try again in a minute.") from e
    if "authentication" in err or "api_key" in err or "unauthorized" in err:
        raise ValueError(f"Invalid {provider} API key. Check backend/.env") from e
    if "model" in err or "invalid_request" in err or "not_found" in err or "400" in err:
        raise ValueError(f"{provider} model error: {e}") from e
    raise ValueError(f"{provider} API error: {e}") from e
