"""LLM package — provider validation and cost estimation.

PydanticAI resolves model strings natively (anthropic:*, openrouter:*, openai:*).
This package validates API key availability at startup and provides cost lookups.

Public API:
    init_llm()       — call once at startup to validate provider keys
    get_model()      — returns the model string (PydanticAI resolves it)
    estimate_cost()  — estimate USD cost for token counts
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_initialized = False


def init_llm() -> None:
    """Validate LLM provider availability. Call once at startup."""
    global _initialized
    from shared.infrastructure.config import (
        ANTHROPIC_API_KEY,
        OPENAI_API_KEY,
        OPENROUTER_API_KEY,
        is_test,
    )

    providers: list[str] = []
    if is_test:
        providers.append("test")
    if ANTHROPIC_API_KEY:
        providers.append("anthropic")
    if OPENROUTER_API_KEY:
        providers.append("openrouter")
    if OPENAI_API_KEY:
        providers.append("openai (embeddings)")

    if not providers:
        logger.warning("No LLM API keys configured — agents will fail at runtime")
    else:
        logger.info("LLM providers available: %s", ", ".join(providers))

    _initialized = True


def get_model(model_id: str) -> str:
    """Return the model string for PydanticAI to resolve natively.

    In test mode, prefixes bare model IDs with 'test:' so PydanticAI
    uses its built-in test model.
    """
    from shared.infrastructure.config import is_test

    if is_test and not model_id.startswith("test:"):
        return f"test:{model_id}"
    return model_id


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for the given token counts."""
    from assistant.infrastructure.llm.cost import calc_cost

    return calc_cost(model_id, input_tokens, output_tokens)
