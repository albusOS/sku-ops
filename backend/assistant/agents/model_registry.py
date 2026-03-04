"""Model registry — maps task types to models via OpenRouter.

Single source of truth for which model handles which task.  Falls back to
direct Anthropic provider when OpenRouter is not configured.
"""
import logging
from functools import lru_cache

from shared.infrastructure.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_AVAILABLE,
    AGENT_PRIMARY_MODEL,
)

logger = logging.getLogger(__name__)

# ── Per-task model assignments ────────────────────────────────────────────────
# OpenRouter model identifiers (provider/model format).
# Override any entry via env: MODEL_REGISTRY_<TASK>=<model>  (dots→underscores)

_DEFAULTS: dict[str, str] = {
    # Primary agent work — quality matters most
    "agent:inventory":  "anthropic/claude-sonnet-4-6",
    "agent:ops":        "anthropic/claude-sonnet-4-6",
    "agent:finance":    "anthropic/claude-sonnet-4-6",
    "agent:insights":   "anthropic/claude-sonnet-4-6",
    "agent:general":    "anthropic/claude-sonnet-4-6",

    # Infrastructure — cheap/fast, only used as LLM fallback for ambiguous routing
    "infra:router_fallback": "meta-llama/llama-3.3-70b-instruct",
    "infra:merge_fallback":  "meta-llama/llama-3.3-70b-instruct",

    # Eval — judge model for quality scoring
    "eval:judge": "anthropic/claude-sonnet-4-6",
}

# Per-million-token pricing (input, output) for cost estimation.
# Updated from OpenRouter pricing page; used when the API doesn't return cost.
_PRICING: dict[str, dict[str, float]] = {
    "anthropic/claude-sonnet-4-6":           {"input": 3.00,  "output": 15.00},
    "anthropic/claude-haiku-4-5":            {"input": 0.80,  "output": 4.00},
    "anthropic/claude-opus-4-6":             {"input": 15.00, "output": 75.00},
    "meta-llama/llama-3.3-70b-instruct":     {"input": 0.39,  "output": 0.39},
    "google/gemini-2.0-flash-001":           {"input": 0.10,  "output": 0.40},
    "mistralai/mistral-small-24b-instruct-2501": {"input": 0.14, "output": 0.14},
}


def _resolve(task: str) -> str:
    """Return the model identifier for *task*, checking env overrides first."""
    import os
    env_key = "MODEL_REGISTRY_" + task.replace(":", "_").replace(".", "_").upper()
    override = os.environ.get(env_key, "").strip()
    if override:
        return override
    return _DEFAULTS.get(task, _DEFAULTS["agent:general"])


def get_model_name(task: str) -> str:
    """Return the raw model identifier string for a task."""
    return _resolve(task)


def get_model(task: str):
    """Return a PydanticAI-compatible model for *task*.

    When OpenRouter is configured, returns an OpenAI-compatible model pointed at
    the OpenRouter gateway.  Otherwise falls back to the direct Anthropic
    provider using AGENT_PRIMARY_MODEL.
    """
    if not OPENROUTER_AVAILABLE:
        logger.debug("OpenRouter not configured, falling back to %s", AGENT_PRIMARY_MODEL)
        return AGENT_PRIMARY_MODEL

    model_name = _resolve(task)
    return _build_openai_model(model_name)


@lru_cache(maxsize=32)
def _build_openai_model(model_name: str):
    """Cached constructor so we reuse the same httpx client per model."""
    from pydantic_ai.models.openai import OpenAIModel
    return OpenAIModel(
        model_name,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )


def calc_cost(task_or_model: str, usage) -> float:
    """Estimate cost in USD from a PydanticAI Usage object.

    Accepts either a task key ("agent:inventory") or a raw model name
    ("anthropic/claude-sonnet-4-6").
    """
    model = _resolve(task_or_model) if ":" in task_or_model else task_or_model
    # Strip pydantic-ai provider prefix if present (e.g. "anthropic:claude-...")
    bare = model.split(":", 1)[-1] if model.startswith(("anthropic:", "openai:")) else model
    pricing = _PRICING.get(model) or _PRICING.get(bare)
    if not pricing:
        for key, p in _PRICING.items():
            if bare in key or key in bare:
                pricing = p
                break
    if not pricing:
        return 0.0
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    return round((inp * pricing["input"] + out * pricing["output"]) / 1_000_000, 6)
