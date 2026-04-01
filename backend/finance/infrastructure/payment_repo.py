"""Payment repository — persistence for payment records."""

from finance.domain.payment import Payment
from shared.infrastructure.db import get_org_id, sql_execute


def _row_to_model(row) -> Payment | None:
    if row is None:
        return None
    d = dict(row)
    return Payment.model_validate(d)


_COLUMNS = "id, invoice_id, billing_entity_id, amount, method, reference, payment_date, notes, recorded_by_id, xero_payment_id, organization_id, created_at, updated_at"


async def insert(
    payment: Payment, withdrawal_ids: list[str] | None = None
) -> None:
    d = payment.model_dump()
    org_id = get_org_id()
    ins_q = "INSERT INTO payments ("
    ins_q += _COLUMNS
    ins_q += ") VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)"
    await sql_execute(
        ins_q,
        (
            d["id"],
            d.get("invoice_id"),
            d.get("billing_entity_id"),
            d["amount"],
            d.get("method", "bank_transfer"),
            d.get("reference", ""),
            d["payment_date"],
            d.get("notes"),
            d["recorded_by_id"],
            d.get("xero_payment_id"),
            org_id,
            d["created_at"],
            d["updated_at"],
        ),
        read_only=False,
    )
    for wid in withdrawal_ids or []:
        await sql_execute(
            "INSERT INTO payment_withdrawals (payment_id, withdrawal_id) VALUES ($1, $2)",
            (d["id"], wid),
            read_only=False,
        )


async def get_by_id(payment_id: str) -> Payment | None:
    org_id = get_org_id()
    sel_q = "SELECT "
    sel_q += _COLUMNS
    sel_q += " FROM payments WHERE id = $1 AND organization_id = $2"
    res = await sql_execute(
        sel_q, (payment_id, org_id), read_only=True, max_rows=2
    )
    row = res.rows[0] if res.rows else None
    p = _row_to_model(row)
    if p:
        wc = await sql_execute(
            "SELECT withdrawal_id FROM payment_withdrawals WHERE payment_id = $1",
            (payment_id,),
            read_only=True,
            max_rows=500,
        )
        p.withdrawal_ids = [r["withdrawal_id"] for r in wc.rows]
    return p


async def list_payments(
    invoice_id: str | None = None,
    billing_entity_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Payment]:
    org_id = get_org_id()
    n = 1
    sql = "SELECT "
    sql += _COLUMNS
    sql += f" FROM payments WHERE organization_id = ${n}"
    params: list = [org_id]
    n += 1
    if invoice_id:
        sql += f" AND invoice_id = ${n}"
        params.append(invoice_id)
        n += 1
    if billing_entity_id:
        sql += f" AND billing_entity_id = ${n}"
        params.append(billing_entity_id)
        n += 1
    if start_date:
        sql += f" AND payment_date >= ${n}"
        params.append(start_date)
        n += 1
    if end_date:
        sql += f" AND payment_date <= ${n}"
        params.append(end_date)
        n += 1
    sql += f" ORDER BY payment_date DESC LIMIT ${n} OFFSET ${n + 1}"
    params.extend([limit, offset])
    res = await sql_execute(sql, params, read_only=True, max_rows=limit + 1)
    return [_row_to_model(r) for r in res.rows]


async def list_for_invoice(invoice_id: str) -> list[Payment]:
    org_id = get_org_id()
    sel_q = "SELECT "
    sel_q += _COLUMNS
    sel_q += " FROM payments WHERE invoice_id = $1 AND organization_id = $2 ORDER BY payment_date DESC"
    res = await sql_execute(
        sel_q, (invoice_id, org_id), read_only=True, max_rows=500
    )
    return [_row_to_model(r) for r in res.rows]


class PaymentRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_payments = staticmethod(list_payments)
    list_for_invoice = staticmethod(list_for_invoice)


payment_repo = PaymentRepo()
