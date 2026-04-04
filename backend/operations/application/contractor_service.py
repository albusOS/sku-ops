"""Contractor management service.

Owns all contractor CRUD and queries. Cross-context consumers import
from here for contractor lookups. When Supabase arrives, the auth parts
(password, JWT) move to Supabase; profile data stays here.
"""

from __future__ import annotations

from datetime import UTC, datetime

import bcrypt
from pydantic import BaseModel, ConfigDict, field_validator

from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import (
    get_org_id,
    sql_execute,
    transaction,
)
from shared.infrastructure.db.base import get_database_manager


def _db_finance():
    return get_database_manager().finance


def _make_id() -> str:
    return new_uuid7_str()


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
    d.pop("password", None)
    return Contractor.model_validate(d)


_SELECT_COLS = (
    "id, email, name, role, company, billing_entity, billing_entity_id, phone, is_active, organization_id, created_at"
)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def get_contractor_by_id(user_id: str) -> Contractor | None:
    org_id = get_org_id()
    cursor = await sql_execute(
        f"SELECT {_SELECT_COLS} FROM users WHERE id = $1 AND organization_id = $2",
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
    cursor = await sql_execute(
        f"SELECT {_SELECT_COLS} FROM users WHERE id IN ({placeholders}) AND organization_id = ${1 + len(user_ids)}",
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
    base = f"SELECT {_SELECT_COLS} FROM users WHERE role = 'contractor' AND organization_id = $1"
    params: list = [org_id]
    if search and search.strip():
        term = f"%{search.strip()}%"
        base += " AND (name LIKE $2 OR email LIKE $3 OR company LIKE $4 OR billing_entity LIKE $5 OR phone LIKE $6)"
        params.extend([term, term, term, term, term])
    base += " ORDER BY name"
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
    """Create a contractor user with associated billing entity.

    Raises ValueError if email is already registered.
    Runs inside a transaction so billing entity + user insert are atomic.
    """
    org_id = get_org_id()

    async with transaction():
        dup = await sql_execute("SELECT id FROM users WHERE email = $1", (email,))
        if dup.rows:
            raise ValueError("Email already registered")

        billing_name = billing_entity_name or company or "Independent"
        be = await _db_finance().billing_entity_ensure(org_id, billing_name)

        contractor_id = _make_id()
        now = _now()
        hashed_pw = _hash_password(password)
        company_val = company or "Independent"

        cols = (
            "id, email, password, name, role, company, billing_entity, billing_entity_id, "
            "phone, is_active, organization_id, created_at"
        )
        await sql_execute(
            f"INSERT INTO users ({cols}) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
            (
                contractor_id,
                email,
                hashed_pw,
                name,
                "contractor",
                company_val,
                billing_name,
                be.id if be else None,
                phone or "",
                True,
                org_id,
                now,
            ),
        )

    return ContractorCreateResult(
        id=contractor_id,
        email=email,
        name=name,
        company=company_val,
        billing_entity=billing_name,
        billing_entity_id=be.id if be else None,
        phone=phone or "",
        organization_id=org_id,
        created_at=now,
    )


async def update_contractor(contractor_id: str, updates: UpdateContractorCommand) -> Contractor | None:
    """Update contractor profile fields. Returns updated contractor or None."""
    contractor = await get_contractor_by_id(contractor_id)
    if not contractor or contractor.role != "contractor":
        return None
    org_id = get_org_id()
    if contractor.organization_id != org_id:
        return None

    set_clauses = []
    values = []
    n = 1
    for key in ("name", "company", "billing_entity", "phone"):
        val = getattr(updates, key, None)
        if val is not None:
            set_clauses.append(f"{key} = ${n}")
            values.append(val)
            n += 1
    if updates.is_active is not None:
        set_clauses.append(f"is_active = ${n}")
        values.append(bool(updates.is_active))
        n += 1
    if not set_clauses:
        return contractor

    billing_name_changed = updates.billing_entity is not None and updates.billing_entity != contractor.billing_entity

    async with transaction():
        if billing_name_changed:
            be = await _db_finance().billing_entity_ensure(org_id, updates.billing_entity)
            set_clauses.append(f"billing_entity_id = ${n}")
            values.append(be.id if be else None)
            n += 1

        values.extend([contractor_id, org_id])
        await sql_execute(
            f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ${n} AND organization_id = ${n + 1}",
            values,
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
        )

    return cursor.rowcount
