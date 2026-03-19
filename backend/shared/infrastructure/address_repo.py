"""Address repository — persistence for the address book.

Cross-cutting reference data used by billing entities, jobs, etc.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shared.infrastructure.database import get_connection, get_org_id


class StoredAddress(BaseModel):
    """Typed model for a persisted address row."""

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


def _row_to_model(row) -> StoredAddress | None:
    if row is None:
        return None
    return StoredAddress.model_validate(dict(row))


_COLUMNS = "id, label, line1, line2, city, state, postal_code, country, billing_entity_id, job_id, organization_id, created_at"


async def insert(address: StoredAddress) -> None:
    conn = get_connection()
    await conn.execute(
        f"INSERT INTO addresses ({_COLUMNS}) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
        (
            address.id,
            address.label,
            address.line1,
            address.line2,
            address.city,
            address.state,
            address.postal_code,
            address.country,
            address.billing_entity_id,
            address.job_id,
            address.organization_id,
            address.created_at,
        ),
    )
    await conn.commit()


async def get_by_id(address_id: str) -> StoredAddress | None:
    org_id = get_org_id()
    conn = get_connection()
    cursor = await conn.execute(
        f"SELECT {_COLUMNS} FROM addresses WHERE id = $1 AND organization_id = $2",
        (address_id, org_id),
    )
    return _row_to_model(await cursor.fetchone())


async def list_addresses(
    billing_entity_id: str | None = None,
    job_id: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StoredAddress]:
    org_id = get_org_id()
    conn = get_connection()
    sql = f"SELECT {_COLUMNS} FROM addresses WHERE organization_id = $1"
    params: list = [org_id]
    n = 2
    if billing_entity_id:
        sql += f" AND billing_entity_id = ${n}"
        params.append(billing_entity_id)
        n += 1
    if job_id:
        sql += f" AND job_id = ${n}"
        params.append(job_id)
        n += 1
    if q:
        like = f"%{q.lower()}%"
        sql += f" AND (LOWER(label) LIKE ${n} OR LOWER(line1) LIKE ${n + 1} OR LOWER(city) LIKE ${n + 2})"
        params.extend([like, like, like])
        n += 3
    sql += f" ORDER BY label, line1 LIMIT ${n} OFFSET ${n + 1}"
    params.extend([limit, offset])
    cursor = await conn.execute(sql, params)
    return [m for r in await cursor.fetchall() if (m := _row_to_model(r)) is not None]


async def search(query: str, limit: int = 20) -> list[StoredAddress]:
    """Fast prefix/substring search for autocomplete."""
    org_id = get_org_id()
    conn = get_connection()
    like = f"%{query.lower()}%"
    cursor = await conn.execute(
        f"SELECT {_COLUMNS} FROM addresses"
        " WHERE organization_id = $1"
        " AND (LOWER(label) LIKE $2 OR LOWER(line1) LIKE $3 OR LOWER(city) LIKE $4)"
        " ORDER BY label, line1 LIMIT $5",
        (org_id, like, like, like, limit),
    )
    return [m for r in await cursor.fetchall() if (m := _row_to_model(r)) is not None]


class AddressRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_addresses = staticmethod(list_addresses)
    search = staticmethod(search)


address_repo = AddressRepo()
