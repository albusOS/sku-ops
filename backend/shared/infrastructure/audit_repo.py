"""Audit log repository — delegates to SharedDatabaseService."""

from __future__ import annotations

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def query_audit_log(
    *,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    db = get_database_manager()
    return await db.shared.query_audit_log(
        get_org_id(),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


async def distinct_actions() -> list[str]:
    db = get_database_manager()
    return await db.shared.audit_distinct_actions(get_org_id())
