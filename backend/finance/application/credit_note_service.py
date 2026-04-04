"""Credit note application service — orchestrates cross-context interactions."""

import logging
from datetime import UTC, datetime

from finance.application.ledger_service import record_credit_note_application
from finance.domain.credit_note import CreditNote
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import CreditNoteApplied

logger = logging.getLogger(__name__)


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations


async def insert_credit_note(
    return_id: str,
    invoice_id: str | None,
    items: list[dict],
    subtotal: float = 0,
    tax: float = 0,
    total: float = 0,
) -> CreditNote:
    """Create a credit note and link it to the return (operations-owned mutation)."""
    org_id = get_org_id()
    fin = _db_finance()
    async with transaction():
        cn = await fin.credit_note_insert(
            org_id,
            return_id,
            invoice_id,
            items,
            subtotal,
            tax,
            total,
        )
        await _db_operations().link_return_credit_note(org_id, return_id, cn.id)
    logger.info(
        "credit_note.created",
        extra={
            "org_id": org_id,
            "credit_note_id": cn.id,
            "return_id": return_id,
            "invoice_id": invoice_id,
            "total": total,
        },
    )
    return cn


async def apply_credit_note(
    credit_note_id: str,
    performed_by_user_id: str | None = None,
) -> CreditNote:
    """Apply a credit note to its linked invoice and write AR ledger entry.

    If the invoice balance reaches zero, marks linked withdrawals as paid
    via the operations facade. All steps run in a single transaction so
    invoice, withdrawal, and ledger state stay consistent.
    """
    org_id = get_org_id()
    fin = _db_finance()
    async with transaction():
        result = await fin.credit_note_apply(org_id, credit_note_id)

        if result.auto_paid and result.invoice_id:
            now = datetime.now(UTC)
            await _db_operations().mark_withdrawals_paid_by_invoice(org_id, result.invoice_id, now)

        await record_credit_note_application(
            credit_note_id=credit_note_id,
            amount=float(result.credit_note.total),
            billing_entity=result.credit_note.billing_entity,
            contractor_id="",
            performed_by_user_id=performed_by_user_id,
        )

    await dispatch(
        CreditNoteApplied(
            org_id=org_id,
            credit_note_id=credit_note_id,
            invoice_id=result.invoice_id or "",
        )
    )
    logger.info(
        "credit_note.applied",
        extra={
            "org_id": org_id,
            "credit_note_id": credit_note_id,
            "invoice_id": result.invoice_id,
            "auto_paid": result.auto_paid,
            "performed_by_user_id": performed_by_user_id,
        },
    )
    return result.credit_note
