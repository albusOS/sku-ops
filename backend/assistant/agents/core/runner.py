"""Agent execution — run loop with retry/backoff, error classification, and run logging."""

import asyncio
import contextlib
import logging
import random
import time
from enum import StrEnum

from assistant.agents.core.contracts import AgentConfig, AgentResult, UsageInfo
from assistant.agents.core.messages import (
    extract_text_history,
    extract_tool_calls,
    extract_tool_calls_detailed,
)
from assistant.agents.core.model_registry import (
    calc_cost,
    get_fallback_model,
    get_model_name,
)
from assistant.agents.core.validators import classify_intent, validate_response
from shared.infrastructure.config import (
    ANTHROPIC_AVAILABLE,
    OPENROUTER_AVAILABLE,
)
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.logging_config import (
    agent_name_var,
    operation_var,
    trace_id_var,
)
from shared.infrastructure.metrics import agent_run as record_agent_run
from shared.infrastructure.metrics import llm_usage, tool_call

logger = logging.getLogger(__name__)


def _db_assistant():
    return get_database_manager().assistant


AGENT_TIMEOUT_SECONDS = 60
_MAX_RETRIES = 3
_OVERLOAD_MAX_RETRIES = 1
_BASE_DELAY = 0.5  # seconds
_OVERLOAD_BASE_DELAY = 2.0  # shorter initial backoff — fail fast, switch to fallback
_MAX_DELAY = 15.0  # seconds


def get_agent_timeout(config: AgentConfig | None) -> int:
    """Return timeout seconds from config or global default."""
    if config and config.retry.timeout_seconds:
        return config.retry.timeout_seconds
    return AGENT_TIMEOUT_SECONDS


# ── Error classification ─────────────────────────────────────────────────────


class _ErrorKind(StrEnum):
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    SERVER = "server"
    OVERLOADED = "overloaded"
    MODEL_ERROR = "model_error"
    AUTH = "auth"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


def _classify(e: Exception) -> tuple[_ErrorKind, bool, float | None]:
    """Return (kind, is_retriable, retry_after_seconds)."""
    s = str(e).lower()
    t = type(e).__name__.lower()

    retry_after: float | None = None
    resp = getattr(e, "response", None)
    if resp is not None:
        hdrs = getattr(resp, "headers", {})
        ra = hdrs.get("retry-after") or hdrs.get("x-ratelimit-reset-requests")
        if ra:
            with contextlib.suppress(ValueError, TypeError):
                retry_after = float(ra)

    if any(k in t for k in ("ratelimit", "rate_limit")) or any(
        k in s for k in ("rate limit", "429", "too many requests", "ratelimit")
    ):
        return _ErrorKind.RATE_LIMIT, True, retry_after

    if isinstance(e, asyncio.TimeoutError) or "timeout" in t or "timeout" in s:
        return _ErrorKind.TIMEOUT, True, None

    if any(k in t for k in ("connection", "network", "connect")) or any(
        k in s
        for k in (
            "connection error",
            "network",
            "socket",
            "unreachable",
            "refused",
            "reset by peer",
        )
    ):
        return _ErrorKind.NETWORK, True, None

    if any(k in s for k in ("529", "overload", "service unavailable", "capacity")):
        return _ErrorKind.OVERLOADED, True, retry_after

    if any(k in s for k in ("500", "502", "503", "internal server", "bad gateway")):
        return _ErrorKind.SERVER, True, None

    if any(k in s for k in ("thinking", "budget", "extended thinking", "model_settings")):
        return _ErrorKind.MODEL_ERROR, True, None

    if any(k in t for k in ("auth", "permission")) or any(
        k in s
        for k in (
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "invalid api key",
            "authentication",
        )
    ):
        return _ErrorKind.AUTH, False, None

    if any(k in s for k in ("400", "bad request", "invalid request")) or "badrequest" in t:
        return _ErrorKind.VALIDATION, False, None

    return _ErrorKind.UNKNOWN, False, None


async def _backoff(attempt: int, retry_after: float | None) -> None:
    """Exponential backoff with jitter. Honours Retry-After when present."""
    if retry_after is not None:
        delay = min(retry_after, _MAX_DELAY)
    else:
        delay = min(_BASE_DELAY * (2**attempt), _MAX_DELAY)
    jitter = random.uniform(-delay * 0.25, delay * 0.25)
    await asyncio.sleep(max(0.1, delay + jitter))


# ── Agent runner ─────────────────────────────────────────────────────────────


async def run_agent(
    agent,
    user_message: str,
    *,
    msg_history,
    deps,
    model_settings: dict | None = None,
    timeout_seconds: int = AGENT_TIMEOUT_SECONDS,
    agent_name: str = "agent",
    agent_label: str = "",
    session_id: str = "",
    config: "AgentConfig | None" = None,
):
    """Run a PydanticAI agent with retry/backoff, error classification, and run logging.

    Every invocation (success or failure) is logged to the agent_runs table
    via fire-and-forget background task.

    *config* is optional — when provided, its RetryConfig fields override the
    module-level defaults for max_retries and backoff_base.
    """
    trace_id = getattr(deps, "trace_id", "")
    if trace_id:
        trace_id_var.set(trace_id)
    agent_name_var.set(agent_name)
    operation_var.set("agent_run")

    max_retries = (
        config.retry.max_retries if (config and config.retry.max_retries) else _MAX_RETRIES
    )
    backoff_base = (
        config.retry.backoff_base if (config and config.retry.backoff_base) else _BASE_DELAY
    )

    active_settings = model_settings
    active_model_override: str | None = None
    t0 = time.monotonic()
    attempts = 0
    overload_attempts = 0

    async def _run(settings, model_override: str | None = None):
        run_kwargs: dict = {
            "message_history": msg_history,
            "deps": deps,
            "model_settings": settings or None,
        }
        if model_override:
            run_kwargs["model"] = model_override
        return await asyncio.wait_for(
            agent.run(user_message, **run_kwargs),
            timeout=timeout_seconds,
        )

    async def _backoff_local(
        attempt: int, retry_after: float | None, base: float = backoff_base
    ) -> None:
        if retry_after is not None:
            delay = min(retry_after, _MAX_DELAY)
        else:
            delay = min(base * (2**attempt), _MAX_DELAY)
        jitter = random.uniform(-delay * 0.25, delay * 0.25)
        await asyncio.sleep(max(0.1, delay + jitter))

    last_exc: Exception = RuntimeError(f"{agent_name}: no attempts made")

    for attempt in range(max_retries):
        attempts = attempt + 1
        try:
            result = await _run(active_settings, active_model_override)
            duration_ms = int((time.monotonic() - t0) * 1000)
            _log_success(
                result,
                user_message=user_message,
                agent_name=agent_name,
                agent_label=agent_label,
                session_id=session_id,
                user_id=getattr(deps, "user_id", ""),
                duration_ms=duration_ms,
                attempts=attempts,
            )
        except TimeoutError:
            last_exc = RuntimeError(f"{agent_name} timed out after {timeout_seconds}s")
            kind, retriable, retry_after = _ErrorKind.TIMEOUT, True, None
        except Exception as e:
            last_exc = e
            kind, retriable, retry_after = _classify(e)
        else:
            return result

        if not retriable:
            logger.error(
                "%s non-retriable %s on attempt %s: %s",
                agent_name,
                kind,
                attempt + 1,
                last_exc,
            )
            _log_failure(
                user_message=user_message,
                agent_name=agent_name,
                agent_label=agent_label,
                session_id=session_id,
                user_id=getattr(deps, "user_id", ""),
                duration_ms=int((time.monotonic() - t0) * 1000),
                attempts=attempts,
                error=str(last_exc),
                error_kind=kind.value,
            )
            raise last_exc

        if kind == _ErrorKind.OVERLOADED:
            overload_attempts += 1
            if overload_attempts >= _OVERLOAD_MAX_RETRIES and not active_model_override:
                original_model = get_model_name(
                    f"agent:{agent_label}" if agent_label else "agent:unified"
                )
                fallback = get_fallback_model(original_model)
                if fallback:
                    logger.warning(
                        "%s overloaded after %s attempts, switching to fallback: %s",
                        agent_name,
                        overload_attempts,
                        fallback,
                    )
                    active_model_override = fallback
                    overload_attempts = 0
                    continue
                logger.warning(
                    "%s overloaded after %s attempts, no fallback available: %s",
                    agent_name,
                    overload_attempts,
                    last_exc,
                )
                break

        if active_settings and kind == _ErrorKind.MODEL_ERROR:
            logger.warning(
                "%s model_error with thinking settings, dropping and retrying: %s",
                agent_name,
                last_exc,
            )
            active_settings = None
            continue

        if attempt < max_retries - 1:
            effective_base = _OVERLOAD_BASE_DELAY if kind == _ErrorKind.OVERLOADED else backoff_base
            logger.warning(
                "%s %s on attempt %s/%s, backing off: %s",
                agent_name,
                kind,
                attempt + 1,
                max_retries,
                last_exc,
            )
            await _backoff_local(attempt, retry_after, base=effective_base)
        else:
            logger.warning(
                "%s %s on final attempt %s/%s: %s",
                agent_name,
                kind,
                max_retries,
                max_retries,
                last_exc,
            )

    _log_failure(
        user_message=user_message,
        agent_name=agent_name,
        agent_label=agent_label,
        session_id=session_id,
        user_id=getattr(deps, "user_id", ""),
        duration_ms=int((time.monotonic() - t0) * 1000),
        attempts=attempts,
        error=str(last_exc),
        error_kind=_classify(last_exc)[0].value,
    )
    raise last_exc


# ── Run logging (fire-and-forget) ────────────────────────────────────────────


def _log_success(
    result,
    *,
    user_message,
    agent_name,
    agent_label="",
    session_id,
    user_id,
    duration_ms,
    attempts,
):
    usage = result.usage()
    label = (
        agent_label or agent_name.split(":")[0].lower().replace("agent", "").strip() or "inventory"
    )
    model_name = get_model_name(f"agent:{label}")
    cost = calc_cost(model_name, usage)
    tool_calls = extract_tool_calls_detailed(result.all_messages())
    response_text = result.output if isinstance(result.output, str) else str(result.output)

    tool_calls_simple = extract_tool_calls(result.all_messages())

    # Prometheus metrics (sync — no blocking)
    record_agent_run(label, "success", duration_ms / 1000.0)
    llm_usage(model_name, usage.input_tokens, usage.output_tokens, cost, agent=label)
    for tc in tool_calls:
        tool_call(tc.get("tool", "unknown"), "success")

    async def _classify_and_write():
        try:
            intent = await classify_intent(user_message)
            validation = validate_response(
                user_message,
                response_text,
                tool_calls_simple,
                tool_calls,
                intent=intent,
            )
            await _db_assistant().log_agent_run(
                get_org_id(),
                session_id=session_id,
                user_id=user_id,
                agent_name=agent_name,
                model=model_name,
                mode="fast",
                user_message=user_message,
                response_text=response_text,
                tool_calls=tool_calls,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
                attempts=attempts,
                validation_passed=validation.passed,
                validation_failures=validation.failures,
                validation_scores=validation.scores,
            )
        except Exception as e:
            logger.warning("Failed to classify/log agent run: %s", e)

    _ = asyncio.create_task(_classify_and_write())  # RUF006: hold reference


def _log_failure(
    *,
    user_message,
    agent_name,
    agent_label="",
    session_id,
    user_id,
    duration_ms,
    attempts,
    error,
    error_kind,
):
    label = (
        agent_label or agent_name.split(":")[0].lower().replace("agent", "").strip() or "inventory"
    )
    model_name = get_model_name(f"agent:{label}")

    # Prometheus metrics
    status = (
        "timeout"
        if error_kind == "timeout"
        else "overloaded"
        if error_kind == "overloaded"
        else "error"
    )
    record_agent_run(label, status, duration_ms / 1000.0)

    async def _write():
        try:
            await _db_assistant().log_agent_run(
                get_org_id(),
                session_id=session_id,
                user_id=user_id,
                agent_name=agent_name,
                model=model_name,
                mode="fast",
                user_message=user_message,
                response_text="",
                tool_calls=[],
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                duration_ms=duration_ms,
                attempts=attempts,
                error=error,
                error_kind=error_kind,
            )
        except Exception as e:
            logger.warning("Failed to log agent run failure: %s", e)

    _ = asyncio.create_task(_write())  # RUF006: hold reference


# ── Specialist runner (no reflection re-run) ──────────────────────────────────


async def run_specialist(
    agent,
    user_message: str,
    *,
    msg_history,
    deps,
    model_settings: dict | None = None,
    agent_name: str = "agent",
    agent_label: str = "inventory",
    session_id: str = "",
    history: list[dict] | None = None,
    config: AgentConfig | None = None,
):
    """Run an agent, validate for logging only (no re-run), package result.

    Standard run cycle for all specialist agents:
    1. Run the agent with tools (with retry/backoff)
    2. Run validators for quality scoring (logged, not acted on)
    3. Package the result dict
    """
    if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE:
        return {
            "response": f"{agent_name} requires ANTHROPIC_API_KEY or OPENROUTER_API_KEY.",
            "tool_calls": [],
            "history": [],
            "thinking": [],
            "agent": agent_label,
        }

    timeout = get_agent_timeout(config)

    _soft_error = {
        "response": "I ran into an issue. Please try again in a moment.",
        "tool_calls": [],
        "history": history or [],
        "thinking": [],
        "agent": agent_label,
    }

    try:
        result = await run_agent(
            agent,
            user_message,
            msg_history=msg_history,
            deps=deps,
            model_settings=model_settings,
            timeout_seconds=timeout,
            agent_name=agent_name,
            agent_label=agent_label,
            session_id=session_id,
        )
    except Exception:
        logger.exception("%s failed", agent_name)
        return _soft_error

    try:
        response_text = result.output if isinstance(result.output, str) else str(result.output)
        model_name = get_model_name(f"agent:{agent_label}")
        usage = result.usage()
        cost = calc_cost(model_name, usage)

        tool_calls_final = extract_tool_calls(result.all_messages())
        tool_calls_det = extract_tool_calls_detailed(result.all_messages())
        text_history = extract_text_history(result.all_messages())

        agent_result = AgentResult(
            agent=agent_label,
            response=response_text,
            tool_calls=tool_calls_final,
            tool_calls_detailed=tool_calls_det,
            history=text_history,
            usage=UsageInfo(
                cost_usd=cost,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                model=model_name,
            ),
            validation=None,
        )
    except Exception:
        logger.exception("%s result processing failed", agent_name)
        return _soft_error

    # Run validation in background — it makes an LLM call (classify_intent)
    # that should never block the user-facing response.
    async def _background_validate():
        try:
            intent = await classify_intent(user_message)
            validation = validate_response(
                user_message,
                response_text,
                tool_calls_final,
                tool_calls_det,
                intent=intent,
            )
            await _db_assistant().log_agent_run(
                get_org_id(),
                session_id=session_id,
                user_id=getattr(deps, "user_id", ""),
                agent_name=agent_name,
                model=model_name,
                mode="fast",
                user_message=user_message,
                response_text=response_text,
                tool_calls=tool_calls_det,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_usd=cost,
                duration_ms=int((time.monotonic() - t0) * 1000),
                attempts=1,
                validation_passed=validation.passed,
                validation_failures=validation.failures,
                validation_scores=validation.scores,
            )
        except Exception as e:
            logger.warning("Background validation/logging failed: %s", e)

    t0 = time.monotonic()
    _ = asyncio.create_task(_background_validate())

    return agent_result.to_dict()
