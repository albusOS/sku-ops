"""Background task: extract memory artifacts from completed chat sessions.

Called fire-and-forget via asyncio.create_task(). Never raises — failures are
logged as warnings and silently discarded so they never affect the user.

Uses generate_text (PydanticAI-backed) when LLM is available.
"""

import json
import logging

from assistant.agents.core.model_registry import get_model_name
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM = load_prompt(__file__, "prompt.md")


async def extract_and_save(
    user_id: str,
    session_id: str,
    history: list[dict],
) -> None:
    """Extract facts from conversation history and persist as memory artifacts.

    Designed to run as a background asyncio task — swallows all exceptions.
    """
    if not history or len(history) < 4:
        return
    try:
        from assistant.application.llm import generate_text
        from shared.infrastructure.config import (
            ANTHROPIC_AVAILABLE,
            OPENROUTER_AVAILABLE,
            is_test,
        )

        if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE and not is_test:
            return

        turns = []
        for h in history[-20:]:
            role = (h.get("role") or "user").upper()
            content = (h.get("content") or "").strip()[:600]
            if content:
                turns.append(f"{role}: {content}")
        if len(turns) < 2:
            return

        prompt = "\n\n".join(turns)
        model_id = get_model_name("infra:synthesis")
        raw = await generate_text(prompt, _EXTRACT_SYSTEM, model_id)
        if not raw or not raw.strip():
            return

        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.removeprefix("```json").removeprefix("```")
            stripped = stripped.removesuffix("```").strip()

        artifacts = json.loads(stripped)
        if isinstance(artifacts, list) and artifacts and len(artifacts) <= 50:
            await get_database_manager().assistant.memory_save(
                get_org_id(), user_id, session_id, artifacts
            )

    except (
        json.JSONDecodeError,
        ValueError,
        TypeError,
        RuntimeError,
        OSError,
    ) as e:
        logger.warning("Memory extraction failed (non-critical): %s", e)
