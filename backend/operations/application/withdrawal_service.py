"""Withdrawal service: encapsulates creation and payment workflows for material withdrawals."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from finance.application.invoice_service import (
    create_invoice_from_withdrawals as _create_invoice,
)
from finance.application.invoice_service import (
    mark_paid_for_withdrawal as _mark_invoice_paid,
)
from finance.application.ledger_service import (
    record_payment as _record_payment_ledger,
)
from finance.application.ledger_service import (
    record_withdrawal as _record_withdrawal_ledger,
)
from inventory.application.inventory_service import (
    process_withdrawal_stock_changes,
)
from operations.domain.enums import PaymentStatus
from operations.domain.withdrawal import (
    ContractorContext,
    MaterialWithdrawal,
    MaterialWithdrawalCreate,
)
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import (
    InventoryChanged,
    WithdrawalCreated,
    WithdrawalPaid,
)
from shared.kernel.event_payloads import LedgerItem
from shared.kernel.stock import StockDecrement
from shared.kernel.units import (
    are_compatible,
    convert_quantity,
    cost_per_sell_unit,
)

if TYPE_CHECKING:
    from shared.kernel.types import CurrentUser

logger = logging.getLogger(__name__)


def _db_operations():
    return get_database_manager().operations


def _db_finance():
    return get_database_manager().finance


def _convert_price_per_unit(
    price_per_base: float,
    base_unit: str,
    requested_unit: str,
) -> float:
    """Convert a per-base_unit price to a per-requested_unit price.

    1 yard = 3 feet, so price_per_foot = price_per_yard / 3.
    Generalized: convert 1 of requested_unit to base_unit to get the ratio.
    """
    if base_unit == requested_unit:
        return price_per_base
    if not are_compatible(base_unit, requested_unit):
        return price_per_base
    base_qty_per_one_requested = convert_quantity(1, requested_unit, base_unit)
    return round(price_per_base * base_qty_per_one_requested, 6)


async def create_withdrawal(
    data: MaterialWithdrawalCreate,
    contractor: ContractorContext,
    current_user: CurrentUser,
    *,
    tax_rate: float = 0.10,
) -> MaterialWithdrawal:
    """Create a material withdrawal.

    The transaction writes: stock decrement, withdrawal row, ledger entries.
    All three commit atomically — a failure rolls back all three.

    Post-commit (best-effort, non-atomic): auto-invoice creation, WS push,
    low-stock reorder check. These use domain event handlers. Failure is
    logged and does not affect the withdrawal or ledger.
    """
    if not contractor.id:
        raise ValueError("contractor.id must not be empty")

    org_id = current_user.organization_id
    dbm = get_database_manager()
    db = dbm.operations
    job_uuid = data.job_id
    if data.job_id:
        row = await dbm.jobs.ensure_job(data.job_id, org_id)
        job_uuid = str(row.id)
    products = await dbm.catalog.list_skus(get_org_id())
    product_map = {p.id: p for p in products}
    dept_map = {p.id: p.category_name for p in products}
    enriched_items = []
    for item in data.items:
        p = product_map.get(item.sku_id)
        base_unit = (p.base_unit if p else "each").lower()
        req_unit = (item.unit or base_unit).lower()
        sell_uom = (p.sell_uom if p else base_unit).lower()
        pack_qty = p.pack_qty if p else 1

        updates: dict = {}
        p_cost = p.cost if p else 0
        p_price = p.price if p else 0

        if item.cost == 0.0 and p_cost:
            updates["cost"] = _convert_price_per_unit(
                p_cost, base_unit, req_unit
            )
        elif (
            item.cost != 0.0
            and req_unit != base_unit
            and are_compatible(base_unit, req_unit)
        ):
            updates["cost"] = _convert_price_per_unit(
                p_cost or item.cost, base_unit, req_unit
            )

        if item.unit_price == 0.0 and p_price:
            updates["unit_price"] = _convert_price_per_unit(
                p_price, base_unit, req_unit
            )
        elif (
            item.unit_price != 0.0
            and req_unit != base_unit
            and are_compatible(base_unit, req_unit)
        ):
            updates["unit_price"] = _convert_price_per_unit(
                p_price or item.unit_price, base_unit, req_unit
            )

        updates["sell_uom"] = sell_uom
        updates["sell_cost"] = cost_per_sell_unit(
            p_cost, base_unit, sell_uom, pack_qty
        )

        item = item.model_copy(update=updates)
        enriched_items.append(item)
    data = data.model_copy(update={"items": enriched_items, "job_id": job_uuid})

    billing_entity_name = contractor.billing_entity
    billing_entity_id = contractor.billing_entity_id
    if billing_entity_name and not billing_entity_id:
        be = await dbm.finance.billing_entity_ensure(
            org_id, billing_entity_name
        )
        billing_entity_id = be.id if be else None

    withdrawal = MaterialWithdrawal(
        items=data.items,
        job_id=job_uuid,
        service_address=data.service_address,
        notes=data.notes,
        subtotal=0,
        tax=0,
        total=0,
        cost_total=0,
        contractor_id=contractor.id,
        contractor_name=contractor.name,
        contractor_company=contractor.company,
        billing_entity=billing_entity_name,
        billing_entity_id=billing_entity_id,
        payment_status=PaymentStatus.UNPAID,
        processed_by_id=current_user.id,
        processed_by_name=current_user.name,
        organization_id=org_id,
    )
    withdrawal.compute_totals(tax_rate=tax_rate)

    sku_ids = tuple(i.sku_id for i in data.items)
    ledger_items = tuple(
        LedgerItem(
            sku_id=i.sku_id,
            quantity=i.quantity,
            unit=i.unit or "each",
            unit_price=i.unit_price,
            cost=i.cost,
            sell_uom=i.sell_uom,
            sell_cost=i.sell_cost,
            category_name=dept_map.get(i.sku_id),
        )
        for i in data.items
    )

    async with transaction():
        decrements = [
            StockDecrement(
                sku_id=i.sku_id,
                sku=i.sku,
                name=i.name,
                quantity=i.quantity,
                unit=i.unit or "each",
            )
            for i in data.items
        ]
        await process_withdrawal_stock_changes(
            items=decrements,
            withdrawal_id=withdrawal.id,
            user_id=current_user.id,
            user_name=current_user.name,
        )

        await db.insert_withdrawal(org_id, withdrawal)

        await _record_withdrawal_ledger(
            withdrawal_id=withdrawal.id,
            items=list(ledger_items),
            tax=withdrawal.tax,
            total=withdrawal.total,
            job_id=withdrawal.job_id or "",
            billing_entity=withdrawal.billing_entity or "",
            contractor_id=contractor.id,
            performed_by_user_id=current_user.id,
        )

        await _create_invoice(withdrawal_ids=[withdrawal.id])

    await dispatch(
        WithdrawalCreated(
            org_id=org_id,
            withdrawal_id=withdrawal.id,
            sku_ids=sku_ids,
            contractor_id=contractor.id,
            job_id=withdrawal.job_id or "",
            billing_entity=withdrawal.billing_entity or "",
            tax=withdrawal.tax,
            total=withdrawal.total,
            performed_by_user_id=current_user.id,
            ledger_items=ledger_items,
        )
    )
    await dispatch(
        InventoryChanged(
            org_id=org_id,
            sku_ids=sku_ids,
            change_type="withdrawal",
        )
    )

    return withdrawal


async def create_withdrawal_wired(
    data: MaterialWithdrawalCreate,
    contractor: ContractorContext,
    current_user: CurrentUser,
) -> MaterialWithdrawal:
    """Wired version that resolves org settings before delegating to create_withdrawal."""
    settings = await _db_finance().org_settings_get(get_org_id())
    return await create_withdrawal(
        data,
        contractor,
        current_user,
        tax_rate=settings.default_tax_rate,
    )


async def mark_single_withdrawal_paid(
    withdrawal_id: str,
    performed_by_user_id: str,
    *,
    organization_id: str,
) -> MaterialWithdrawal:
    """Mark a withdrawal as paid.

    The transaction writes: withdrawal status → paid, invoice status → paid,
    payment ledger entry. All three commit atomically.

    Post-commit (best-effort): WithdrawalPaid dispatched for WS notification.
    """
    db = _db_operations()
    withdrawal = await db.get_withdrawal_by_id(organization_id, withdrawal_id)
    if not withdrawal:
        raise ValueError(f"Withdrawal {withdrawal_id} not found")
    paid_at = datetime.now(UTC)

    async with transaction():
        result, changed = await db.mark_withdrawal_paid(
            organization_id, withdrawal_id, paid_at
        )
        if not result:
            raise ValueError(
                f"Withdrawal {withdrawal_id} could not be marked paid"
            )
        if changed:
            await _mark_invoice_paid(withdrawal_id)
            await _record_payment_ledger(
                withdrawal_id=withdrawal_id,
                amount=withdrawal.total,
                billing_entity=withdrawal.billing_entity or "",
                contractor_id=withdrawal.contractor_id,
                performed_by_user_id=performed_by_user_id,
            )

    if changed:
        await dispatch(
            WithdrawalPaid(
                org_id=withdrawal.organization_id,
                withdrawal_id=withdrawal_id,
                amount=withdrawal.total,
                billing_entity=withdrawal.billing_entity or "",
                contractor_id=withdrawal.contractor_id,
                performed_by_user_id=performed_by_user_id,
            )
        )
    return result


async def bulk_mark_withdrawals_paid(
    withdrawal_ids: list[str],
    performed_by_user_id: str,
    *,
    organization_id: str,
) -> int:
    """Mark multiple withdrawals as paid in bulk.

    The transaction writes: all withdrawal statuses → paid, all invoices → paid,
    a payment ledger entry for each withdrawal. All commit atomically or not at all.

    Post-commit (best-effort): WithdrawalPaid dispatched per withdrawal for WS notification.
    """
    if len(withdrawal_ids) > 200:
        raise ValueError("Cannot mark more than 200 withdrawals at once")

    paid_at = datetime.now(UTC)

    db = _db_operations()
    # Fetch before the transaction so we have the data needed for ledger entries
    withdrawals = []
    for wid in withdrawal_ids:
        w = await db.get_withdrawal_by_id(organization_id, wid)
        if w:
            withdrawals.append(w)

    changed_ids: set[str] = set()
    async with transaction():
        changed_ids = set(
            await db.bulk_mark_withdrawals_paid(
                organization_id, withdrawal_ids, paid_at
            )
        )
        for w in withdrawals:
            if w.id not in changed_ids:
                continue
            await _mark_invoice_paid(w.id)
            await _record_payment_ledger(
                withdrawal_id=w.id,
                amount=w.total,
                billing_entity=w.billing_entity or "",
                contractor_id=w.contractor_id,
                performed_by_user_id=performed_by_user_id,
            )

    for w in withdrawals:
        if w.id not in changed_ids:
            continue
        await dispatch(
            WithdrawalPaid(
                org_id=w.organization_id,
                withdrawal_id=w.id,
                amount=w.total,
                billing_entity=w.billing_entity or "",
                contractor_id=w.contractor_id,
                performed_by_user_id=performed_by_user_id,
            )
        )
    return len(changed_ids)
