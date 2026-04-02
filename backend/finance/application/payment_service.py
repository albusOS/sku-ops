"""Payment service: orchestrates recording payments against outbound sales invoices."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from finance.application.invoice_service import mark_paid_for_withdrawal
from finance.application.ledger_service import (
    record_payment as _record_ledger_payment,
)
from finance.domain.payment import Payment, PaymentCreate
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import PaymentRecorded

logger = logging.getLogger(__name__)


def _finance():
    return get_database_manager().finance


async def create_payment_for_withdrawals(
    data: PaymentCreate,
    recorded_by_id: str,
) -> Payment:
    """Aggregate withdrawal totals, create payment, mark each withdrawal paid + ledger entry.

    Returns the created Payment domain object.
    """
    now = datetime.now(UTC)

    if not data.withdrawal_ids and not data.invoice_id:
        raise ValueError("Provide withdrawal_ids or invoice_id")

    withdrawal_ids = list(data.withdrawal_ids)
    org_id = get_org_id()
    fin = _finance()
    ops = get_database_manager().operations

    if not withdrawal_ids and data.invoice_id:
        invoice = await fin.invoice_get_by_id(org_id, data.invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {data.invoice_id} not found")
        withdrawal_ids = invoice.withdrawal_ids

    if not withdrawal_ids:
        raise ValueError("No withdrawals linked to the provided invoice")

    total_amount = 0.0
    billing_entity = ""
    billing_entity_id = None
    contractor_id = ""

    for wid in withdrawal_ids:
        w = await ops.get_withdrawal_by_id(org_id, wid)
        if not w:
            raise ValueError(f"Withdrawal {wid} not found")
        total_amount += w.total
        billing_entity = billing_entity or w.billing_entity
        billing_entity_id = billing_entity_id or w.billing_entity_id
        contractor_id = contractor_id or w.contractor_id

    amount = data.amount if data.amount is not None else total_amount

    payment = Payment(
        invoice_id=data.invoice_id,
        billing_entity_id=billing_entity_id,
        amount=amount,
        method=data.method,
        reference=data.reference,
        payment_date=data.payment_date or now,
        notes=data.notes,
        recorded_by_id=recorded_by_id,
        organization_id=org_id,
    )

    paid_at = data.payment_date or now

    async with transaction():
        await fin.payment_insert(org_id, payment, withdrawal_ids)

        for wid in withdrawal_ids:
            await ops.mark_withdrawal_paid(org_id, wid, paid_at)
            await mark_paid_for_withdrawal(wid)
            w = await ops.get_withdrawal_by_id(org_id, wid)
            if w:
                await _record_ledger_payment(
                    withdrawal_id=wid,
                    amount=w.total,
                    billing_entity=w.billing_entity,
                    contractor_id=w.contractor_id,
                    performed_by_user_id=recorded_by_id,
                )

    await dispatch(
        PaymentRecorded(
            org_id=org_id,
            withdrawal_ids=tuple(withdrawal_ids),
        )
    )
    logger.info(
        "payment.recorded",
        extra={
            "org_id": org_id,
            "payment_id": payment.id,
            "amount": amount,
            "method": data.method,
            "withdrawal_count": len(withdrawal_ids),
            "recorded_by_id": recorded_by_id,
        },
    )
    return payment
