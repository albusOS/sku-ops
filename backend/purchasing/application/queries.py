"""Purchasing application queries — safe for cross-context import.

Other bounded contexts import from here, never from purchasing.infrastructure directly.
"""

from datetime import datetime
from typing import TypedDict

from purchasing.domain.purchase_order import POItemRow, PORow, VendorPerformance
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


class VendorCatalogRow(TypedDict):
    vendor_sku: str | None
    cost: float
    lead_time_days: int | None
    moq: float | None
    is_preferred: bool
    purchase_uom: str
    purchase_pack_qty: int
    sku: str
    name: str
    quantity: float
    min_stock: int
    sell_uom: str
    department: str


class PurchaseHistoryItem(TypedDict):
    id: str
    vendor_name: str
    document_date: str | None
    total: float | None
    status: str
    created_at: datetime
    received_at: datetime | None
    items: list[dict]
    item_count: int


class ReorderRow(TypedDict):
    sku_id: str
    sku: str
    name: str
    quantity: float
    min_stock: int
    current_cost: float
    sell_uom: str
    department: str
    vendor_options: list[dict]
    deficit: float


def _db_purchasing():
    return get_database_manager().purchasing


def _db_catalog():
    return get_database_manager().catalog


async def get_po_with_cost(po_id: str) -> dict | None:
    return await _db_purchasing().get_po_with_cost(get_org_id(), po_id)


async def list_unsynced_po_bills() -> list[dict]:
    return await _db_purchasing().list_unsynced_po_bills(get_org_id())


async def list_failed_po_bills() -> list[dict]:
    return await _db_purchasing().list_failed_po_bills(get_org_id())


async def set_xero_sync_status(
    po_id: str, status: str, updated_at: datetime
) -> None:
    await _db_purchasing().set_po_xero_sync_status(
        get_org_id(), po_id, status, updated_at
    )


async def set_xero_bill_id(
    po_id: str, xero_bill_id: str, updated_at: datetime
) -> None:
    await _db_purchasing().set_po_xero_bill_id(
        get_org_id(), po_id, xero_bill_id, updated_at
    )


async def po_summary_by_status() -> dict[str, dict]:
    """PO count and total grouped by status. Used by dashboard."""
    return await _db_purchasing().po_summary_by_status(get_org_id())


async def list_pos(status: str | None = None) -> list[PORow]:
    return await _db_purchasing().list_pos(get_org_id(), status=status)


async def list_pos_with_counts(status: str | None = None) -> list[PORow]:
    return await _db_purchasing().list_pos_with_counts(
        get_org_id(), status=status
    )


async def get_po(po_id: str) -> PORow | None:
    return await _db_purchasing().get_po(get_org_id(), po_id)


async def get_po_items(po_id: str) -> list[POItemRow]:
    items = await _db_purchasing().get_po_items(get_org_id(), po_id)
    sku_ids = [i.sku_id for i in items if i.sku_id]
    if not sku_ids:
        return items
    products = {}
    for pid in set(sku_ids):
        p = await _db_catalog().get_sku_by_id(pid, get_org_id())
        if p:
            products[pid] = p
    enriched = []
    for item in items:
        pid = item.sku_id
        if pid and pid in products:
            p = products[pid]
            enriched.append(
                item.model_copy(
                    update={
                        "matched_sku": p.sku,
                        "matched_name": p.name,
                        "matched_quantity": p.quantity,
                        "matched_cost": p.cost,
                    }
                )
            )
        else:
            enriched.append(item)
    return enriched


# ── Agent-facing analytics queries ───────────────────────────────────────────


async def vendor_catalog(vendor_id: str) -> list[VendorCatalogRow]:
    """SKUs supplied by a vendor with cost, lead time, moq, preferred status."""
    return await _db_purchasing().vendor_catalog(get_org_id(), vendor_id)


async def vendor_performance(
    vendor_id: str, days: int = 90, vendor_name: str = ""
) -> VendorPerformance:
    """PO count, total spend, avg lead time, fill rate for a vendor."""
    return await _db_purchasing().vendor_performance(
        get_org_id(), vendor_id, days=days, vendor_name=vendor_name
    )


async def purchase_history(
    vendor_id: str, days: int = 90, limit: int = 20
) -> list[PurchaseHistoryItem]:
    """Recent POs for a vendor with item summaries."""
    return await _db_purchasing().purchase_history(
        get_org_id(), vendor_id, days=days, limit=limit
    )


async def reorder_with_vendor_context(limit: int = 30) -> list[ReorderRow]:
    """Low-stock SKUs enriched with vendor options for procurement planning."""
    return await _db_purchasing().reorder_with_vendor_context(
        get_org_id(), limit=limit
    )
