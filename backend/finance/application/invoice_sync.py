"""Invoice sync — Xero synchronization and COGS repost."""

import logging

from finance.adapters.invoicing_factory import get_invoicing_gateway
from finance.application.org_settings_service import get_xero_settings
from finance.application.sync_results import InvoiceSyncResult
from finance.domain.enums import XeroSyncStatus
from finance.domain.invoice import InvoiceWithDetails
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _xero_status(status: str | XeroSyncStatus) -> str:
    return status if isinstance(status, str) else status.value


def _db_finance():
    return get_database_manager().finance


# ---------------------------------------------------------------------------
# Xero sync
# ---------------------------------------------------------------------------


async def sync_invoice(inv_id: str) -> InvoiceSyncResult:
    """Sync a single invoice to Xero."""
    org_id = get_org_id()
    fin = _db_finance()
    inv = await fin.invoice_get_by_id(org_id, inv_id)
    if not inv:
        return InvoiceSyncResult(invoice_id=inv_id, success=False, error="Invoice not found")

    if inv.xero_sync_status == XeroSyncStatus.SYNCING:
        try:
            existing = await _gateway_fetch_existing(inv)
            if existing:
                return existing
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning("Idempotency check failed for %s: %s", inv_id, e)

    await fin.invoice_set_xero_sync_status(org_id, inv_id, _xero_status(XeroSyncStatus.SYNCING))

    xero_settings = await get_xero_settings()
    gateway = get_invoicing_gateway(xero_settings)

    try:
        result = await gateway.sync_invoice(inv, xero_settings)
    except (RuntimeError, OSError, ValueError) as e:
        await fin.invoice_set_xero_sync_status(org_id, inv_id, _xero_status(XeroSyncStatus.FAILED))
        return InvoiceSyncResult(
            invoice_id=inv_id,
            invoice_number=inv.invoice_number,
            success=False,
            error=str(e),
        )

    if result.success and result.external_id:
        await fin.invoice_set_xero_invoice_id(
            org_id,
            inv_id,
            result.external_id,
            xero_cogs_journal_id=result.external_journal_id,
        )
    else:
        await fin.invoice_set_xero_sync_status(org_id, inv_id, _xero_status(XeroSyncStatus.FAILED))

    return InvoiceSyncResult(
        invoice_id=inv_id,
        invoice_number=inv.invoice_number,
        xero_invoice_id=result.external_id,
        xero_journal_id=result.external_journal_id,
        success=result.success,
        error=result.error,
    )


async def _gateway_fetch_existing(
    inv: InvoiceWithDetails,
) -> InvoiceSyncResult | None:
    """Check Xero for an existing invoice matching our number (idempotency guard)."""
    org_id = get_org_id()
    fin = _db_finance()
    xero_settings = await get_xero_settings()
    gateway = get_invoicing_gateway(xero_settings)
    existing = await gateway.fetch_invoice_by_number(inv.invoice_number, xero_settings)
    if existing:
        xero_id = existing["InvoiceID"]
        await fin.invoice_set_xero_invoice_id(org_id, inv.id, xero_id)
        return InvoiceSyncResult(invoice_id=inv.id, success=True, xero_invoice_id=xero_id)
    return None


# ---------------------------------------------------------------------------
# COGS repost
# ---------------------------------------------------------------------------


async def repost_cogs_for_invoice(inv_id: str) -> InvoiceSyncResult:
    """Re-post the COGS manual journal for an invoice whose line items changed after sync."""
    org_id = get_org_id()
    fin = _db_finance()
    inv = await fin.invoice_get_by_id(org_id, inv_id)
    if not inv:
        return InvoiceSyncResult(invoice_id=inv_id, success=False, error="Invoice not found")
    if not inv.xero_invoice_id:
        return InvoiceSyncResult(
            invoice_id=inv_id,
            success=False,
            error="Invoice not yet synced to Xero",
        )

    xero_settings = await get_xero_settings()
    gateway = get_invoicing_gateway(xero_settings)

    try:
        new_journal_id = await gateway.repost_cogs_journal(
            inv, xero_settings, old_journal_id=inv.xero_cogs_journal_id
        )
        await fin.invoice_set_xero_invoice_id(
            org_id,
            inv_id,
            inv.xero_invoice_id,
            xero_cogs_journal_id=new_journal_id,
        )
        return InvoiceSyncResult(invoice_id=inv_id, success=True, xero_journal_id=new_journal_id)
    except (RuntimeError, OSError, ValueError) as e:
        await fin.invoice_set_xero_sync_status(org_id, inv_id, _xero_status(XeroSyncStatus.FAILED))
        return InvoiceSyncResult(invoice_id=inv_id, success=False, error=str(e))
