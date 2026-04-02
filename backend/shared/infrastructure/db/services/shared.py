"""Shared / cross-cutting persistence via SQLModel."""

from __future__ import annotations

import contextlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import defer

from shared.infrastructure.db.orm_utils import (
    as_uuid_required,
    parse_date_param,
    uuid_str,
)
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.types.public_sql_model_models import (
    Addresses,
    AuditLog,
    Organizations,
    ProcessedEvents,
    Users,
)

logger = logging.getLogger(__name__)

_ACTIVE_CACHE_TTL = 60
_ACTIVE_CACHE_MAX = 1000
_active_cache: dict[str, tuple[bool, float]] = {}


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime | str | None = None


class StoredAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str = ""
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    billing_entity_id: str | None = None
    job_id: str | None = None
    organization_id: str = ""
    created_at: datetime | None = None


class SharedDatabaseService(DomainDatabaseService):
    async def is_user_active(self, user_id: str) -> bool:
        now = time.monotonic()
        cached = _active_cache.get(user_id)
        if cached and (now - cached[1]) < _ACTIVE_CACHE_TTL:
            return cached[0]
        try:
            uid = as_uuid_required(user_id)
            async with self.session() as session:
                result = await session.execute(
                    select(Users.is_active).where(Users.id == uid).limit(1)
                )
                row = result.scalar_one_or_none()
                active = bool(row) if row is not None else True
        except (RuntimeError, OSError, ValueError):
            return True
        _active_cache[user_id] = (active, now)
        if len(_active_cache) > _ACTIVE_CACHE_MAX:
            expired = [
                k
                for k, (_, ts) in _active_cache.items()
                if (now - ts) >= _ACTIVE_CACHE_TTL
            ]
            for k in expired:
                del _active_cache[k]
        return active

    async def fetch_user_by_email(self, email: str) -> dict | None:
        async with self.session() as session:
            result = await session.execute(
                select(Users).where(Users.email == email)
            )
            u = result.scalar_one_or_none()
            if u is None:
                return None
            return self._user_to_auth_dict(u, include_password=True)

    async def fetch_user_safe_by_id(self, user_id: str) -> dict | None:
        uid = as_uuid_required(user_id)
        async with self.session() as session:
            result = await session.execute(
                select(Users)
                .options(defer(Users.password))
                .where(Users.id == uid)
            )
            u = result.scalar_one_or_none()
            if u is None:
                return None
            return self._user_to_safe_dict(u)

    async def insert_user(
        self,
        *,
        user_id: str,
        email: str,
        password_hash: str,
        name: str,
        role: str = "admin",
        organization_id: str,
        created_at: datetime,
    ) -> None:
        row = Users(
            id=as_uuid_required(user_id),
            email=email,
            password=password_hash,
            name=name,
            role=role,
            is_active=True,
            organization_id=as_uuid_required(organization_id),
            created_at=created_at,
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    def _user_to_auth_dict(self, u: Users, *, include_password: bool) -> dict:
        d: dict = {
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "company": u.company,
            "billing_entity": u.billing_entity,
            "phone": u.phone,
            "is_active": u.is_active,
            "organization_id": uuid_str(u.organization_id),
        }
        if include_password:
            d["password"] = u.password
        if u.billing_entity_id is not None:
            d["billing_entity_id"] = str(u.billing_entity_id)
        return d

    def _user_to_safe_dict(self, u: Users) -> dict:
        d = {
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "company": u.company,
            "billing_entity": u.billing_entity,
            "billing_entity_id": uuid_str(u.billing_entity_id),
            "phone": u.phone,
            "is_active": u.is_active,
            "organization_id": uuid_str(u.organization_id),
        }
        return d

    async def get_organization_by_id(self, org_id: str) -> Organization | None:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(Organizations).where(Organizations.id == oid)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return Organization(
                id=str(row.id),
                name=row.name,
                slug=row.slug,
                created_at=row.created_at,
            )

    async def list_organizations(self) -> list[Organization]:
        async with self.session() as session:
            result = await session.execute(
                select(Organizations).order_by(Organizations.name)
            )
            rows = result.scalars().all()
            return [
                Organization(
                    id=str(r.id),
                    name=r.name,
                    slug=r.slug,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    async def insert_address(self, address: StoredAddress) -> None:
        row = Addresses(
            id=as_uuid_required(address.id),
            label=address.label,
            line1=address.line1,
            line2=address.line2,
            city=address.city,
            state=address.state,
            postal_code=address.postal_code,
            country=address.country,
            billing_entity_id=as_uuid_required(address.billing_entity_id)
            if address.billing_entity_id
            else None,
            job_id=as_uuid_required(address.job_id) if address.job_id else None,
            organization_id=as_uuid_required(address.organization_id),
            created_at=address.created_at or datetime.now(UTC),
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def get_address_by_id(
        self, address_id: str, org_id: str
    ) -> StoredAddress | None:
        aid = as_uuid_required(address_id)
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(Addresses).where(
                    Addresses.id == aid, Addresses.organization_id == oid
                )
            )
            row = result.scalar_one_or_none()
            return self._address_to_stored(row)

    async def list_addresses(
        self,
        org_id: str,
        *,
        billing_entity_id: str | None = None,
        job_id: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoredAddress]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(Addresses).where(Addresses.organization_id == oid)
            if billing_entity_id:
                stmt = stmt.where(
                    Addresses.billing_entity_id
                    == as_uuid_required(billing_entity_id)
                )
            if job_id:
                stmt = stmt.where(Addresses.job_id == as_uuid_required(job_id))
            if q:
                like = f"%{q.lower()}%"
                stmt = stmt.where(
                    or_(
                        func.lower(Addresses.label).like(like),
                        func.lower(Addresses.line1).like(like),
                        func.lower(Addresses.city).like(like),
                    )
                )
            stmt = (
                stmt.order_by(Addresses.label, Addresses.line1)
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._address_to_stored(r) for r in rows if r is not None]

    async def search_addresses(
        self, org_id: str, query: str, *, limit: int = 20
    ) -> list[StoredAddress]:
        oid = as_uuid_required(org_id)
        like = f"%{query.lower()}%"
        async with self.session() as session:
            stmt = (
                select(Addresses)
                .where(Addresses.organization_id == oid)
                .where(
                    or_(
                        func.lower(Addresses.label).like(like),
                        func.lower(Addresses.line1).like(like),
                        func.lower(Addresses.city).like(like),
                    )
                )
                .order_by(Addresses.label, Addresses.line1)
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._address_to_stored(r) for r in rows if r is not None]

    def _address_to_stored(self, row: Addresses | None) -> StoredAddress | None:
        if row is None:
            return None
        return StoredAddress(
            id=str(row.id),
            label=row.label,
            line1=row.line1,
            line2=row.line2,
            city=row.city,
            state=row.state,
            postal_code=row.postal_code,
            country=row.country,
            billing_entity_id=uuid_str(row.billing_entity_id),
            job_id=uuid_str(row.job_id),
            organization_id=str(row.organization_id),
            created_at=row.created_at,
        )

    async def query_audit_log(
        self,
        org_id: str,
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
        oid = as_uuid_required(org_id)
        conds = [AuditLog.organization_id == oid]
        if user_id:
            conds.append(AuditLog.user_id == as_uuid_required(user_id))
        if action:
            conds.append(AuditLog.action.like(f"%{action}%"))
        if resource_type:
            conds.append(AuditLog.resource_type == resource_type)
        if resource_id:
            conds.append(AuditLog.resource_id == resource_id)
        start_bound = parse_date_param(start_date)
        if start_bound is not None:
            conds.append(AuditLog.created_at >= start_bound)
        end_bound = parse_date_param(end_date)
        if end_bound is not None:
            conds.append(AuditLog.created_at <= end_bound)

        async with self.session() as session:
            count_result = await session.execute(
                select(func.count()).select_from(AuditLog).where(and_(*conds))
            )
            total = int(count_result.scalar_one() or 0)

            stmt = (
                select(AuditLog)
                .where(and_(*conds))
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            entries = []
            for row in rows:
                d = {
                    "id": str(row.id),
                    "action": row.action,
                    "created_at": row.created_at,
                    "details": row.details,
                    "ip_address": row.ip_address,
                    "organization_id": uuid_str(row.organization_id),
                    "resource_id": row.resource_id,
                    "resource_type": row.resource_type,
                    "user_id": uuid_str(row.user_id),
                }
                if d.get("details"):
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        d["details"] = json.loads(d["details"])
                entries.append(d)
            return entries, total

    async def audit_distinct_actions(self, org_id: str) -> list[str]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(AuditLog.action)
                .where(AuditLog.organization_id == oid)
                .distinct()
                .order_by(AuditLog.action)
            )
            return [r[0] for r in result.all()]

    async def insert_audit_row(
        self,
        *,
        audit_id: uuid.UUID,
        user_id: str | uuid.UUID | None,
        action: str,
        resource_type: str | None,
        resource_id: str | None,
        details: str,
        ip_address: str,
        organization_id: str | uuid.UUID | None,
        created_at: datetime,
    ) -> None:
        row = AuditLog(
            id=audit_id,
            user_id=as_uuid_required(user_id) if user_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or None,
            ip_address=ip_address or None,
            organization_id=as_uuid_required(organization_id)
            if organization_id
            else None,
            created_at=created_at,
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def event_already_processed(
        self, event_id: str, handler_name: str
    ) -> bool:
        try:
            eid = as_uuid_required(event_id)
            async with self.session() as session:
                result = await session.execute(
                    select(ProcessedEvents.event_id).where(
                        ProcessedEvents.event_id == eid,
                        ProcessedEvents.handler_name == handler_name,
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            logger.debug(
                "processed_events lookup failed, treating as not processed",
                exc_info=True,
            )
            return False

    async def mark_event_processed(
        self, event_id: str, handler_name: str, event_type: str
    ) -> None:
        try:
            row = ProcessedEvents(
                event_id=as_uuid_required(event_id),
                handler_name=handler_name,
                event_type=event_type,
                processed_at=datetime.now(UTC),
            )
            async with self.session() as session:
                session.add(row)
                await self.end_write_session(session)
        except Exception:
            logger.debug("processed_events insert failed", exc_info=True)
