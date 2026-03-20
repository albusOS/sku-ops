"""
Inventory service: atomic stock operations and stock ledger.

Every quantity change creates an immutable StockTransaction record.
Withdrawals use atomic UPDATE with quantity guard to prevent overselling.
Unit conversion happens here — stock is always stored in the product's base_unit.
"""

from datetime import UTC, datetime
from uuid import uuid4

from catalog.application.queries import (
    add_sku_quantity,
    atomic_adjust_sku,
    atomic_decrement_sku,
    get_sku_by_id,
)
from finance.application.ledger_service import record_adjustment as _record_ledger_adjustment
from inventory.domain.errors import InsufficientStockError, NegativeStockError
from inventory.domain.stock import StockDecrement, StockTransaction, StockTransactionType
from inventory.infrastructure.stock_repo import stock_repo as _default_stock_repo
from inventory.ports.stock_repo_port import StockRepoPort
from shared.infrastructure.database import get_org_id, transaction
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import InventoryChanged
from shared.kernel.errors import ResourceNotFoundError
from shared.kernel.units import are_compatible, convert_quantity

_DISCRETE_SELL_UOMS = frozenset({"pack", "box", "case", "bag", "roll", "kit"})


async def _record_stock_transaction(
    sku_id: str,
    sku: str,
    product_name: str,
    quantity_delta: float,
    quantity_before: float,
    transaction_type: StockTransactionType,
    user_id: str,
    user_name: str,
    reference_id: str | None = None,
    reason: str | None = None,
    unit: str = "each",
    original_quantity: float | None = None,
    original_unit: str | None = None,
    repo: StockRepoPort = _default_stock_repo,
) -> None:
    """Append an immutable transaction to the stock ledger."""
    quantity_after = round(quantity_before + quantity_delta, 6)
    tx = StockTransaction(
        sku_id=sku_id,
        sku=sku,
        product_name=product_name,
        quantity_delta=quantity_delta,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        unit=unit,
        transaction_type=transaction_type,
        reference_id=reference_id,
        reference_type=transaction_type.value,
        reason=reason,
        original_quantity=original_quantity,
        original_unit=original_unit,
        user_id=user_id,
        user_name=user_name,
        organization_id=get_org_id(),
    )
    await repo.insert_transaction(tx)


async def process_withdrawal_stock_changes(
    items: list[StockDecrement],
    withdrawal_id: str,
    user_id: str,
    user_name: str,
) -> None:
    """
    Atomically decrement product quantities for a withdrawal.
    Converts from the requested unit to the product's base_unit before decrementing.
    Uses UPDATE with quantity guard to prevent overselling.
    All decrements and ledger entries are committed atomically — if any item
    fails the quantity guard, the entire transaction rolls back.
    """
    now = datetime.now(UTC)

    # Resolve UOM conversions before entering the transaction (read-only, no side effects).
    resolved: list[tuple[StockDecrement, float, str]] = []
    for item in items:
        product = await get_sku_by_id(item.sku_id)
        base_unit = (product.base_unit if product else "each").lower()
        requested_unit = (item.unit or "each").lower()
        pack_qty = product.pack_qty if product else 1
        if requested_unit != base_unit and are_compatible(requested_unit, base_unit):
            canonical_qty = convert_quantity(item.quantity, requested_unit, base_unit)
        else:
            canonical_qty = item.quantity
        if pack_qty > 1 and requested_unit != base_unit and requested_unit in _DISCRETE_SELL_UOMS:
            canonical_qty = canonical_qty * pack_qty
        resolved.append((item, canonical_qty, base_unit))

    async with transaction():
        for item, canonical_qty, base_unit in resolved:
            product = await get_sku_by_id(item.sku_id)
            result = await atomic_decrement_sku(item.sku_id, canonical_qty, now)

            if not result:
                available = product.quantity if product else 0
                raise InsufficientStockError(
                    sku=item.sku, requested=item.quantity, available=available
                )

            quantity_before = result.quantity + canonical_qty
            await _record_stock_transaction(
                sku_id=item.sku_id,
                sku=item.sku,
                product_name=item.name,
                quantity_delta=-canonical_qty,
                quantity_before=quantity_before,
                transaction_type=StockTransactionType.WITHDRAWAL,
                user_id=user_id,
                user_name=user_name,
                reference_id=withdrawal_id,
                original_quantity=item.quantity,
                original_unit=item.unit or "each",
                unit=base_unit,
            )


async def process_receiving_stock_changes(
    sku_id: str,
    sku: str,
    product_name: str,
    quantity: float,
    user_id: str,
    user_name: str,
    reference_id: str | None = None,
    unit: str = "each",
    transaction_type: StockTransactionType = StockTransactionType.RECEIVING,
    original_quantity: float | None = None,
    original_unit: str | None = None,
) -> None:
    """Add stock (receiving, import, return) and record transaction.

    Converts from the supplied unit to the product's base_unit before adding.
    The quantity increment and ledger entry are committed atomically.
    """
    product = await get_sku_by_id(sku_id)
    base_unit = (product.base_unit if product else "each").lower()
    incoming_unit = (unit or "each").lower()

    if incoming_unit != base_unit and are_compatible(incoming_unit, base_unit):
        canonical_qty = convert_quantity(quantity, incoming_unit, base_unit)
    else:
        canonical_qty = quantity

    now = datetime.now(UTC)
    async with transaction():
        result = await add_sku_quantity(sku_id, canonical_qty, now)
        if not result:
            raise ResourceNotFoundError("Product", sku_id)

        quantity_before = result.quantity - canonical_qty
        await _record_stock_transaction(
            sku_id=sku_id,
            sku=sku,
            product_name=product_name,
            quantity_delta=canonical_qty,
            quantity_before=quantity_before,
            transaction_type=transaction_type,
            user_id=user_id,
            user_name=user_name,
            reference_id=reference_id,
            unit=base_unit,
            original_quantity=original_quantity,
            original_unit=original_unit,
        )


async def process_import_stock_changes(
    sku_id: str,
    sku: str,
    product_name: str,
    quantity: float,
    user_id: str,
    user_name: str,
    unit: str = "each",
) -> None:
    """Record stock added via bulk import (new product creation - no delta from existing)."""
    await _record_stock_transaction(
        sku_id=sku_id,
        sku=sku,
        product_name=product_name,
        quantity_delta=quantity,
        quantity_before=0,
        transaction_type=StockTransactionType.IMPORT,
        user_id=user_id,
        user_name=user_name,
        unit=unit or "each",
    )


async def get_stock_history(
    sku_id: str,
    limit: int = 50,
) -> list[StockTransaction]:
    """Get stock transaction history for a product."""
    return await _default_stock_repo.list_by_product(sku_id, limit)


async def process_adjustment_stock_changes(
    sku_id: str,
    quantity_delta: float,
    reason: str,
    user_id: str,
    user_name: str,
    *,
    emit_event: bool = True,
) -> None:
    """
    Adjust stock (count, damage, correction) and record transaction.
    Uses atomic UPDATE to avoid TOCTOU race conditions.
    """
    quantity_delta = float(quantity_delta)
    if quantity_delta == 0:
        raise ValueError("quantity_delta must not be zero")
    now = datetime.now(UTC)
    product = await get_sku_by_id(sku_id)
    if not product:
        raise ResourceNotFoundError("Product", sku_id)

    base_unit = product.base_unit.lower()
    async with transaction():
        result = await atomic_adjust_sku(sku_id, quantity_delta, now)
        if not result:
            raise NegativeStockError(sku_id, current=product.quantity, delta=quantity_delta)

        quantity_after = result.quantity
        quantity_before = quantity_after - quantity_delta
        adjustment_id = str(uuid4())
        await _record_stock_transaction(
            sku_id=sku_id,
            sku=product.sku,
            product_name=product.name,
            quantity_delta=quantity_delta,
            quantity_before=quantity_before,
            transaction_type=StockTransactionType.ADJUSTMENT,
            user_id=user_id,
            user_name=user_name,
            reference_id=adjustment_id,
            reason=reason,
            unit=base_unit,
        )

        await _record_ledger_adjustment(
            adjustment_ref_id=adjustment_id,
            sku_id=sku_id,
            product_cost=product.cost,
            quantity_delta=quantity_delta,
            department=product.category_name,
            reason=reason,
            performed_by_user_id=user_id,
        )

    if emit_event:
        await dispatch(
            InventoryChanged(
                org_id=get_org_id(),
                sku_ids=(sku_id,),
                change_type="adjustment",
            )
        )


async def restock_as_return(
    sku_id: str,
    sku: str,
    product_name: str,
    quantity: float,
    user_id: str,
    user_name: str,
    reference_id: str | None = None,
    unit: str = "each",
) -> None:
    """Restock inventory as a customer/vendor return (RETURN transaction type)."""
    await process_receiving_stock_changes(
        sku_id=sku_id,
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        user_id=user_id,
        user_name=user_name,
        reference_id=reference_id,
        unit=unit,
        transaction_type=StockTransactionType.RETURN,
    )
