"""Cycle count repository — delegates to InventoryDatabaseService."""

from datetime import datetime

from inventory.domain.cycle_count import CycleCount, CycleCountItem
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def insert_count(count: CycleCount) -> None:
    db = get_database_manager()
    await db.inventory.insert_cycle_count(count)


async def insert_item(item: CycleCountItem) -> None:
    db = get_database_manager()
    await db.inventory.insert_cycle_count_item(item)


async def update_item_counted(
    item_id: str,
    counted_qty: float,
    variance: float,
    notes: str | None,
) -> CycleCountItem | None:
    db = get_database_manager()
    return await db.inventory.update_cycle_count_item_counted(
        get_org_id(),
        item_id,
        counted_qty,
        variance,
        notes,
    )


async def commit_count(
    count_id: str,
    committed_by_id: str,
    committed_at: datetime | str,
) -> bool:
    """Atomically transition status open -> committed. Returns False if already committed."""
    db = get_database_manager()
    ts = committed_at
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return await db.inventory.commit_cycle_count(
        get_org_id(), count_id, committed_by_id, ts
    )


async def get_count(count_id: str) -> CycleCount | None:
    db = get_database_manager()
    got = await db.inventory.get_cycle_count(get_org_id(), count_id)
    if got is None:
        return None
    return CycleCount.model_validate(got.model_dump())


async def list_counts(status: str | None = None) -> list[CycleCount]:
    db = get_database_manager()
    rows = await db.inventory.list_cycle_counts(get_org_id(), status=status)
    return [CycleCount.model_validate(r.model_dump()) for r in rows]


async def list_items(cycle_count_id: str) -> list[CycleCountItem]:
    db = get_database_manager()
    rows = await db.inventory.list_cycle_count_items(
        get_org_id(), cycle_count_id
    )
    return [CycleCountItem.model_validate(r.model_dump()) for r in rows]


async def get_item(item_id: str, cycle_count_id: str) -> CycleCountItem | None:
    db = get_database_manager()
    got = await db.inventory.get_cycle_count_item(
        get_org_id(), item_id, cycle_count_id
    )
    if got is None:
        return None
    return CycleCountItem.model_validate(got.model_dump())
