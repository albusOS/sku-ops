"""Financial ledger service — writes monetary entries at event time.

Each public function corresponds to one financial event. The entries it
creates are the system of record for all reports. If an entry is wrong,
you write a correcting entry (never delete).

Every event produces a set of entries grouped under a single journal_id
so the transaction can be verified as balanced.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from finance.domain.ledger import Account, FinancialEntry, ReferenceType
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.types import round_money

if TYPE_CHECKING:
    from shared.kernel.event_payloads import LedgerItem, ReceivedItemSummary


async def _check_fiscal_period() -> None:
    """Check that the current date is not in a closed fiscal period."""
    now = datetime.now(UTC)
    await get_database_manager().finance.fiscal_check_period_open(
        get_org_id(), now
    )


async def _record_sale_event(
    reference_id: str,
    reference_type: ReferenceType,
    sign: int,
    items: list[LedgerItem],
    tax: float,
    total: float,
    job_id: str,
    billing_entity: str,
    contractor_id: str,
    performed_by_user_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Shared logic for withdrawals (+1) and returns (-1).

    Entries per item: REVENUE, COGS, INVENTORY (decrease on sale, increase on return).
    Entries per event: TAX_COLLECTED, ACCOUNTS_RECEIVABLE.
    All entries share one journal_id.
    """
    if await get_database_manager().finance.ledger_entries_exist(
        get_org_id(), reference_type.value, reference_id
    ):
        return
    await _check_fiscal_period()
    journal_id = new_uuid7_str()
    common = {
        "journal_id": journal_id,
        "job_id": job_id,
        "billing_entity": billing_entity,
        "contractor_id": contractor_id,
        "performed_by_user_id": performed_by_user_id,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "organization_id": get_org_id(),
    }
    entries: list[FinancialEntry] = []

    for li in items:
        qty = li.quantity
        unit = li.unit
        unit_price = li.unit_price
        sell_cost = li.sell_cost or li.cost
        sell_uom = li.sell_uom or unit
        dept = li.category_name
        pid = li.sku_id
        entries.append(
            FinancialEntry(
                account=Account.REVENUE,
                amount=round_money(sign * unit_price * qty),
                quantity=qty,
                unit=unit,
                unit_cost=unit_price,
                department=dept,
                sku_id=pid,
                **common,
            )
        )
        entries.append(
            FinancialEntry(
                account=Account.COGS,
                amount=round_money(sign * sell_cost * qty),
                quantity=qty,
                unit=sell_uom,
                unit_cost=sell_cost,
                department=dept,
                sku_id=pid,
                **common,
            )
        )
        entries.append(
            FinancialEntry(
                account=Account.INVENTORY,
                amount=round_money(-sign * sell_cost * qty),
                quantity=qty,
                unit=sell_uom,
                unit_cost=sell_cost,
                department=dept,
                sku_id=pid,
                **common,
            )
        )

    entries.append(
        FinancialEntry(
            account=Account.TAX_COLLECTED,
            amount=round_money(sign * tax),
            **common,
        )
    )
    entries.append(
        FinancialEntry(
            account=Account.ACCOUNTS_RECEIVABLE,
            amount=round_money(sign * total),
            **common,
        )
    )

    if created_at:
        for e in entries:
            e.created_at = created_at

    await get_database_manager().finance.ledger_insert_entries(
        get_org_id(), entries
    )


async def record_withdrawal(
    withdrawal_id: str,
    items: list[LedgerItem],
    tax: float,
    total: float,
    job_id: str,
    billing_entity: str,
    contractor_id: str,
    performed_by_user_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Write ledger entries for a new material withdrawal."""
    await _record_sale_event(
        reference_id=withdrawal_id,
        reference_type=ReferenceType.WITHDRAWAL,
        sign=+1,
        items=items,
        tax=tax,
        total=total,
        job_id=job_id,
        billing_entity=billing_entity,
        contractor_id=contractor_id,
        performed_by_user_id=performed_by_user_id,
        created_at=created_at,
    )


async def record_return(
    return_id: str,
    items: list[LedgerItem],
    tax: float,
    total: float,
    job_id: str,
    billing_entity: str,
    contractor_id: str,
    performed_by_user_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Write reversing entries for a material return."""
    await _record_sale_event(
        reference_id=return_id,
        reference_type=ReferenceType.RETURN,
        sign=-1,
        items=items,
        tax=tax,
        total=total,
        job_id=job_id,
        billing_entity=billing_entity,
        contractor_id=contractor_id,
        performed_by_user_id=performed_by_user_id,
        created_at=created_at,
    )


async def record_po_receipt(
    po_id: str,
    items: list[ReceivedItemSummary],
    vendor_name: str,
    performed_by_user_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Write inventory + AP entries for each received PO line item."""
    if await get_database_manager().finance.ledger_entries_exist(
        get_org_id(), ReferenceType.PO_RECEIPT.value, po_id
    ):
        return
    await _check_fiscal_period()
    journal_id = new_uuid7_str()
    org_id = get_org_id()
    entries: list[FinancialEntry] = []

    for ri in items:
        cost = ri.cost
        delivered = ri.delivered_qty
        amount = round_money(cost * delivered)
        if amount == 0:
            continue

        dept = ri.department
        pid = ri.sku_id
        entries.append(
            FinancialEntry(
                account=Account.INVENTORY,
                amount=amount,
                quantity=delivered,
                unit="each",
                unit_cost=cost,
                journal_id=journal_id,
                department=dept,
                vendor_name=vendor_name,
                sku_id=pid,
                performed_by_user_id=performed_by_user_id,
                reference_type=ReferenceType.PO_RECEIPT,
                reference_id=po_id,
                organization_id=org_id,
            )
        )
        entries.append(
            FinancialEntry(
                account=Account.ACCOUNTS_PAYABLE,
                amount=amount,
                quantity=delivered,
                unit="each",
                unit_cost=cost,
                journal_id=journal_id,
                department=dept,
                vendor_name=vendor_name,
                sku_id=pid,
                performed_by_user_id=performed_by_user_id,
                reference_type=ReferenceType.PO_RECEIPT,
                reference_id=po_id,
                organization_id=org_id,
            )
        )

    if created_at:
        for e in entries:
            e.created_at = created_at
    if entries:
        await get_database_manager().finance.ledger_insert_entries(
            get_org_id(), entries
        )


_DAMAGE_REASONS = {"damage"}
_THEFT_REASONS = {"theft"}


def _offset_account_for_reason(reason: str | None) -> Account:
    """Route negative adjustments to the correct contra-inventory account."""
    if reason in _DAMAGE_REASONS:
        return Account.DAMAGE
    return Account.SHRINKAGE


async def record_adjustment(
    adjustment_ref_id: str,
    sku_id: str,
    product_cost: float,
    quantity_delta: float,
    department: str | None,
    reason: str | None = None,
    performed_by_user_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Write inventory + contra entries for a stock adjustment.

    Negative delta: INVENTORY decreases, offset account (shrinkage or damage) increases.
    Positive delta: INVENTORY increases, offset account decreases (found stock).
    The offset account is determined by reason: 'damage' → DAMAGE, everything else → SHRINKAGE.
    """
    if await get_database_manager().finance.ledger_entries_exist(
        get_org_id(), ReferenceType.ADJUSTMENT.value, adjustment_ref_id
    ):
        return
    await _check_fiscal_period()
    amount = round_money(abs(quantity_delta) * product_cost)
    if amount == 0:
        return

    org_id = get_org_id()
    journal_id = new_uuid7_str()
    sign = -1 if quantity_delta < 0 else 1
    offset_account = _offset_account_for_reason(reason)
    entries = [
        FinancialEntry(
            account=Account.INVENTORY,
            amount=sign * amount,
            journal_id=journal_id,
            department=department,
            sku_id=sku_id,
            performed_by_user_id=performed_by_user_id,
            reference_type=ReferenceType.ADJUSTMENT,
            reference_id=adjustment_ref_id,
            organization_id=org_id,
        ),
        FinancialEntry(
            account=offset_account,
            amount=-sign * amount,
            journal_id=journal_id,
            department=department,
            sku_id=sku_id,
            performed_by_user_id=performed_by_user_id,
            reference_type=ReferenceType.ADJUSTMENT,
            reference_id=adjustment_ref_id,
            organization_id=org_id,
        ),
    ]
    if created_at:
        for e in entries:
            e.created_at = created_at
    await get_database_manager().finance.ledger_insert_entries(
        get_org_id(), entries
    )


async def record_payment(
    withdrawal_id: str,
    amount: float,
    billing_entity: str,
    contractor_id: str,
    performed_by_user_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Write AR reduction when a withdrawal is marked paid."""
    if await get_database_manager().finance.ledger_entries_exist(
        get_org_id(), ReferenceType.PAYMENT.value, withdrawal_id
    ):
        return
    journal_id = new_uuid7_str()
    entry = FinancialEntry(
        account=Account.ACCOUNTS_RECEIVABLE,
        amount=-round_money(amount),
        journal_id=journal_id,
        billing_entity=billing_entity,
        contractor_id=contractor_id,
        performed_by_user_id=performed_by_user_id,
        reference_type=ReferenceType.PAYMENT,
        reference_id=withdrawal_id,
        organization_id=get_org_id(),
    )
    if created_at:
        entry.created_at = created_at
    await get_database_manager().finance.ledger_insert_entries(
        get_org_id(), [entry]
    )


async def record_credit_note_application(
    credit_note_id: str,
    amount: float,
    billing_entity: str,
    contractor_id: str,
    performed_by_user_id: str | None = None,
) -> None:
    """Write AR reduction when a credit note is applied to an invoice."""
    if await get_database_manager().finance.ledger_entries_exist(
        get_org_id(), ReferenceType.CREDIT_NOTE.value, credit_note_id
    ):
        return
    journal_id = new_uuid7_str()
    await get_database_manager().finance.ledger_insert_entries(
        get_org_id(),
        [
            FinancialEntry(
                account=Account.ACCOUNTS_RECEIVABLE,
                amount=-round_money(amount),
                journal_id=journal_id,
                billing_entity=billing_entity,
                contractor_id=contractor_id,
                performed_by_user_id=performed_by_user_id,
                reference_type=ReferenceType.CREDIT_NOTE,
                reference_id=credit_note_id,
                organization_id=get_org_id(),
            ),
        ],
    )
