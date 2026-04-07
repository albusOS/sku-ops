"""Return service: validate against original withdrawal, restock, emit events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from finance.application.ledger_service import (
    record_return as _record_return_ledger,
)
from inventory.application.inventory_service import restock_as_return
from operations.domain.returns import MaterialReturn, ReturnCreate, ReturnItem
from shared.infrastructure.db import get_org_id, get_session, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.domain_events import dispatch
from shared.infrastructure.types.public_sql_model_models import Withdrawals
from shared.kernel.domain_events import InventoryChanged, ReturnCreated
from shared.kernel.errors import DomainError, ResourceNotFoundError
from shared.kernel.event_payloads import LedgerItem

if TYPE_CHECKING:
    from shared.kernel.types import CurrentUser


def _db_operations():
    return get_database_manager().operations


def _db_finance():
    return get_database_manager().finance


async def create_return(
    data: ReturnCreate,
    current_user: CurrentUser,
) -> MaterialReturn:
    """Process a return against a previous withdrawal.

    The transaction writes: inventory restock, return row, ledger entries.
    All three commit atomically — a failure rolls back all three.

    Post-commit (best-effort): credit note creation, WS push.
    """
    org_id = current_user.organization_id
    db = _db_operations()
    settings = await _db_finance().org_settings_get(get_org_id())
    tax_rate = settings.default_tax_rate

    withdrawal = await db.get_withdrawal_by_id(org_id, data.withdrawal_id)
    if not withdrawal:
        raise ResourceNotFoundError("Withdrawal", data.withdrawal_id)

    w_item_map: dict[str, object] = {}
    for wi in withdrawal.items:
        if wi.sku_id not in w_item_map:
            w_item_map[wi.sku_id] = wi
        else:
            prev = w_item_map[wi.sku_id]
            w_item_map[wi.sku_id] = wi.model_copy(update={"quantity": prev.quantity + wi.quantity})

    w_dept_map = {wi.sku_id: getattr(wi, "category_name", None) for wi in withdrawal.items}

    ret = MaterialReturn(
        withdrawal_id=data.withdrawal_id,
        contractor_id=withdrawal.contractor_id,
        contractor_name=withdrawal.contractor_name,
        billing_entity=withdrawal.billing_entity,
        job_id=withdrawal.job_id,
        items=[],  # filled after validation inside transaction
        reason=data.reason,
        notes=data.notes,
        processed_by_id=current_user.id,
        processed_by_name=current_user.name,
        organization_id=org_id,
    )

    enriched_items: list[ReturnItem] = []
    sku_ids: tuple[str, ...] = ()
    ledger_items: tuple[LedgerItem, ...] = ()

    async with transaction():
        # Lock the withdrawal row to serialize concurrent returns for the same withdrawal.
        async with get_session() as session:
            await session.execute(
                select(Withdrawals.id)
                .where(
                    Withdrawals.id == as_uuid_required(data.withdrawal_id),
                    Withdrawals.organization_id == as_uuid_required(org_id),
                )
                .with_for_update()
            )

        # Re-read already-returned quantities inside the transaction (after lock).
        existing_returns = await db.list_returns_by_withdrawal(org_id, data.withdrawal_id)
        already_returned: dict[str, float] = {}
        for er in existing_returns:
            for ri in er.items:
                already_returned[ri.sku_id] = already_returned.get(ri.sku_id, 0) + ri.quantity

        enriched_items = []
        for item in data.items:
            original = w_item_map.get(item.sku_id)
            if not original:
                raise DomainError(f"Product {item.sku_id} ({item.sku}) not on original withdrawal")

            max_returnable = original.quantity - already_returned.get(item.sku_id, 0)
            if item.quantity > max_returnable:
                raise DomainError(
                    f"Cannot return {item.quantity} of {item.name} — "
                    f"max returnable is {max_returnable}"
                )

            enriched_items.append(
                item.model_copy(
                    update={
                        "unit_price": item.unit_price or original.unit_price,
                        "cost": item.cost or original.cost,
                        "unit": item.unit or original.unit,
                    }
                )
            )

        ret.items = enriched_items
        ret.compute_totals(tax_rate=tax_rate)

        sku_ids = tuple(item.sku_id for item in enriched_items)
        ledger_items = tuple(
            LedgerItem(
                sku_id=item.sku_id,
                quantity=item.quantity,
                unit=item.unit or "each",
                unit_price=item.unit_price,
                cost=item.cost,
                category_name=w_dept_map.get(item.sku_id),
            )
            for item in enriched_items
        )

        for item in enriched_items:
            await restock_as_return(
                sku_id=item.sku_id,
                sku=item.sku,
                product_name=item.name,
                quantity=item.quantity,
                user_id=current_user.id,
                user_name=current_user.name,
                reference_id=ret.id,
                unit=item.unit,
            )
        await db.insert_return(org_id, ret)
        await _record_return_ledger(
            return_id=ret.id,
            items=list(ledger_items),
            tax=ret.tax,
            total=ret.total,
            job_id=withdrawal.job_id or "",
            billing_entity=withdrawal.billing_entity or "",
            contractor_id=withdrawal.contractor_id,
            performed_by_user_id=current_user.id,
        )

    await dispatch(
        ReturnCreated(
            org_id=org_id,
            return_id=ret.id,
            withdrawal_id=data.withdrawal_id,
            contractor_id=withdrawal.contractor_id,
            job_id=withdrawal.job_id or "",
            billing_entity=withdrawal.billing_entity or "",
            tax=ret.tax,
            total=ret.total,
            performed_by_user_id=current_user.id,
            sku_ids=sku_ids,
            ledger_items=ledger_items,
            invoice_id=withdrawal.invoice_id,
        )
    )
    await dispatch(
        InventoryChanged(
            org_id=org_id,
            sku_ids=sku_ids,
            change_type="return",
        )
    )

    return ret
