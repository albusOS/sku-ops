"""Shared utilities for all specialist agents."""
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)

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
