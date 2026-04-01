"""Persist agent run rows — uses ambient ``org_id`` from request/job context."""

from __future__ import annotations

from typing import Any

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def log_agent_run(**kwargs: Any) -> str:
    return await get_database_manager().assistant.log_agent_run(
        get_org_id(), **kwargs
    )
