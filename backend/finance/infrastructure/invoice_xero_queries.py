"""Invoice repo — Xero sync status updates and sync-related queries."""

from datetime import UTC, datetime

from finance.domain.invoice import Invoice
from shared.infrastructure.db import get_org_id, sql_execute


async def set_xero_invoice_id(
    invoice_id: str,
    xero_invoice_id: str,
    xero_cogs_journal_id: str | None = None,
) -> None:
    org_id = get_org_id()
    await sql_execute(
        "UPDATE invoices SET xero_invoice_id = $1, xero_cogs_journal_id = $2,"
        " xero_sync_status = 'synced', updated_at = $3"
        " WHERE id = $4 AND organization_id = $5",
        (
            xero_invoice_id,
            xero_cogs_journal_id,
            datetime.now(UTC),
            invoice_id,
            org_id,
        ),
    )


async def set_xero_sync_status(invoice_id: str, status: str) -> None:
    org_id = get_org_id()
    await sql_execute(
        "UPDATE invoices SET xero_sync_status = $1, updated_at = $2"
        " WHERE id = $3 AND organization_id = $4",
        (status, datetime.now(UTC), invoice_id, org_id),
    )


def _row_to_invoice(row) -> Invoice | None:
    if row is None:
        return None
    d = dict(row)
    return Invoice.model_validate(d)


async def list_unsynced_invoices() -> list[Invoice]:
    org_id = get_org_id()
    res = await sql_execute(
        """SELECT id, invoice_number, billing_entity, total, status, xero_sync_status, organization_id, created_at
           FROM invoices
           WHERE organization_id = $1
             AND status IN ('approved', 'sent')
             AND (xero_invoice_id IS NULL OR xero_sync_status = 'syncing')
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (org_id,),
    )
    return [_row_to_invoice(r) for r in res.rows]


async def list_invoices_needing_reconciliation() -> list[Invoice]:
    org_id = get_org_id()
    res = await sql_execute(
        """SELECT id, invoice_number, billing_entity, total, xero_invoice_id, xero_sync_status, organization_id,
                  (SELECT COUNT(*) FROM invoice_line_items WHERE invoice_id = invoices.id) AS line_count
           FROM invoices
           WHERE organization_id = $1
             AND xero_invoice_id IS NOT NULL
             AND xero_sync_status != 'mismatch'
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (org_id,),
    )
    return [_row_to_invoice(r) for r in res.rows]


async def list_failed_invoices() -> list[Invoice]:
    org_id = get_org_id()
    res = await sql_execute(
        """SELECT id, invoice_number, billing_entity, total, status, organization_id, created_at
           FROM invoices
           WHERE organization_id = $1
             AND xero_sync_status = 'failed'
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (org_id,),
    )
    return [_row_to_invoice(r) for r in res.rows]


async def list_mismatch_invoices() -> list[Invoice]:
    org_id = get_org_id()
    res = await sql_execute(
        """SELECT id, invoice_number, billing_entity, total, xero_invoice_id, organization_id, created_at
           FROM invoices
           WHERE organization_id = $1
             AND xero_sync_status = 'mismatch'
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (org_id,),
    )
    return [_row_to_invoice(r) for r in res.rows]


async def list_stale_cogs_invoices() -> list[Invoice]:
    org_id = get_org_id()
    res = await sql_execute(
        """SELECT id, invoice_number, billing_entity, total, xero_invoice_id, xero_cogs_journal_id, organization_id,
                  (SELECT COUNT(*) FROM invoice_line_items WHERE invoice_id = invoices.id) AS line_count
           FROM invoices
           WHERE organization_id = $1
             AND xero_sync_status = 'cogs_stale'
             AND xero_invoice_id IS NOT NULL
             AND deleted_at IS NULL
           ORDER BY created_at""",
        (org_id,),
    )
    return [_row_to_invoice(r) for r in res.rows]
