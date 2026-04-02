"""Cycle count application service.

Lifecycle:
  open  → counters enter counted_qty line by line
        → get_count_detail for live variance preview
  commit → applies all non-zero variances as stock adjustments inside a single
           database transaction (all-or-nothing), then transitions status to
           committed in the same transaction.

The snapshot (snapshot_qty) is frozen at open time and never changed.
Inventory is only touched at commit — never during the counting phase.
"""

from datetime import UTC, datetime

from inventory.application.inventory_service import (
    process_adjustment_stock_changes,
)
from inventory.domain.cycle_count import (
    CommitCycleCountResult,
    CycleCount,
    CycleCountDetail,
    CycleCountItem,
    CycleCountStatus,
)
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import InventoryChanged
from shared.kernel.errors import ResourceNotFoundError


def _inv():
    return get_database_manager().inventory


async def _get_count(count_id: str) -> CycleCount | None:
    return await _inv().get_cycle_count(get_org_id(), count_id)


async def open_cycle_count(
    created_by_id: str,
    created_by_name: str,
    scope: str | None = None,
) -> CycleCount:
    """Open a new cycle count session.

    Snapshots the current quantity of every active product in scope.
    scope=None counts everything; scope=<category_name> limits to that category.
    Returns the new CycleCount.
    """
    products = await get_database_manager().catalog.list_skus(get_org_id())
    if scope:
        products = [p for p in products if p.category_name == scope]

    if not products:
        raise ValueError(
            f"No products found{f' in department {scope!r}' if scope else ''}. "
            "Cannot open an empty cycle count."
        )

    count = CycleCount(
        organization_id=get_org_id(),
        scope=scope,
        created_by_id=created_by_id,
        created_by_name=created_by_name,
    )

    async with transaction():
        await _inv().insert_cycle_count(count)
        for p in products:
            item = CycleCountItem(
                cycle_count_id=count.id,
                sku_id=p.id,
                sku=p.sku,
                product_name=p.name,
                snapshot_qty=p.quantity,
                unit=p.base_unit or "each",
            )
            await _inv().insert_cycle_count_item(item)

    return count


async def update_counted_qty(
    count_id: str,
    item_id: str,
    counted_qty: float,
    notes: str | None,
) -> CycleCountItem:
    """Record the physical count for one line item.

    Computes variance = counted_qty - snapshot_qty inline.
    The count must still be open.
    """
    count = await _get_count(count_id)
    if not count:
        raise ResourceNotFoundError("CycleCount", count_id)
    if count.status != CycleCountStatus.OPEN:
        raise ValueError("Cannot update a committed cycle count.")

    item = await _inv().get_cycle_count_item(get_org_id(), item_id, count_id)
    if item is None:
        raise ResourceNotFoundError("CycleCountItem", item_id)

    variance = counted_qty - item.snapshot_qty
    updated = await _inv().update_cycle_count_item_counted(
        get_org_id(),
        item_id,
        counted_qty,
        variance,
        notes,
    )
    if not updated:
        raise ResourceNotFoundError("CycleCountItem", item_id)
    return updated


async def get_count_detail(count_id: str) -> CycleCountDetail:
    """Return the count header plus all line items with their current variance."""
    count = await _get_count(count_id)
    if not count:
        raise ResourceNotFoundError("CycleCount", count_id)

    items = await _inv().list_cycle_count_items(get_org_id(), count_id)
    return CycleCountDetail(
        id=count.id,
        organization_id=count.organization_id,
        status=count.status,
        scope=count.scope,
        created_by_id=count.created_by_id,
        created_by_name=count.created_by_name,
        committed_by_id=count.committed_by_id,
        committed_at=count.committed_at,
        created_at=count.created_at,
        items=items,
    )


async def commit_cycle_count(
    count_id: str,
    committed_by_id: str,
    committed_by_name: str,
) -> CommitCycleCountResult:
    """Apply all non-zero variances as stock adjustments and close the count.

    All adjustments and the status transition run inside a single database
    transaction. If any adjustment fails (e.g. NegativeStockError), the entire
    commit is rolled back — no partial state is ever written.

    Items without a counted_qty are skipped (uncounted = no adjustment).
    Items with variance == 0 are skipped (no change needed).
    """
    count = await _get_count(count_id)
    if not count:
        raise ResourceNotFoundError("CycleCount", count_id)
    if count.status != CycleCountStatus.OPEN:
        raise ValueError("Cycle count is already committed.")

    items = await _inv().list_cycle_count_items(get_org_id(), count_id)
    items_to_adjust = [
        i
        for i in items
        if i.counted_qty is not None and i.variance not in (None, 0, 0.0)
    ]

    committed_at = datetime.now(UTC)

    adjusted_sku_ids: list[str] = []
    async with transaction():
        # Flip status first — if another request already committed, abort before
        # touching stock. Stock adjustments only proceed if this transaction wins
        # the conditional UPDATE.
        committed = await _inv().commit_cycle_count(
            get_org_id(),
            count_id,
            committed_by_id,
            committed_at,
        )
        if not committed:
            raise ValueError("Cycle count is already committed.")
        for item in items_to_adjust:
            await process_adjustment_stock_changes(
                sku_id=item.sku_id,
                quantity_delta=item.variance,
                reason="count",
                user_id=committed_by_id,
                user_name=committed_by_name,
                emit_event=False,
            )
            adjusted_sku_ids.append(item.sku_id)

    if adjusted_sku_ids:
        await dispatch(
            InventoryChanged(
                org_id=get_org_id(),
                sku_ids=tuple(adjusted_sku_ids),
                change_type="cycle_count",
            )
        )

    return CommitCycleCountResult(
        id=count.id,
        organization_id=count.organization_id,
        status=CycleCountStatus.COMMITTED,
        scope=count.scope,
        created_by_id=count.created_by_id,
        created_by_name=count.created_by_name,
        committed_by_id=committed_by_id,
        committed_at=committed_at,
        created_at=count.created_at,
        items_adjusted=len(items_to_adjust),
    )


async def list_cycle_counts(status: str | None = None) -> list[CycleCount]:
    return await _inv().list_cycle_counts(get_org_id(), status=status)
