"""Low-level invoice fetch helpers — imported by both invoice_repo and invoice_mutations.

Extracted into its own module so that invoice_mutations can call get_by_id without
creating a circular import with invoice_repo.
"""

from finance.domain.invoice import Invoice, InvoiceLineItem, InvoiceWithDetails
from shared.infrastructure.db import get_org_id, sql_execute


def _row_to_model(row) -> Invoice | None:
    if row is None:
        return None
    d = dict(row)
    return Invoice.model_validate(d)


def _build_invoice_with_details(
    inv_row,
    line_item_rows,
    withdrawal_ids: list[str],
) -> InvoiceWithDetails:
    d = dict(inv_row)
    items = []
    for r in line_item_rows:
        li = dict(r)
        items.append(InvoiceLineItem.model_validate(li))
    d["line_items"] = items
    d["withdrawal_ids"] = withdrawal_ids
    return InvoiceWithDetails.model_validate(d)


async def get_by_id(invoice_id: str) -> InvoiceWithDetails | None:
    org_id = get_org_id()
    res_inv = await sql_execute(
        "SELECT * FROM invoices WHERE id = $1 AND organization_id = $2 AND deleted_at IS NULL",
        (invoice_id, org_id),
        read_only=True,
        max_rows=2,
    )
    row = res_inv.rows[0] if res_inv.rows else None
    if not row:
        return None

    res_li = await sql_execute(
        "SELECT li.* FROM invoice_line_items li"
        " JOIN invoices i ON i.id = li.invoice_id"
        " WHERE li.invoice_id = $1 AND i.organization_id = $2"
        " ORDER BY li.id",
        (invoice_id, org_id),
        read_only=True,
        max_rows=2000,
    )
    li_rows = res_li.rows

    res_w = await sql_execute(
        "SELECT iw.withdrawal_id FROM invoice_withdrawals iw"
        " JOIN invoices i ON i.id = iw.invoice_id"
        " WHERE iw.invoice_id = $1 AND i.organization_id = $2",
        (invoice_id, org_id),
        read_only=True,
        max_rows=500,
    )
    withdrawal_ids = [r["withdrawal_id"] for r in res_w.rows]

    return _build_invoice_with_details(row, li_rows, withdrawal_ids)
