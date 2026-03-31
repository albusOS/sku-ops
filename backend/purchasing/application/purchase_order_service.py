"""
Purchase order service: create pending POs and receive items into inventory.

Items are saved as pending when a document is reviewed; inventory only updates
on receive. All types are explicit — no dicts flowing across domain boundaries.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from purchasing.domain.purchase_order import (
    CreatePOResult,
    POItemCreate,
    POItemStatus,
    POStatus,
    PurchaseOrder,
    PurchaseOrderItem,
)
from purchasing.infrastructure.po_repo import po_repo as _default_repo
from purchasing.ports.po_repo_port import PORepoPort
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import get_org_id, transaction
from shared.kernel.errors import ResourceNotFoundError
from shared.kernel.types import CurrentUser

logger = logging.getLogger(__name__)


@dataclass
class PurchasingDeps:
    """Cross-domain dependencies injected by the API layer."""

    list_departments: Callable[..., Awaitable[list]]
    get_department_by_code: Callable[..., Awaitable[Any]]
    find_vendor_by_name: Callable[..., Awaitable[Any]]
    insert_vendor: Callable[..., Awaitable[None]]
    get_sku_by_id: Callable[..., Awaitable[Any]]
    find_vendor_item_by_vendor_and_sku_code: Callable[..., Awaitable[Any]]
    find_sku_by_name_and_vendor: Callable[..., Awaitable[Any]]
    update_sku: Callable[..., Awaitable[Any]]
    create_product_with_sku: Callable[..., Awaitable[Any]]
    add_vendor_item: Callable[..., Awaitable[Any]]
    process_receiving_stock_changes: Callable[..., Awaitable[None]]


def _resolve_vendor_dict(vendor_name: str, vendor_id: str) -> dict:
    """Build a minimal vendor insert dict."""
    now = datetime.now(UTC)
    return {
        "id": vendor_id,
        "name": vendor_name,
        "contact_name": "",
        "email": "",
        "phone": "",
        "address": "",
        "created_at": now,
    }


def _resolve_po_item_cost(item: dict) -> float:
    """Derive item cost from cost field, falling back to 70% of unit_price/price."""
    cost = float(item.get("cost") or 0)
    if cost == 0:
        price = float(item.get("unit_price") or item.get("price") or 0)
        cost = round(price * 0.7, 4) if price else 0
    return cost


async def create_purchase_order(
    vendor_name: str,
    products: list[POItemCreate],
    deps: PurchasingDeps,
    current_user: CurrentUser,
    document_date: str | None = None,
    total: float | None = None,
    category_id: str | None = None,
    create_vendor_if_missing: bool = True,
    repo: PORepoPort = _default_repo,
) -> CreatePOResult:
    """Save reviewed receipt items as a pending purchase order.

    Items arrive already enriched by the product intelligence pipeline
    (parse_service). This function persists them as PO line items.
    Inventory is NOT updated here — that happens on receive.
    """
    vendor_name = (vendor_name or "").strip()
    if not vendor_name:
        raise ValueError("Vendor name is required")

    org_id = get_org_id()

    vendor = await deps.find_vendor_by_name(vendor_name)
    if not vendor:
        if not create_vendor_if_missing:
            raise ResourceNotFoundError("Vendor", vendor_name)
        vendor_id = new_uuid7_str()
        vendor_dict = _resolve_vendor_dict(vendor_name, vendor_id)
        vendor_dict["organization_id"] = org_id
        await deps.insert_vendor(vendor_dict)
        vendor_created = True
    else:
        vendor_id = vendor.id
        vendor_name = vendor.name
        vendor_created = False

    override_dept_code = None
    if category_id:
        departments = await deps.list_departments()
        dept_by_id = {d.id: d for d in departments}
        if category_id in dept_by_id:
            override_dept_code = dept_by_id[category_id].code.upper()

    selected = [p for p in products if p.selected]
    selected_dicts = [p.model_dump() for p in selected]

    # Product intelligence (UOM, department, catalog matching) runs at document parse
    # time in parse_service. Items arrive here already enriched. We only apply the
    # department override from category_id if set.
    for item in selected_dicts:
        if override_dept_code:
            item["suggested_department"] = override_dept_code

    po = PurchaseOrder(
        vendor_id=vendor_id,
        vendor_name=vendor_name,
        document_date=document_date,
        total=total,
        status=POStatus.ORDERED,
        created_by_id=current_user.id,
        created_by_name=current_user.name,
        organization_id=org_id,
    )

    po_items: list[PurchaseOrderItem] = []
    for item in selected_dicts:
        cost_val = _resolve_po_item_cost(item)
        po_items.append(
            PurchaseOrderItem(
                po_id=po.id,
                name=item.get("name", "Unknown"),
                original_sku=item.get("original_sku"),
                ordered_qty=float(
                    item.get("ordered_qty") or item.get("quantity") or 1
                ),
                delivered_qty=item.get("delivered_qty") or 0,
                unit_price=float(item.get("price") or 0),
                cost=round(cost_val, 2),
                base_unit=item.get("base_unit") or "each",
                sell_uom=item.get("sell_uom") or "each",
                pack_qty=int(item.get("pack_qty") or 1),
                purchase_uom=item.get("purchase_uom") or "each",
                purchase_pack_qty=int(item.get("purchase_pack_qty") or 1),
                suggested_department=(
                    item.get("suggested_department") or "HDW"
                ).upper(),
                status=POItemStatus.ORDERED,
                sku_id=item.get("sku_id") or None,
                organization_id=org_id,
            )
        )

    async with transaction():
        await repo.insert_po(po)
        await repo.insert_items(po_items)

    logger.info(
        "purchase_order.created",
        extra={
            "org_id": org_id,
            "po_id": po.id,
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "item_count": len(po_items),
            "user_id": current_user.id,
        },
    )

    return CreatePOResult(
        id=po.id,
        vendor_id=vendor_id,
        vendor_created=vendor_created,
        vendor_name=vendor_name,
        status=po.status.value,
        item_count=len(po_items),
        created_at=po.created_at,
    )


# Re-export receiving functions so existing imports from this module keep working
from purchasing.application.po_receiving_service import (  # noqa: E402
    _apply_overrides,
    _match_sku,
    _recompute_po_status,
    mark_delivery_received,
    receive_po_items,
)

__all__ = [
    "CreatePOResult",
    "PurchasingDeps",
    "_apply_overrides",
    "_match_sku",
    "_recompute_po_status",
    "_resolve_po_item_cost",
    "_resolve_vendor_dict",
    "create_purchase_order",
    "mark_delivery_received",
    "receive_po_items",
]
