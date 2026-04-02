"""Catalog application queries — compositors only.

Thin reads and writes use ``get_database_manager().catalog`` (and ``transaction``)
at the call site with ``get_org_id()``.
"""

from __future__ import annotations

from catalog.domain.department import Department
from catalog.domain.sku import Sku
from catalog.domain.vendor import Vendor
from catalog.domain.vendor_item import VendorItem
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager


async def get_vendor_items_for_skus(
    sku_ids: list[str],
) -> dict[str, list[VendorItem]]:
    items = await get_database_manager().catalog.list_vendor_items_by_skus(
        get_org_id(), sku_ids
    )
    grouped: dict[str, list[VendorItem]] = {}
    for item in items:
        grouped.setdefault(item.sku_id, []).append(item)
    return grouped


async def find_product_by_original_sku_and_vendor(
    original_sku: str, vendor_id: str
) -> Sku | None:
    """Resolve vendor part number → VendorItem → SKU."""
    cat = get_database_manager().catalog
    oid = get_org_id()
    vi = await cat.find_vendor_item_by_vendor_and_sku(
        oid, vendor_id, original_sku
    )
    if not vi:
        return None
    return await cat.get_sku_by_id(vi.sku_id, oid)


async def sku_vendor_options(sku_id: str) -> list[dict]:
    """All vendors for a SKU with cost, lead time, moq, preferred, and last PO date."""
    org_id = get_org_id()
    cat = get_database_manager().catalog
    pur = get_database_manager().purchasing
    items = await cat.list_vendor_items_by_sku(sku_id, org_id)
    if not items:
        return []

    last_by_vendor = await pur.last_po_created_at_by_vendor_for_sku(
        org_id, sku_id
    )
    result = []
    for vi in items:
        vendor = await cat.get_vendor_by_id(vi.vendor_id, org_id)
        result.append(
            {
                "vendor_id": vi.vendor_id,
                "vendor_name": vendor.name if vendor else vi.vendor_name,
                "vendor_sku": vi.vendor_sku,
                "cost": vi.cost,
                "lead_time_days": vi.lead_time_days,
                "moq": vi.moq,
                "is_preferred": vi.is_preferred,
                "purchase_uom": vi.purchase_uom,
                "purchase_pack_qty": vi.purchase_pack_qty,
                "last_po_date": last_by_vendor.get(vi.vendor_id),
            }
        )
    return result


async def get_known_unit_codes() -> frozenset[str]:
    """Return all active unit codes visible to the current org (global + org-specific)."""
    units = await get_database_manager().catalog.list_uoms(get_org_id())
    return frozenset(u.code for u in units)


async def insert_department(department: Department | dict) -> None:
    d = (
        Department.model_validate(department)
        if isinstance(department, dict)
        else department
    )
    async with transaction():
        await get_database_manager().catalog.insert_department(d)


async def insert_vendor(vendor: Vendor | dict) -> None:
    v = Vendor.model_validate(vendor) if isinstance(vendor, dict) else vendor
    async with transaction():
        await get_database_manager().catalog.insert_vendor(v)
