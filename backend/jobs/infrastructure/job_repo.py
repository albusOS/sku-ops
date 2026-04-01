"""Job repository — delegates to JobsDatabaseService."""

from jobs.domain.job import Job
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def insert(job: Job) -> None:
    db = get_database_manager()
    await db.jobs.insert_job(job)


async def get_by_id(job_id: str) -> Job | None:
    db = get_database_manager()
    return await db.jobs.get_job_by_id(job_id, get_org_id())


async def get_by_code(code: str) -> Job | None:
    db = get_database_manager()
    return await db.jobs.get_job_by_code(code, get_org_id())


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


async def update(job_id: str, updates: dict) -> Job | None:
    db = get_database_manager()
    return await db.jobs.update_job(job_id, get_org_id(), updates)


async def search(query: str, limit: int = 20) -> list[Job]:
    db = get_database_manager()
    return await db.jobs.search_jobs(get_org_id(), query, limit=limit)


async def ensure_job(code: str) -> Job:
    db = get_database_manager()
    return await db.jobs.ensure_job(code, get_org_id())


class JobRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    get_by_code = staticmethod(get_by_code)
    list_jobs = staticmethod(list_jobs)
    update = staticmethod(update)
    search = staticmethod(search)
    ensure_job = staticmethod(ensure_job)


job_repo = JobRepo()
