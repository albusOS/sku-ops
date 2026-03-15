"""Thin facade for non-agent LLM access.

Cross-context consumers (purchasing, documents) import from here at module level.
This avoids function-body imports of assistant.application.llm which hide
circular dependencies.

The facade lazily resolves the underlying LLM client on first call,
so importing this module has zero side effects and no import cycles.
"""

from __future__ import annotations

from collections.abc import Callable

from shared.infrastructure.config import ANTHROPIC_AVAILABLE

GenerateTextFn = Callable[[str, str | None], str | None] | None


def get_generate_text() -> GenerateTextFn:
    """Return the generate_text callable if LLM is configured, else None.

    Safe to call at any point after startup — lazily imports the real implementation.
    """
    if not ANTHROPIC_AVAILABLE:
        return None
    from assistant.application.llm import generate_text

    return generate_text
