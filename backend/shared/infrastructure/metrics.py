"""Business metrics helpers — safe access to Prometheus counters/gauges.

Import from here instead of prometheus.py directly. Every function is a
no-op when prometheus_client is not installed, so callers never need to
check availability.
"""

from __future__ import annotations

from shared.infrastructure.prometheus import _PROMETHEUS_AVAILABLE

if _PROMETHEUS_AVAILABLE:
    from shared.infrastructure.prometheus import (
        agent_run_duration,
        chat_messages_total,
        chat_sessions_active,
        document_imports_total,
        llm_cost_usd_total,
        llm_tokens_total,
        tool_calls_total,
    )


# ── Chat session tracking ────────────────────────────────────────────────────


def chat_session_opened() -> None:
    if _PROMETHEUS_AVAILABLE:
        chat_sessions_active.inc()


def chat_session_closed() -> None:
    if _PROMETHEUS_AVAILABLE:
        chat_sessions_active.dec()


def chat_message(agent: str, status: str) -> None:
    """Record a chat message. status: success | error | cancelled | timeout."""
    if _PROMETHEUS_AVAILABLE:
        chat_messages_total.labels(agent=agent, status=status).inc()


# ── Agent execution ──────────────────────────────────────────────────────────


def agent_run(agent: str, status: str, duration_seconds: float) -> None:
    """Record an agent run. status: success | error | timeout."""
    if _PROMETHEUS_AVAILABLE:
        agent_run_duration.labels(agent=agent, status=status).observe(duration_seconds)


# ── LLM usage ────────────────────────────────────────────────────────────────


def llm_usage(model: str, input_tokens: int, output_tokens: int, cost_usd: float, agent: str = "") -> None:
    """Record LLM token usage and cost."""
    if _PROMETHEUS_AVAILABLE:
        llm_tokens_total.labels(direction="input", model=model).inc(input_tokens)
        llm_tokens_total.labels(direction="output", model=model).inc(output_tokens)
        if cost_usd > 0:
            llm_cost_usd_total.labels(agent=agent or "unknown").inc(cost_usd)


# ── Tool calls ───────────────────────────────────────────────────────────────


def tool_call(tool: str, status: str = "success") -> None:
    """Record a tool call. status: success | error."""
    if _PROMETHEUS_AVAILABLE:
        tool_calls_total.labels(tool=tool, status=status).inc()


# ── Document imports ─────────────────────────────────────────────────────────


def document_import(status: str) -> None:
    """Record a document import attempt. status: success | error."""
    if _PROMETHEUS_AVAILABLE:
        document_imports_total.labels(status=status).inc()
