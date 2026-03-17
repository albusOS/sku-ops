"""Organization (tenant) repository — shared infrastructure.

Organizations are the tenancy boundary. Every bounded context
filters by organization_id but none owns the concept — it is
cross-cutting infrastructure.
"""

from pydantic import BaseModel

from shared.infrastructure.database import get_connection


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    created_at: str = ""


def _row_to_model(row) -> Organization | None:
    if row is None:
        return None
    d = dict(row)
    d.pop("organization_id", None)
    return Organization.model_validate(d)


async def get_by_id(org_id: str) -> Organization | None:
    conn = get_connection()
    cursor = await conn.execute(
        "SELECT id, name, slug, created_at FROM organizations WHERE id = $1",
        (org_id,),
    )
    row = await cursor.fetchone()
    return _row_to_model(row)


async def list_all() -> list[Organization]:
    conn = get_connection()
    cursor = await conn.execute(
        "SELECT id, name, slug, created_at FROM organizations ORDER BY name"
    )
    rows = await cursor.fetchall()
    return [_row_to_model(r) for r in rows]
