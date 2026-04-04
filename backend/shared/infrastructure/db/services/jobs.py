"""Jobs persistence via SQLModel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select

from jobs.domain.job import Job
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.types.public_sql_model_models import Jobs


class JobsDatabaseService(DomainDatabaseService):
    def _row_to_job(self, row: Jobs) -> Job:
        return Job(
            id=str(row.id),
            organization_id=str(row.organization_id),
            created_at=row.created_at,
            updated_at=row.updated_at,
            code=row.code,
            name=row.name or "",
            billing_entity_id=str(row.billing_entity_id) if row.billing_entity_id else None,
            status=row.status,
            service_address=row.service_address or "",
            notes=row.notes,
        )

    async def insert_job(self, job: Job) -> None:
        row = Jobs(
            id=as_uuid_required(job.id),
            code=job.code,
            name=job.name or "",
            billing_entity_id=as_uuid_required(job.billing_entity_id) if job.billing_entity_id else None,
            status=str(job.status),
            service_address=job.service_address or "",
            notes=job.notes,
            organization_id=as_uuid_required(job.organization_id),
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def get_job_by_id(self, job_id: str, org_id: str) -> Job | None:
        try:
            jid = as_uuid_required(job_id)
        except ValueError:
            return None
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(select(Jobs).where(Jobs.id == jid, Jobs.organization_id == oid))
            row = result.scalar_one_or_none()
            return self._row_to_job(row) if row else None

    async def get_job_by_code(self, code: str, org_id: str) -> Job | None:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(select(Jobs).where(Jobs.code == code, Jobs.organization_id == oid))
            row = result.scalar_one_or_none()
            return self._row_to_job(row) if row else None

    async def list_jobs(
        self,
        org_id: str,
        *,
        status: str | None = None,
        q: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Job]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(Jobs).where(Jobs.organization_id == oid)
            if status:
                stmt = stmt.where(Jobs.status == status)
            if q:
                like = f"%{q.lower()}%"
                stmt = stmt.where(
                    or_(
                        func.lower(Jobs.code).like(like),
                        func.lower(Jobs.name).like(like),
                    )
                )
            stmt = stmt.order_by(Jobs.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._row_to_job(r) for r in rows]

    async def update_job(self, job_id: str, org_id: str, updates: dict) -> Job | None:
        jid = as_uuid_required(job_id)
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(select(Jobs).where(Jobs.id == jid, Jobs.organization_id == oid))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            now = datetime.now(UTC)
            for key in (
                "name",
                "status",
                "billing_entity_id",
                "service_address",
                "notes",
            ):
                if key in updates and updates[key] is not None:
                    val = updates[key]
                    if key == "billing_entity_id" and val is not None:
                        val = as_uuid_required(val)
                    setattr(row, key, val)
            row.updated_at = now
            await self.end_write_session(session)
        return await self.get_job_by_id(job_id, org_id)

    async def search_jobs(self, org_id: str, query: str, *, limit: int = 20) -> list[Job]:
        oid = as_uuid_required(org_id)
        like = f"%{query.lower()}%"
        async with self.session() as session:
            stmt = (
                select(Jobs)
                .where(
                    Jobs.organization_id == oid,
                    Jobs.status == "active",
                    or_(
                        func.lower(Jobs.code).like(like),
                        func.lower(Jobs.name).like(like),
                    ),
                )
                .order_by(Jobs.code)
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._row_to_job(r) for r in rows]

    async def ensure_job(self, code: str, org_id: str) -> Job:
        """Resolve an existing job by UUID or human code; otherwise create a stub keyed by ``code``."""
        key = str(code).strip()
        try:
            uuid.UUID(key)
            by_id = await self.get_job_by_id(key, org_id)
            if by_id:
                return by_id
        except ValueError:
            pass
        existing = await self.get_job_by_code(key, org_id)
        if existing:
            return existing
        job = Job(code=key, name=key, organization_id=org_id)
        await self.insert_job(job)
        got = await self.get_job_by_code(key, org_id)
        if got is None:
            raise RuntimeError("insert_job succeeded but job row not found by code")
        return got
