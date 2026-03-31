"""Return repository."""

from operations.domain.returns import MaterialReturn
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.database import get_connection, get_org_id


async def _hydrate_items(conn, return_id: str) -> list[dict]:
    """Fetch normalized line items for a return."""
    cursor = await conn.execute(
        "SELECT sku_id, sku, name, quantity, unit_price, cost, unit, sell_uom, sell_cost"
        " FROM return_items WHERE return_id = $1 ORDER BY id",
        (return_id,),
    )
    return [dict(r) for r in await cursor.fetchall()]


async def _row_to_model(row, conn=None) -> MaterialReturn | None:
    if row is None:
        return None
    d = dict(row)
    d.pop("items", None)
    if conn is not None:
        d["items"] = await _hydrate_items(conn, d["id"])
    else:
        d["items"] = []
    return MaterialReturn.model_validate(d)


async def insert(ret: MaterialReturn) -> None:
    conn = get_connection()
    org_id = ret.organization_id or get_org_id()
    await conn.execute(
        """INSERT INTO returns (id, withdrawal_id, contractor_id, contractor_name,
           billing_entity, job_id, subtotal, tax, total, cost_total,
           reason, notes, credit_note_id, processed_by_id, processed_by_name,
           organization_id, created_at, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)""",
        (
            ret.id,
            ret.withdrawal_id,
            ret.contractor_id,
            ret.contractor_name,
            ret.billing_entity,
            ret.job_id,
            ret.subtotal,
            ret.tax,
            ret.total,
            ret.cost_total,
            ret.reason,
            ret.notes,
            ret.credit_note_id,
            ret.processed_by_id,
            ret.processed_by_name,
            org_id,
            ret.created_at,
            ret.updated_at,
        ),
    )
    for item in ret.items:
        qty = item.quantity
        price = item.unit_price
        cost = item.cost
        await conn.execute(
            """INSERT INTO return_items
               (id, return_id, sku_id, sku, name, quantity, unit_price, cost, unit, amount, cost_total, sell_uom, sell_cost)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
            (
                new_uuid7_str(),
                ret.id,
                item.sku_id or "",
                item.sku or "",
                item.name or "",
                qty,
                price,
                cost,
                item.unit or "each",
                round(qty * price, 2),
                round(qty * cost, 2),
                item.sell_uom or "each",
                item.sell_cost,
            ),
        )

    await conn.commit()


async def get_by_id(return_id: str) -> MaterialReturn | None:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT * FROM returns WHERE id = $1 AND organization_id = $2",
        (return_id, org_id),
    )
    row = await cursor.fetchone()
    return await _row_to_model(row, conn)


async def list_returns(
    contractor_id: str | None = None,
    withdrawal_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[MaterialReturn]:
    conn = get_connection()
    org_id = get_org_id()
    n = 1
    query = f"SELECT * FROM returns WHERE organization_id = ${n}"
    params: list = [org_id]
    n += 1
    if contractor_id:
        query += f" AND contractor_id = ${n}"
        params.append(contractor_id)
        n += 1
    if withdrawal_id:
        query += f" AND withdrawal_id = ${n}"
        params.append(withdrawal_id)
        n += 1
    if start_date:
        query += f" AND created_at >= ${n}"
        params.append(start_date)
        n += 1
    if end_date:
        query += f" AND created_at <= ${n}"
        params.append(end_date)
        n += 1
    query += f" ORDER BY created_at DESC LIMIT ${n}"
    params.append(limit)
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    return [await _row_to_model(r, conn) for r in rows]


async def list_by_withdrawal(withdrawal_id: str) -> list[MaterialReturn]:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT * FROM returns WHERE withdrawal_id = $1 AND organization_id = $2 ORDER BY created_at DESC",
        (withdrawal_id, org_id),
    )
    rows = await cursor.fetchall()
    return [await _row_to_model(r, conn) for r in rows]


async def link_credit_note(return_id: str, credit_note_id: str) -> None:
    """Set the credit_note_id on a return. Called by finance context via facade."""
    conn = get_connection()
    org_id = get_org_id()
    await conn.execute(
        "UPDATE returns SET credit_note_id = $1 WHERE id = $2 AND organization_id = $3",
        (credit_note_id, return_id, org_id),
    )
    await conn.commit()


class ReturnRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_returns = staticmethod(list_returns)
    list_by_withdrawal = staticmethod(list_by_withdrawal)
    link_credit_note = staticmethod(link_credit_note)


return_repo = ReturnRepo()
