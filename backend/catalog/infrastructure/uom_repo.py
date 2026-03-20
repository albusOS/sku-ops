"""Unit of measure repository."""

from datetime import UTC, datetime

from catalog.domain.unit_of_measure import UnitOfMeasure
from shared.infrastructure.database import get_connection, get_org_id


def _row_to_model(row) -> UnitOfMeasure | None:
    if row is None:
        return None
    d = dict(row)
    return UnitOfMeasure.model_validate(d)


async def list_all() -> list[UnitOfMeasure]:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        """SELECT id, code, name, family, organization_id, created_at
           FROM units_of_measure
           WHERE organization_id = $1
             AND deleted_at IS NULL
           ORDER BY code""",
        (org_id,),
    )
    rows = await cursor.fetchall()
    return [u for r in rows if (u := _row_to_model(r)) is not None]


async def get_by_code(code: str) -> UnitOfMeasure | None:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        """SELECT id, code, name, family, organization_id, created_at
           FROM units_of_measure
           WHERE code = $1
             AND organization_id = $2
             AND deleted_at IS NULL""",
        (code.lower(), org_id),
    )
    row = await cursor.fetchone()
    return _row_to_model(row)


async def get_by_id(uom_id: str) -> UnitOfMeasure | None:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        """SELECT id, code, name, family, organization_id, created_at
           FROM units_of_measure
           WHERE id = $1
             AND organization_id = $2
             AND deleted_at IS NULL""",
        (uom_id, org_id),
    )
    row = await cursor.fetchone()
    return _row_to_model(row)


async def insert(uom: UnitOfMeasure) -> None:
    d = uom.model_dump()
    d["organization_id"] = d.get("organization_id") or get_org_id()
    conn = get_connection()
    await conn.execute(
        """INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        (d["id"], d["code"], d["name"], d["family"], d["organization_id"], d["created_at"]),
    )


async def delete(uom_id: str) -> int:
    conn = get_connection()
    org_id = get_org_id()
    now = datetime.now(UTC)
    cursor = await conn.execute(
        """UPDATE units_of_measure SET deleted_at = $1
           WHERE id = $2 AND organization_id = $3 AND deleted_at IS NULL""",
        (now, uom_id, org_id),
    )
    return cursor.rowcount


class UomRepo:
    list_all = staticmethod(list_all)
    get_by_code = staticmethod(get_by_code)
    get_by_id = staticmethod(get_by_id)
    insert = staticmethod(insert)
    delete = staticmethod(delete)


uom_repo = UomRepo()
