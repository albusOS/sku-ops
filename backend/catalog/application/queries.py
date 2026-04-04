"""Catalog application queries — cross-context compositors only.

Single-context reads and writes use the catalog and purchasing database
services (and ``transaction``) at the call site with ``get_org_id()``.
"""

from __future__ import annotations

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _db_catalog():
    return get_database_manager().catalog


def _db_purchasing():
    return get_database_manager().purchasing


async def sku_vendor_options(sku_id: str) -> list[dict]:
    """All vendors for a SKU with cost, lead time, moq, preferred, and last PO date."""
    org_id = get_org_id()
    cat = _db_catalog()
    pur = _db_purchasing()
    items = await cat.list_vendor_items_by_sku(sku_id, org_id)
    if not items:
        return []

    last_by_vendor = await pur.last_po_created_at_by_vendor_for_sku(org_id, sku_id)
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
