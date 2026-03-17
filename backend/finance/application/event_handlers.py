"""Finance domain event handlers — post-commit, best-effort side effects.

Ledger entries, invoice status updates, payment recording, and invoice creation
are all written inside the owning service's transaction (atomic, reliable).

These handlers handle genuinely optional side effects that can fail without
corrupting core data:
  - Auto-credit-note creation and application on return (when invoice exists)

WithdrawalCreated: invoice is now created atomically inside create_withdrawal().
WithdrawalPaid: dispatched for WS notification only.
"""

from __future__ import annotations

import logging

from finance.application.credit_note_service import apply_credit_note, insert_credit_note
from shared.infrastructure.domain_events import idempotent, on, retryable
from shared.kernel.domain_events import ReturnCreated

logger = logging.getLogger(__name__)


# ── Auto credit note on return ────────────────────────────────────────────────


@on(ReturnCreated)
@idempotent
@retryable(max_retries=2, base_delay=0.1)
async def auto_credit_note_on_return(event: ReturnCreated) -> None:
    """Create and apply a credit note when a return has an associated invoice.

    The ledger reversal is already committed atomically inside return_service.
    This handler generates the credit note document and applies it against
    the original invoice so the contractor's balance reflects the return.

    Skipped if there is no invoice_id (return against an un-invoiced withdrawal).
    Failure is logged — the return and ledger are already committed.
    """
    if not event.invoice_id:
        return

    try:
        items = [
            {
                "name": li.sku_id,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "cost": li.cost,
                "sku_id": li.sku_id,
                "unit": li.unit,
            }
            for li in event.ledger_items
        ]
        subtotal = round(sum(li.unit_price * li.quantity for li in event.ledger_items), 2)

        cn = await insert_credit_note(
            return_id=event.return_id,
            invoice_id=event.invoice_id,
            items=items,
            subtotal=subtotal,
            tax=event.tax,
            total=event.total,
        )
        await apply_credit_note(
            credit_note_id=cn.id,
            performed_by_user_id=event.performed_by_user_id or None,
        )
        logger.info(
            "credit_note.auto_applied",
            extra={
                "org_id": event.org_id,
                "credit_note_id": cn.id,
                "return_id": event.return_id,
                "invoice_id": event.invoice_id,
                "total": event.total,
            },
        )
    except Exception:
        logger.exception(
            "Auto credit note failed for return %s (invoice %s)",
            event.return_id,
            event.invoice_id,
        )
