"""Assistant application queries — safe for cross-context import.

API and other bounded contexts import from here, never from assistant.infrastructure directly.
All reads go through ``get_database_manager().assistant`` with org scope from ``get_org_id``.
"""

from __future__ import annotations

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

__all__ = [
    "get_cost_breakdown",
    "get_session_trace",
    "get_stats",
    "get_validation_summary",
    "list_runs",
]


async def list_runs(
    *,
    agent_name: str | None = None,
    session_id: str | None = None,
    minutes: int = 60,
    limit: int = 50,
    validation_failed_only: bool = False,
) -> list[dict]:
    db = get_database_manager()
    return await db.assistant.list_agent_runs(
        get_org_id(),
        agent_name=agent_name,
        session_id=session_id,
        minutes=minutes,
        limit=limit,
        validation_failed_only=validation_failed_only,
    )


async def get_stats(*, hours: int = 24) -> dict:
    db = get_database_manager()
    return await db.assistant.agent_run_stats(get_org_id(), hours=hours)


async def get_session_trace(session_id: str) -> list[dict]:
    db = get_database_manager()
    return await db.assistant.agent_session_trace(get_org_id(), session_id)


async def get_validation_summary(*, hours: int = 24) -> dict:
    db = get_database_manager()
    return await db.assistant.agent_validation_summary(
        get_org_id(), hours=hours
    )


async def get_cost_breakdown(
    *, days: int = 7, group_by: str = "agent"
) -> list[dict]:
    db = get_database_manager()
    return await db.assistant.agent_cost_breakdown(
        get_org_id(), days=days, group_by=group_by
    )
