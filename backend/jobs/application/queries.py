"""Job application queries — safe for cross-context import.

API and other bounded contexts import from here, never from jobs.infrastructure directly.
Thin delegation layer that decouples consumers from infrastructure details.
"""

from jobs.domain.job import Job
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def list_jobs(
    status: str | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Job]:
    db = get_database_manager()
    return await db.jobs.list_jobs(
        get_org_id(),
        status=status,
        q=q,
        limit=limit,
        offset=offset,
    )


async def search_jobs(query: str, limit: int = 20) -> list[Job]:
    db = get_database_manager()
    return await db.jobs.search_jobs(get_org_id(), query, limit=limit)


async def get_job_by_id(job_id: str) -> Job | None:
    db = get_database_manager()
    return await db.jobs.get_job_by_id(job_id, get_org_id())


async def get_job_by_code(code: str) -> Job | None:
    db = get_database_manager()
    return await db.jobs.get_job_by_code(code, get_org_id())


async def insert_job(job: Job | dict) -> None:
    db = get_database_manager()
    await db.jobs.insert_job(job)


async def update_job(job_id: str, updates: dict) -> Job | None:
    db = get_database_manager()
    return await db.jobs.update_job(job_id, get_org_id(), updates)
