"""Material request repository."""

from datetime import datetime

from operations.domain.enums import MaterialRequestStatus
from operations.domain.material_request import MaterialRequest
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.database import get_connection, get_org_id
from shared.kernel.errors import InvalidTransitionError


async def _hydrate_items(conn, material_request_id: str) -> list[dict]:
    """Fetch normalized line items for a material request."""
    cursor = await conn.execute(
        "SELECT sku_id, sku, name, quantity, unit_price, cost, unit"
        " FROM material_request_items WHERE material_request_id = $1 ORDER BY id",
        (material_request_id,),
    )
    return [dict(r) for r in await cursor.fetchall()]


async def _row_to_model(row, conn=None) -> MaterialRequest | None:
    if row is None:
        return None
    d = dict(row)
    d.pop("items", None)
    if conn is not None:
        d["items"] = await _hydrate_items(conn, d["id"])
    else:
        d["items"] = []
    return MaterialRequest.model_validate(d)


async def insert(request: MaterialRequest) -> None:
    conn = get_connection()
    org_id = request.organization_id or get_org_id()
    await conn.execute(
        """INSERT INTO material_requests (id, contractor_id, contractor_name, status, withdrawal_id,
           job_id, service_address, notes, created_at, processed_at, processed_by_id, organization_id)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
        (
            request.id,
            request.contractor_id,
            request.contractor_name,
            request.status,
            request.withdrawal_id,
            request.job_id,
            request.service_address,
            request.notes,
            request.created_at,
            request.processed_at,
            request.processed_by_id,
            org_id,
        ),
    )
    for item in request.items:
        await conn.execute(
            """INSERT INTO material_request_items
               (id, material_request_id, sku_id, sku, name, quantity, unit_price, cost, unit)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            (
                new_uuid7_str(),
                request.id,
                item.sku_id or "",
                item.sku or "",
                item.name or "",
                item.quantity,
                item.unit_price,
                item.cost,
                item.unit or "each",
            ),
        )
    await conn.commit()


async def get_by_id(request_id: str) -> MaterialRequest | None:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT * FROM material_requests WHERE id = $1 AND organization_id = $2",
        (request_id, org_id),
    )
    row = await cursor.fetchone()
    return await _row_to_model(row, conn)


async def list_pending(limit: int = 100) -> list[MaterialRequest]:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT * FROM material_requests WHERE status = $1 AND organization_id = $2 ORDER BY created_at DESC LIMIT $3",
        (MaterialRequestStatus.PENDING, org_id, limit),
    )
    rows = await cursor.fetchall()
    return [await _row_to_model(r, conn) for r in rows]


async def list_by_contractor(
    contractor_id: str, limit: int = 100
) -> list[MaterialRequest]:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT * FROM material_requests WHERE contractor_id = $1 AND organization_id = $2 ORDER BY created_at DESC LIMIT $3",
        (contractor_id, org_id, limit),
    )
    rows = await cursor.fetchall()
    return [await _row_to_model(r, conn) for r in rows]


async def mark_processed(
    request_id: str,
    withdrawal_id: str,
    processed_by_id: str,
    processed_at: datetime,
) -> bool:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        """UPDATE material_requests SET status = $1, withdrawal_id = $2, processed_by_id = $3, processed_at = $4
           WHERE id = $5 AND status = $6 AND organization_id = $7""",
        (
            MaterialRequestStatus.PROCESSED,
            withdrawal_id,
            processed_by_id,
            processed_at,
            request_id,
            MaterialRequestStatus.PENDING,
            org_id,
        ),
    )
    if cursor.rowcount == 0:
        raise InvalidTransitionError(
            "MaterialRequest", "processed", "processed"
        )
    await conn.commit()
    return True


class MaterialRequestRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_pending = staticmethod(list_pending)
    list_by_contractor = staticmethod(list_by_contractor)
    mark_processed = staticmethod(mark_processed)


material_request_repo = MaterialRequestRepo()
