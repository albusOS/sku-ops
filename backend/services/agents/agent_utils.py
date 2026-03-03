"""Shared utilities for all specialist agents."""
import asyncio
import logging
import random
from enum import Enum

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 45
_MAX_RETRIES = 3
_BASE_DELAY = 1.0   # seconds
_MAX_DELAY = 16.0   # seconds


# ── Error classification ─────────────────────────────────────────────────────

class _ErrorKind(str, Enum):
    RATE_LIMIT  = "rate_limit"   # 429 — retriable, backoff, honour Retry-After
    TIMEOUT     = "timeout"      # network or wait_for timeout — retriable
    NETWORK     = "network"      # connection errors — retriable
    SERVER      = "server"       # 500/503/overload — retriable
    MODEL_ERROR = "model_error"  # thinking budget, bad model_settings — drop settings + retry
    AUTH        = "auth"         # 401/403 — NOT retriable
    VALIDATION  = "validation"   # 400 — NOT retriable
    UNKNOWN     = "unknown"      # NOT retriable


def _classify(e: Exception) -> tuple[_ErrorKind, bool, float | None]:
    """Return (kind, is_retriable, retry_after_seconds)."""
    s = str(e).lower()
    t = type(e).__name__.lower()

    # Extract Retry-After header when available (Anthropic sends this on 429)
    retry_after: float | None = None
    resp = getattr(e, "response", None)
    if resp is not None:
        hdrs = getattr(resp, "headers", {})
        ra = hdrs.get("retry-after") or hdrs.get("x-ratelimit-reset-requests")
        if ra:
            try:
                retry_after = float(ra)
            except (ValueError, TypeError):
                pass

    if any(k in t for k in ("ratelimit", "rate_limit")) or \
       any(k in s for k in ("rate limit", "429", "too many requests", "ratelimit")):
        return _ErrorKind.RATE_LIMIT, True, retry_after

    if isinstance(e, asyncio.TimeoutError) or "timeout" in t or "timeout" in s:
        return _ErrorKind.TIMEOUT, True, None

    if any(k in t for k in ("connection", "network", "connect")) or \
       any(k in s for k in ("connection error", "network", "socket", "unreachable", "refused", "reset by peer")):
        return _ErrorKind.NETWORK, True, None

    if any(k in s for k in ("500", "503", "502", "overload", "internal server", "service unavailable", "bad gateway")):
        return _ErrorKind.SERVER, True, None

    # Thinking/model config issues — drop settings and retry
    if any(k in s for k in ("thinking", "budget", "extended thinking", "model_settings")):
        return _ErrorKind.MODEL_ERROR, True, None

    if any(k in t for k in ("auth", "permission")) or \
       any(k in s for k in ("401", "403", "unauthorized", "forbidden", "invalid api key", "authentication")):
        return _ErrorKind.AUTH, False, None

    if any(k in s for k in ("400", "bad request", "invalid request")) or "badrequest" in t:
        return _ErrorKind.VALIDATION, False, None

    return _ErrorKind.UNKNOWN, False, None


async def _backoff(attempt: int, retry_after: float | None) -> None:
    """Exponential backoff with ±25% jitter. Honours Retry-After when present."""
    if retry_after is not None:
        delay = min(retry_after, _MAX_DELAY)
    else:
        delay = min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)
    jitter = random.uniform(-delay * 0.25, delay * 0.25)
    await asyncio.sleep(max(0.1, delay + jitter))


# ── Agent runner ─────────────────────────────────────────────────────────────

async def run_agent(
    agent,
    user_message: str,
    *,
    msg_history,
    deps,
    model_id: str,
    model_settings: dict | None,
    timeout_seconds: int = AGENT_TIMEOUT_SECONDS,
    agent_name: str = "agent",
):
    """Run a PydanticAI agent with retry/backoff, error classification, and model fallback.

    Retry strategy (up to _MAX_RETRIES attempts on primary model):
    - rate_limit / network / timeout / server  → exponential backoff + jitter
    - model_error (thinking budget etc.)       → drop thinking settings, retry immediately
    - auth / validation                        → fail immediately, no retry

    After retries exhausted, automatically falls back to the other Anthropic model
    (Haiku ↔ Sonnet) as a last resort before raising.
    """
    from config import ANTHROPIC_MODEL, ANTHROPIC_OPUS_MODEL

    # Fallback: Sonnet → Opus (upgrade, not downgrade)
    fallback_model_id: str | None = ANTHROPIC_OPUS_MODEL if model_id == ANTHROPIC_MODEL else None

    active_settings = model_settings

    async def _run(mid: str, settings):
        return await asyncio.wait_for(
            agent.run(
                user_message,
                message_history=msg_history,
                deps=deps,
                model=f"anthropic:{mid}",
                model_settings=settings or None,
            ),
            timeout=timeout_seconds,
        )

    last_exc: Exception = RuntimeError(f"{agent_name}: no attempts made")

    for attempt in range(_MAX_RETRIES):
        try:
            return await _run(model_id, active_settings)
        except asyncio.TimeoutError:
            last_exc = RuntimeError(f"{agent_name} timed out after {timeout_seconds}s")
            kind, retriable, retry_after = _ErrorKind.TIMEOUT, True, None
        except Exception as e:
            last_exc = e
            kind, retriable, retry_after = _classify(e)

        if not retriable:
            logger.error(f"{agent_name} non-retriable {kind} on attempt {attempt + 1}: {last_exc}")
            raise last_exc

        # Thinking settings caused the model error → drop them and retry immediately
        if active_settings and kind == _ErrorKind.MODEL_ERROR:
            logger.warning(f"{agent_name} model_error with thinking settings, dropping and retrying: {last_exc}")
            active_settings = None
            continue

        if attempt < _MAX_RETRIES - 1:
            logger.warning(f"{agent_name} {kind} on attempt {attempt + 1}/{_MAX_RETRIES}, backing off: {last_exc}")
            await _backoff(attempt, retry_after)
        else:
            logger.warning(f"{agent_name} {kind} on final attempt {_MAX_RETRIES}/{_MAX_RETRIES}: {last_exc}")

    # Primary exhausted → try fallback model
    if fallback_model_id:
        logger.warning(f"{agent_name} primary {model_id} exhausted, falling back to {fallback_model_id}")
        try:
            return await _run(fallback_model_id, None)
        except asyncio.TimeoutError:
            raise RuntimeError(f"{agent_name} fallback {fallback_model_id} timed out after {timeout_seconds}s")
        except Exception as e:
            logger.error(f"{agent_name} fallback {fallback_model_id} also failed: {e}")
            raise e

    raise last_exc


# ── Pricing ───────────────────────────────────────────────────────────────────

_MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5":  {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":   {"input": 15.00, "output": 75.00},
}


def calc_cost(model: str, usage) -> float:
    key = next((k for k in _MODEL_PRICING if model.startswith(k)), None)
    if not key:
        return 0.0
    p = _MODEL_PRICING[key]
    return round((usage.input_tokens * p["input"] + usage.output_tokens * p["output"]) / 1_000_000, 6)


# ── History helpers ───────────────────────────────────────────────────────────

def build_message_history(history: list[dict] | None) -> list | None:
    """Convert text-only {role, content} pairs → PydanticAI ModelMessage list."""
    if not history:
        return None
    messages = []
    for h in history:
        content = (h.get("content") or "").strip()
        if not content:
            continue
        if h.get("role") == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=content)], model_name=None))
    return messages or None


def extract_text_history(messages) -> list[dict]:
    """Extract text-only turns from PydanticAI all_messages() for session storage."""
    out = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    text = part.content if isinstance(part.content, str) else ""
                    if text:
                        out.append({"role": "user", "content": text})
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart) and part.content:
                    out.append({"role": "assistant", "content": part.content})
    return out


def extract_tool_calls(messages) -> list[dict]:
    """Extract tool call names from PydanticAI all_messages()."""
    out = []
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    out.append({"tool": part.tool_name})
    return out
