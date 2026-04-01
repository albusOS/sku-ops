"""Vendor item lifecycle: manage vendor-to-SKU relationships.

Each VendorItem links a vendor to a specific SKU with the vendor's
part number, purchase UOM, cost, lead time, and preferred status.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from catalog.domain.vendor_item import VendorItem
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


async def add_vendor_item(
    sku_id: str,
    vendor_id: str,
    vendor_sku: str | None = None,
    purchase_uom: str = "each",
    purchase_pack_qty: int = 1,
    cost: float = 0.0,
    lead_time_days: int | None = None,
    moq: float | None = None,
    is_preferred: bool = False,
    notes: str | None = None,
) -> VendorItem:
    """Add a vendor relationship to a SKU."""
    org_id = get_org_id()
    cat = get_database_manager().catalog

    vendor = await cat.get_vendor_by_id(vendor_id, org_id)
    vendor_name = vendor.name if vendor else ""

    item = VendorItem(
        vendor_id=vendor_id,
        vendor_name=vendor_name,
        sku_id=sku_id,
        vendor_sku=vendor_sku,
        purchase_uom=purchase_uom,
        purchase_pack_qty=purchase_pack_qty,
        cost=cost,
        lead_time_days=lead_time_days,
        moq=moq,
        is_preferred=is_preferred,
        notes=notes,
        organization_id=org_id,
    )

    async with transaction():
        if is_preferred:
            await cat.clear_preferred_vendor_items_for_sku(sku_id, org_id)
        await cat.insert_vendor_item(item)

    logger.info(
        "vendor_item.added",
        extra={
            "org_id": org_id,
            "vendor_item_id": item.id,
            "sku_id": sku_id,
            "vendor_id": vendor_id,
            "is_preferred": is_preferred,
        },
    )
    return item


async def update_vendor_item(
    item_id: str,
    updates: dict,
) -> VendorItem:
    """Update a vendor item."""
    org_id = get_org_id()
    cat = get_database_manager().catalog
    existing = await cat.get_vendor_item_by_id(item_id, org_id)
    if not existing:
        raise ResourceNotFoundError("VendorItem", item_id)

    payload = {
        **updates,
        "updated_at": updates.get("updated_at") or datetime.now(UTC),
    }
    async with transaction():
        if updates.get("is_preferred"):
            await cat.clear_preferred_vendor_items_for_sku(
                existing.sku_id, org_id
            )
        result = await cat.update_vendor_item(item_id, org_id, payload)
    if not result:
        raise ResourceNotFoundError("VendorItem", item_id)
    logger.info(
        "vendor_item.updated",
        extra={"org_id": org_id, "vendor_item_id": item_id},
    )
    return result


async def remove_vendor_item(item_id: str) -> None:
    """Soft-delete a vendor item."""
    org_id = get_org_id()
    cat = get_database_manager().catalog
    existing = await cat.get_vendor_item_by_id(item_id, org_id)
    if not existing:
        raise ResourceNotFoundError("VendorItem", item_id)
    async with transaction():
        await cat.soft_delete_vendor_item(item_id, org_id)
    logger.info(
        "vendor_item.removed",
        extra={
            "org_id": org_id,
            "vendor_item_id": item_id,
            "sku_id": existing.sku_id,
        },
    )


async def set_preferred_vendor(sku_id: str, vendor_item_id: str) -> None:
    """Set a specific vendor item as the preferred supplier for a SKU."""
    org_id = get_org_id()
    cat = get_database_manager().catalog
    item = await cat.get_vendor_item_by_id(vendor_item_id, org_id)
    if not item or item.sku_id != sku_id:
        raise ResourceNotFoundError("VendorItem", vendor_item_id)

    async with transaction():
        await cat.clear_preferred_vendor_items_for_sku(sku_id, org_id)
        await cat.update_vendor_item(
            vendor_item_id,
            org_id,
            {"is_preferred": True, "updated_at": datetime.now(UTC)},
        )
    logger.info(
        "vendor_item.preferred_set",
        extra={
            "org_id": org_id,
            "vendor_item_id": vendor_item_id,
            "sku_id": sku_id,
        },
    )
