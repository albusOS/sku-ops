"""Job application service — safe for cross-context import.

Other bounded contexts import from here, never from jobs.infrastructure directly.
"""

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def ensure_job(code: str) -> dict:
    """Get existing job by code, or auto-create a minimal one."""
    db = get_database_manager()
    return await db.jobs.ensure_job(code, get_org_id())
