"""Invoice repo — Xero sync status updates and sync-related queries."""

from datetime import UTC, datetime

from finance.domain.invoice import Invoice
from shared.infrastructure.database import get_connection


async def set_xero_invoice_id(
    invoice_id: str,
    xero_invoice_id: str,
    xero_cogs_journal_id: str | None = None,
    organization_id: str | None = None,
) -> None:
    conn = get_connection()
    params: list = [
        xero_invoice_id,
        xero_cogs_journal_id,
        datetime.now(UTC).isoformat(),
        invoice_id,
    ]
    where = "WHERE id = ?"
    if organization_id:
        where += " AND organization_id = ?"
        params.append(organization_id)
    upd_q = "UPDATE invoices SET xero_invoice_id = ?, xero_cogs_journal_id = ?, xero_sync_status = 'synced', updated_at = ? "
    upd_q += where
    await conn.execute(upd_q, params)
    await conn.commit()


async def set_xero_sync_status(
    invoice_id: str, status: str, organization_id: str | None = None
) -> None:
    conn = get_connection()
    params: list = [status, datetime.now(UTC).isoformat(), invoice_id]
    where = "WHERE id = ?"
    if organization_id:
        where += " AND organization_id = ?"
        params.append(organization_id)
    upd_q = "UPDATE invoices SET xero_sync_status = ?, updated_at = ? "
    upd_q += where
    await conn.execute(upd_q, params)
    await conn.commit()


def _row_to_invoice(row) -> Invoice | None:
    if row is None:
        return None
    d = dict(row) if hasattr(row, "keys") else {}
    if not d:
        return None
    if d.get("organization_id") is None:
        d.pop("organization_id", None)
    return Invoice.model_validate(d)


async def list_unsynced_invoices(organization_id: str) -> list[Invoice]:
    conn = get_connection()
    cursor = await conn.execute(
        """SELECT id, invoice_number, billing_entity, total, status, xero_sync_status, created_at
           FROM invoices
           WHERE organization_id = ?
             AND status IN ('approved', 'sent')
             AND (xero_invoice_id IS NULL OR xero_sync_status = 'syncing')
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (organization_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_invoice(r) for r in rows]


async def list_invoices_needing_reconciliation(organization_id: str) -> list[Invoice]:
    conn = get_connection()
    cursor = await conn.execute(
        """SELECT id, invoice_number, billing_entity, total, xero_invoice_id, xero_sync_status,
                  (SELECT COUNT(*) FROM invoice_line_items WHERE invoice_id = invoices.id) AS line_count
           FROM invoices
           WHERE organization_id = ?
             AND xero_invoice_id IS NOT NULL
             AND xero_sync_status != 'mismatch'
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (organization_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_invoice(r) for r in rows]


async def list_failed_invoices(organization_id: str) -> list[Invoice]:
    conn = get_connection()
    cursor = await conn.execute(
        """SELECT id, invoice_number, billing_entity, total, status, created_at
           FROM invoices
           WHERE organization_id = ?
             AND xero_sync_status = 'failed'
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (organization_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_invoice(r) for r in rows]


async def list_mismatch_invoices(organization_id: str) -> list[Invoice]:
    conn = get_connection()
    cursor = await conn.execute(
        """SELECT id, invoice_number, billing_entity, total, xero_invoice_id, created_at
           FROM invoices
           WHERE organization_id = ?
             AND xero_sync_status = 'mismatch'
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (organization_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_invoice(r) for r in rows]


async def list_stale_cogs_invoices(organization_id: str) -> list[Invoice]:
    conn = get_connection()
    cursor = await conn.execute(
        """SELECT id, invoice_number, billing_entity, total, xero_invoice_id, xero_cogs_journal_id,
                  (SELECT COUNT(*) FROM invoice_line_items WHERE invoice_id = invoices.id) AS line_count
           FROM invoices
           WHERE organization_id = ?
             AND xero_sync_status = 'cogs_stale'
             AND xero_invoice_id IS NOT NULL
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (organization_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_invoice(r) for r in rows]
