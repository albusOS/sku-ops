"""Persistent cross-session memory for chat agents.

Delegates persistence and semantic recall to ``AssistantDatabaseService``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


async def save(user_id: str, session_id: str, artifacts: list[dict]) -> None:
    """Persist extracted artifacts and queue embedding upsert (non-blocking)."""
    org_id = get_org_id()
    db = get_database_manager()
    await db.assistant.memory_save(org_id, user_id, session_id, artifacts)


async def recall(
    user_id: str,
    query: str | None = None,
    limit: int = 10,
    query_embedding: np.ndarray | None = None,
) -> str:
    """Return formatted memory context for session injection."""
    org_id = get_org_id()
    db = get_database_manager()
    return await db.assistant.memory_recall(
        org_id,
        user_id,
        query=query,
        limit=limit,
        query_embedding=query_embedding,
    )
