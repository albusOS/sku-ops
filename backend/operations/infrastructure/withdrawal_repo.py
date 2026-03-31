"""Withdrawal repository."""

from datetime import datetime

from operations.domain.enums import PaymentStatus
from operations.domain.withdrawal import MaterialWithdrawal
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.database import get_connection, get_org_id


async def _hydrate_items(conn, withdrawal_id: str) -> list[dict]:
    """Fetch normalized line items for a withdrawal."""
    cursor = await conn.execute(
        "SELECT sku_id, sku, name, quantity, unit_price, cost, unit, sell_uom, sell_cost"
        " FROM withdrawal_items WHERE withdrawal_id = $1 ORDER BY id",
        (withdrawal_id,),
    )
    return [dict(r) for r in await cursor.fetchall()]


async def _row_to_model(row, conn=None) -> MaterialWithdrawal | None:
    if row is None:
        return None
    d = dict(row)
    d.pop("items", None)
    if conn is not None:
        d["items"] = await _hydrate_items(conn, d["id"])
    else:
        d["items"] = []
    return MaterialWithdrawal.model_validate(d)


async def insert(withdrawal: MaterialWithdrawal) -> None:
    conn = get_connection()
    org_id = withdrawal.organization_id or get_org_id()
    await conn.execute(
        """INSERT INTO withdrawals (id, job_id, service_address, notes, subtotal, tax, tax_rate, total, cost_total,
           contractor_id, contractor_name, contractor_company, billing_entity, billing_entity_id, payment_status, invoice_id, paid_at,
           processed_by_id, processed_by_name, organization_id, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)""",
        (
            withdrawal.id,
            withdrawal.job_id,
            withdrawal.service_address,
            withdrawal.notes,
            withdrawal.subtotal,
            withdrawal.tax,
            withdrawal.tax_rate,
            withdrawal.total,
            withdrawal.cost_total,
            withdrawal.contractor_id,
            withdrawal.contractor_name,
            withdrawal.contractor_company,
            withdrawal.billing_entity,
            withdrawal.billing_entity_id,
            withdrawal.payment_status,
            withdrawal.invoice_id,
            withdrawal.paid_at,
            withdrawal.processed_by_id,
            withdrawal.processed_by_name,
            org_id,
            withdrawal.created_at,
        ),
    )
    for item in withdrawal.items:
        qty = item.quantity
        price = item.unit_price
        cost = item.cost
        await conn.execute(
            """INSERT INTO withdrawal_items
               (id, withdrawal_id, sku_id, sku, name, quantity, unit_price, cost, unit, amount, cost_total, sell_uom, sell_cost)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
            (
                new_uuid7_str(),
                withdrawal.id,
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


async def list_withdrawals(
    contractor_id: str | None = None,
    payment_status: str | None = None,
    billing_entity: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10000,
    offset: int = 0,
) -> list[MaterialWithdrawal]:
    conn = get_connection()
    org_id = get_org_id()
    n = 1
    query = f"SELECT * FROM withdrawals WHERE organization_id = ${n}"
    params: list = [org_id]
    n += 1
    if contractor_id:
        query += f" AND contractor_id = ${n}"
        params.append(contractor_id)
        n += 1
    if payment_status:
        query += f" AND payment_status = ${n}"
        params.append(payment_status)
        n += 1
    if billing_entity:
        query += f" AND billing_entity = ${n}"
        params.append(billing_entity)
        n += 1
    if start_date:
        query += f" AND created_at >= ${n}"
        params.append(start_date)
        n += 1
    if end_date:
        query += f" AND created_at <= ${n}"
        params.append(end_date)
        n += 1
    query += f" ORDER BY created_at DESC LIMIT ${n} OFFSET ${n + 1}"
    params.extend([limit, offset])
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    return [await _row_to_model(r, conn) for r in rows]


async def get_by_id(withdrawal_id: str) -> MaterialWithdrawal | None:
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT * FROM withdrawals WHERE id = $1 AND organization_id = $2",
        (withdrawal_id, org_id),
    )
    row = await cursor.fetchone()
    return await _row_to_model(row, conn)


async def mark_paid(
    withdrawal_id: str, paid_at: datetime
) -> tuple[MaterialWithdrawal | None, bool]:
    """Mark withdrawal paid. Returns (withdrawal, actually_changed).

    Only transitions from 'unpaid' — invoiced withdrawals must be paid via the
    invoice payment flow to keep invoice state consistent.
    """
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "UPDATE withdrawals SET payment_status = $1, paid_at = $2 "
        "WHERE id = $3 AND payment_status != $4 AND organization_id = $5",
        (
            PaymentStatus.PAID,
            paid_at,
            withdrawal_id,
            PaymentStatus.PAID,
            org_id,
        ),
    )
    await conn.commit()
    return await get_by_id(withdrawal_id), cursor.rowcount > 0


async def bulk_mark_paid(
    withdrawal_ids: list[str], paid_at: datetime
) -> list[str]:
    """Mark withdrawals paid. Returns IDs that were actually changed (previously unpaid)."""
    if not withdrawal_ids:
        return []
    conn = get_connection()
    org_id = get_org_id()
    n = len(withdrawal_ids)
    id_placeholders = ",".join(f"${i}" for i in range(3, 3 + n))
    exclude_idx = 3 + n
    org_idx = exclude_idx + 1
    cursor = await conn.execute(
        f"UPDATE withdrawals SET payment_status = $1, paid_at = $2 "
        f"WHERE id IN ({id_placeholders}) AND payment_status != ${exclude_idx} "
        f"AND organization_id = ${org_idx} RETURNING id",
        [
            PaymentStatus.PAID,
            paid_at,
            *withdrawal_ids,
            PaymentStatus.PAID,
            org_id,
        ],
    )
    await conn.commit()
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def link_to_invoice(withdrawal_id: str, invoice_id: str) -> bool:
    """Set invoice_id and mark as invoiced. Returns False if already linked or paid.

    Guards against: already linked to another invoice, already marked paid.
    Called by finance context via facade. Org-scoped to prevent cross-tenant mutation.
    """
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "UPDATE withdrawals SET invoice_id = $1, payment_status = $2 "
        "WHERE id = $3 AND invoice_id IS NULL AND payment_status = $4 "
        "AND organization_id = $5",
        (
            invoice_id,
            PaymentStatus.INVOICED,
            withdrawal_id,
            PaymentStatus.UNPAID,
            org_id,
        ),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def unlink_from_invoice(withdrawal_ids: list[str]) -> None:
    """Clear invoice link and reset to unpaid. Called by finance context via facade.

    Org-scoped to prevent cross-tenant mutation.
    """
    if not withdrawal_ids:
        return
    conn = get_connection()
    org_id = get_org_id()
    placeholders = ",".join(f"${i}" for i in range(1, 1 + len(withdrawal_ids)))
    org_idx = len(withdrawal_ids) + 1
    status_idx = org_idx + 1
    await conn.execute(
        f"UPDATE withdrawals SET invoice_id = NULL, payment_status = ${status_idx} "
        f"WHERE id IN ({placeholders}) AND organization_id = ${org_idx}",
        [*withdrawal_ids, org_id, PaymentStatus.UNPAID],
    )
    await conn.commit()


async def mark_paid_by_invoice(invoice_id: str, paid_at: datetime) -> None:
    """Mark all withdrawals linked to an invoice as paid. Called by finance context via facade.

    Org-scoped to prevent cross-tenant mutation.
    """
    conn = get_connection()
    org_id = get_org_id()
    await conn.execute(
        "UPDATE withdrawals SET payment_status = $1, paid_at = $2 "
        "WHERE invoice_id = $3 AND organization_id = $4",
        (PaymentStatus.PAID, paid_at, invoice_id, org_id),
    )
    await conn.commit()


async def units_sold_by_product(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Sum of quantities sold per sku_id from withdrawal_items."""
    conn = get_connection()
    org_id = get_org_id()
    params: list = [org_id]
    n = 2
    date_filter = ""
    if start_date:
        date_filter += f" AND w.created_at >= ${n}"
        params.append(start_date)
        n += 1
    if end_date:
        date_filter += f" AND w.created_at <= ${n}"
        params.append(end_date)
        n += 1
    query = (
        "SELECT wi.sku_id, SUM(wi.quantity) AS total_qty"
        " FROM withdrawal_items wi"
        " JOIN withdrawals w ON wi.withdrawal_id = w.id"
        " WHERE w.organization_id = $1"
    )
    query += date_filter
    query += " GROUP BY wi.sku_id"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def payment_status_breakdown(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Revenue breakdown by payment status: {Paid: X, Invoiced: Y, Unpaid: Z}."""
    conn = get_connection()
    org_id = get_org_id()
    params: list = [org_id]
    n = 2
    date_filter = ""
    if start_date:
        date_filter += f" AND w.created_at >= ${n}"
        params.append(start_date)
        n += 1
    if end_date:
        date_filter += f" AND w.created_at <= ${n}"
        params.append(end_date)
        n += 1
    query = (
        "SELECT"
        " CASE"
        " WHEN w.payment_status = 'paid' THEN 'Paid'"
        " WHEN w.invoice_id IS NOT NULL THEN 'Invoiced'"
        " ELSE 'Unpaid'"
        " END AS status,"
        " ROUND(CAST(SUM(w.total) AS NUMERIC), 2) AS total"
        " FROM withdrawals w"
        " WHERE w.organization_id = $1"
    )
    query += date_filter
    query += " GROUP BY status"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}


class WithdrawalRepo:
    insert = staticmethod(insert)
    list_withdrawals = staticmethod(list_withdrawals)
    get_by_id = staticmethod(get_by_id)
    mark_paid = staticmethod(mark_paid)
    bulk_mark_paid = staticmethod(bulk_mark_paid)
    link_to_invoice = staticmethod(link_to_invoice)
    unlink_from_invoice = staticmethod(unlink_from_invoice)
    mark_paid_by_invoice = staticmethod(mark_paid_by_invoice)
    units_sold_by_product = staticmethod(units_sold_by_product)
    payment_status_breakdown = staticmethod(payment_status_breakdown)


withdrawal_repo = WithdrawalRepo()
