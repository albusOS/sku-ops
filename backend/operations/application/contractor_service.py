"""Contractor management service.

Owns all contractor CRUD and queries. Auth user is provisioned via Supabase Admin;
profile row lives in public.users (billing_entity_id FK).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from shared.infrastructure.db import (
    get_org_id,
    sql_execute,
    transaction,
)
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _db_finance():
    return get_database_manager().finance


def _now() -> datetime:
    return datetime.now(UTC)


class Contractor(BaseModel):
    """Read model for contractor data."""

    model_config = ConfigDict(extra="ignore")

    id: str
    email: str
    name: str
    role: str = "contractor"
    company: str = ""
    billing_entity: str = ""
    billing_entity_id: str | None = None
    phone: str | None = ""
    is_active: bool = True
    organization_id: str = ""
    created_at: datetime | None = None

    @field_validator("company", "billing_entity", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v):
        return v if v is not None else ""


class UpdateContractorCommand(BaseModel):
    """Typed input for updating a contractor's profile fields."""

    name: str | None = None
    company: str | None = None
    billing_entity: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class ContractorCreateResult(BaseModel):
    id: str
    email: str
    name: str
    role: str = "contractor"
    company: str = ""
    billing_entity: str = ""
    billing_entity_id: str | None = None
    phone: str | None = ""
    is_active: bool = True
    organization_id: str = ""
    created_at: datetime | None = None

    @field_validator("company", "billing_entity", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v):
        return v if v is not None else ""


def _row_to_model(row) -> Contractor | None:
    if row is None:
        return None
    d = dict(row)
    if "is_active" in d:
        d["is_active"] = bool(d["is_active"])
    if d.get("billing_entity_id") is not None:
        d["billing_entity_id"] = str(d["billing_entity_id"])
    if d.get("organization_id") is not None:
        d["organization_id"] = str(d["organization_id"])
    if d.get("id") is not None:
        d["id"] = str(d["id"])
    return Contractor.model_validate(d)


_SELECT_COLS = (
    "u.id, u.email, u.name, u.role, u.company, COALESCE(be.name, '') AS billing_entity, "
    "u.billing_entity_id, u.phone, u.is_active, u.organization_id, u.created_at"
)

_FROM_JOIN = "FROM users u LEFT JOIN billing_entities be ON be.id = u.billing_entity_id "


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def get_contractor_by_id(user_id: str) -> Contractor | None:
    org_id = get_org_id()
    cursor = await sql_execute(
        f"SELECT {_SELECT_COLS} {_FROM_JOIN} WHERE u.id = $1 AND u.organization_id = $2",
        (user_id, org_id),
    )
    row = cursor.rows[0] if cursor.rows else None
    return _row_to_model(row)


async def get_users_by_ids(user_ids: list[str]) -> dict[str, Contractor]:
    """Return {user_id: Contractor} for a batch of IDs. Missing IDs are omitted."""
    if not user_ids:
        return {}
    org_id = get_org_id()
    placeholders = ",".join(f"${i}" for i in range(1, 1 + len(user_ids)))
    org_ph = 1 + len(user_ids)
    cursor = await sql_execute(
        f"SELECT {_SELECT_COLS} {_FROM_JOIN} WHERE u.id IN ({placeholders}) "
        f"AND u.organization_id = ${org_ph}",
        (*user_ids, org_id),
    )
    rows = cursor.rows
    result: dict[str, Contractor] = {}
    for row in rows:
        user = _row_to_model(row)
        if user:
            result[user.id] = user
    return result


async def list_contractors(search: str | None = None) -> list[Contractor]:
    org_id = get_org_id()
    base = (
        f"SELECT {_SELECT_COLS} {_FROM_JOIN} WHERE u.role = 'contractor' AND u.organization_id = $1"
    )
    params: list = [org_id]
    if search and search.strip():
        term = f"%{search.strip()}%"
        base += (
            " AND (u.name LIKE $2 OR u.email LIKE $3 OR u.company LIKE $4 OR "
            "be.name LIKE $5 OR u.phone LIKE $6)"
        )
        params.extend([term, term, term, term, term])
    base += " ORDER BY u.name"
    cursor = await sql_execute(base, params)
    rows = cursor.rows
    return [u for r in rows if (u := _row_to_model(r)) is not None]


async def count_contractors() -> int:
    org_id = get_org_id()
    cursor = await sql_execute(
        "SELECT COUNT(*) FROM users WHERE role = 'contractor' AND organization_id = $1",
        (org_id,),
    )
    row = cursor.rows[0] if cursor.rows else None
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


async def create_contractor(
    email: str,
    password: str,
    name: str,
    company: str | None = None,
    billing_entity_name: str | None = None,
    phone: str | None = None,
) -> ContractorCreateResult:
    """Create contractor: Supabase Auth user + profile row (trigger + UPDATE).

    Raises ValueError if email is already registered or Auth admin is unavailable.
    """
    org_id = get_org_id()
    db = get_database_manager()
    company_val = company or "Independent"
    billing_name = billing_entity_name or company or "Independent"

    async with transaction():
        dup = await sql_execute("SELECT id FROM users WHERE email = $1", (email,))
        if dup.rows:
            raise ValueError("Email already registered")

        be = await _db_finance().billing_entity_ensure(org_id, billing_name)
        sb = await db.db_service.get_async_supabase_admin()
        if sb is None:
            raise ValueError("Supabase admin is not configured")

        try:
            auth_res = await sb.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"name": name},
                    "app_metadata": {
                        "role": "contractor",
                        "organization_id": str(org_id),
                    },
                }
            )
        except Exception as e:
            logger.exception(
                "contractor_supabase_create_failed",
                extra={"org_id": org_id, "email": email},
            )
            raise ValueError(f"Could not create auth user: {e}") from e

        uid = str(auth_res.user.id)
        await sql_execute(
            "UPDATE users SET company = $1, billing_entity_id = $2, phone = $3, "
            "organization_id = $4, role = $5 WHERE id = $6",
            (
                company_val,
                be.id if be else None,
                phone or "",
                org_id,
                "contractor",
                uid,
            ),
            read_only=False,
        )

    logger.info(
        "contractor_created",
        extra={"org_id": org_id, "contractor_id": uid, "email": email},
    )

    created = await get_contractor_by_id(uid)
    if created is None:
        msg = "Contractor profile missing after provision"
        raise RuntimeError(msg)

    return ContractorCreateResult(
        id=created.id,
        email=created.email,
        name=created.name,
        company=created.company,
        billing_entity=created.billing_entity,
        billing_entity_id=created.billing_entity_id,
        phone=created.phone or "",
        organization_id=created.organization_id,
        created_at=created.created_at,
    )


async def update_contractor(
    contractor_id: str, updates: UpdateContractorCommand
) -> Contractor | None:
    """Update contractor profile fields. Returns updated contractor or None."""
    contractor = await get_contractor_by_id(contractor_id)
    if not contractor or contractor.role != "contractor":
        return None
    org_id = get_org_id()
    if contractor.organization_id != org_id:
        return None

    set_clauses = []
    values: list = []
    n = 1
    for key in ("name", "company", "phone"):
        val = getattr(updates, key, None)
        if val is not None:
            set_clauses.append(f"{key} = ${n}")
            values.append(val)
            n += 1
    if updates.is_active is not None:
        set_clauses.append(f"is_active = ${n}")
        values.append(bool(updates.is_active))
        n += 1
    if not set_clauses and updates.billing_entity is None:
        return contractor

    billing_name_changed = (
        updates.billing_entity is not None and updates.billing_entity != contractor.billing_entity
    )

    async with transaction():
        if billing_name_changed:
            be = await _db_finance().billing_entity_ensure(org_id, updates.billing_entity)
            set_clauses.append(f"billing_entity_id = ${n}")
            values.append(be.id if be else None)
            n += 1

        if not set_clauses:
            return contractor

        values.extend([contractor_id, org_id])
        next_n = n + 1
        await sql_execute(
            f"UPDATE users SET {', '.join(set_clauses)} "
            f"WHERE id = ${n} AND organization_id = ${next_n}",
            values,
            read_only=False,
        )

    return await get_contractor_by_id(contractor_id)


async def delete_contractor(contractor_id: str) -> int:
    """Delete a contractor. Returns number of rows deleted (0 or 1)."""
    contractor = await get_contractor_by_id(contractor_id)
    if not contractor or contractor.role != "contractor":
        return 0
    org_id = get_org_id()
    if contractor.organization_id != org_id:
        return 0

    async with transaction():
        cursor = await sql_execute(
            "DELETE FROM users WHERE id = $1 AND role = 'contractor' AND organization_id = $2",
            (contractor_id, org_id),
            read_only=False,
        )

    return cursor.rowcount
