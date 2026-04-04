"""Job master data routes."""

from fastapi import APIRouter, HTTPException, Query

from jobs.domain.job import Job, JobCreate, JobStatus, JobUpdate
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _db_jobs():
    return get_database_manager().jobs


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(
    current_user: AdminDep,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return await _db_jobs().list_jobs(
        get_org_id(),
        status=status,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get("/search")
async def search_jobs(
    current_user: CurrentUserDep,
    q: str = "",
    limit: int = Query(20, ge=1, le=100),
):
    """Autocomplete endpoint for job pickers (all authenticated users including contractors)."""
    if not q.strip():
        return await _db_jobs().list_jobs(
            get_org_id(),
            status="active",
            limit=limit,
        )
    return await _db_jobs().search_jobs(get_org_id(), q, limit=limit)


@router.get("/{job_id}")
async def get_job(job_id: str, current_user: CurrentUserDep):
    jobs_svc = _db_jobs()
    oid = get_org_id()
    job = await jobs_svc.get_job_by_id(job_id, oid)
    if not job:
        job = await jobs_svc.get_job_by_code(job_id, oid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("")
async def create_job(
    data: JobCreate,
    current_user: AdminDep,
):
    code = data.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Job code is required")

    existing = await _db_jobs().get_job_by_code(code, get_org_id())
    if existing:
        raise HTTPException(status_code=409, detail=f"Job with code '{code}' already exists")

    job = Job(
        code=code,
        name=data.name or code,
        service_address=data.service_address,
        notes=data.notes,
        organization_id=current_user.organization_id,
    )
    await _db_jobs().insert_job(job)
    return job.model_dump()


@router.put("/{job_id}")
async def update_job(
    job_id: str,
    data: JobUpdate,
    current_user: AdminDep,
):
    oid = get_org_id()
    existing = await _db_jobs().get_job_by_id(job_id, oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")

    updates = data.model_dump(exclude_none=True)
    if "status" in updates:
        valid = {s.value for s in JobStatus}
        if updates["status"] not in valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid)}",
            )

    return await _db_jobs().update_job(job_id, oid, updates)
