"""Shared utilities for all specialist agents."""
import asyncio
import logging

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 45


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
    """Run a PydanticAI agent with timeout and thinking-retry.

    Raises RuntimeError on timeout. Re-raises other exceptions after optionally
    retrying without thinking settings (to recover from thinking-budget errors).
    """
    async def _run(settings):
        return await agent.run(
            user_message,
            message_history=msg_history,
            deps=deps,
            model=f"anthropic:{model_id}",
            model_settings=settings or None,
        )

    try:
        return await asyncio.wait_for(_run(model_settings), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise RuntimeError(f"{agent_name} timed out after {timeout_seconds}s")
    except Exception as e:
        if model_settings:
            logger.warning(f"{agent_name} error with thinking settings, retrying without: {e}")
            try:
                return await asyncio.wait_for(_run(None), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise RuntimeError(f"{agent_name} timed out on retry after {timeout_seconds}s")
        raise

# Pricing per million tokens (USD)
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}


def calc_cost(model: str, usage) -> float:
    key = next((k for k in _MODEL_PRICING if model.startswith(k)), None)
    if not key:
        return 0.0
    p = _MODEL_PRICING[key]
    return round((usage.input_tokens * p["input"] + usage.output_tokens * p["output"]) / 1_000_000, 6)


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
