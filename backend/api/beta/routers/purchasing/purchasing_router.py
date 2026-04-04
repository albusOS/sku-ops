"""Purchase order API routes."""

import logging

from fastapi import APIRouter, HTTPException, Request

from catalog.application.sku_lifecycle import (
    create_product_with_sku as lifecycle_create,
)
from catalog.domain.sku import SkuUpdate
from catalog.domain.vendor import Vendor
from finance.application.po_sync_service import queue_po_for_sync
from inventory.application.inventory_service import (
    process_receiving_stock_changes,
)
from purchasing.application.purchase_order_service import (
    PurchasingDeps,
    create_purchase_order,
    mark_delivery_received,
    receive_po_items,
)
from purchasing.application.queries import (
    get_po,
    get_po_items,
    list_pos_with_counts,
)
from purchasing.domain.purchase_order import (
    CreatePORequest,
    MarkDeliveryRequest,
    ReceiveItemsRequest,
)
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log

logger = logging.getLogger(__name__)


def _db_catalog():
    return get_database_manager().catalog


def _build_deps() -> PurchasingDeps:
    async def list_departments():
        return await _db_catalog().list_departments(get_org_id())

    async def get_department_by_code(code: str):
        return await _db_catalog().get_department_by_code(code, get_org_id())

    async def find_vendor_by_name(name: str):
        return await _db_catalog().find_vendor_by_name(get_org_id(), name)

    async def get_sku_by_id(sku_id: str):
        return await _db_catalog().get_sku_by_id(sku_id, get_org_id())

    async def find_vendor_item_by_vendor_and_sku_code(vendor_id: str, vendor_sku: str):
        return await _db_catalog().find_vendor_item_by_vendor_and_sku(get_org_id(), vendor_id, vendor_sku)

    async def find_sku_by_name_and_vendor(name: str, vendor_id: str):
        return await _db_catalog().find_sku_by_name_and_vendor(get_org_id(), name, vendor_id)

    async def update_sku(sku_id: str, updates: SkuUpdate):
        async with transaction():
            return await _db_catalog().update_sku(sku_id, get_org_id(), updates.model_dump(exclude_none=True))

    async def add_vendor_item(**kw):
        return await _db_catalog().add_vendor_item(get_org_id(), **kw)

    async def insert_vendor_row(vendor: Vendor | dict) -> None:
        v = Vendor.model_validate(vendor) if isinstance(vendor, dict) else vendor
        async with transaction():
            await _db_catalog().insert_vendor(v)

    return PurchasingDeps(
        list_departments=list_departments,
        get_department_by_code=get_department_by_code,
        find_vendor_by_name=find_vendor_by_name,
        insert_vendor=insert_vendor_row,
        get_sku_by_id=get_sku_by_id,
        find_vendor_item_by_vendor_and_sku_code=find_vendor_item_by_vendor_and_sku_code,
        find_sku_by_name_and_vendor=find_sku_by_name_and_vendor,
        update_sku=update_sku,
        create_product_with_sku=lambda **kw: lifecycle_create(**kw, on_stock_import=process_receiving_stock_changes),
        add_vendor_item=add_vendor_item,
        process_receiving_stock_changes=process_receiving_stock_changes,
    )


router = APIRouter(prefix="/purchasing/purchase-orders", tags=["purchase-orders"])


@router.post("")
async def create_po(
    data: CreatePORequest,
    request: Request,
    current_user: AdminDep,
):
    """Save reviewed receipt items as a pending purchase order (no inventory update)."""
    result = await create_purchase_order(
        vendor_name=data.vendor_name,
        products=data.products,
        deps=_build_deps(),
        current_user=current_user,
        document_date=data.document_date,
        total=data.total,
        category_id=data.category_id,
        create_vendor_if_missing=data.create_vendor_if_missing,
    )
    await audit_log(
        user_id=current_user.id,
        action="po.create",
        resource_type="purchase_order",
        resource_id=result.id,
        details={"vendor": data.vendor_name, "item_count": len(data.products)},
        request=request,
        org_id=current_user.organization_id,
    )
    return result


@router.get("")
async def list_purchase_orders(
    current_user: AdminDep,
    status: str | None = None,
):
    """List purchase orders, optionally filtered by status (ordered/received)."""
    return await list_pos_with_counts(status=status)


@router.get("/{po_id}")
async def get_purchase_order(
    po_id: str,
    current_user: AdminDep,
):
    """Get a purchase order with all its items."""
    po = await get_po(po_id)
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order not found: {po_id}")
    items = await get_po_items(po_id)
    return po.model_copy(update={"items": items})


@router.post("/{po_id}/delivery")
async def mark_delivery(
    po_id: str,
    data: MarkDeliveryRequest,
    current_user: AdminDep,
):
    """Mark selected 'ordered' items as 'pending' (delivery arrived at dock)."""
    return await mark_delivery_received(
        po_id=po_id,
        item_ids=data.item_ids,
        current_user=current_user,
    )


@router.post("/{po_id}/receive")
async def receive_items(
    po_id: str,
    data: ReceiveItemsRequest,
    request: Request,
    current_user: AdminDep,
):
    """Mark selected items as arrived and update inventory stock."""
    result = await receive_po_items(
        po_id=po_id,
        item_updates=data.items,
        deps=_build_deps(),
        current_user=current_user,
    )
    await audit_log(
        user_id=current_user.id,
        action="po.receive",
        resource_type="purchase_order",
        resource_id=po_id,
        details={
            "received": result.received,
            "matched": result.matched,
            "cost_total": result.cost_total,
        },
        request=request,
        org_id=current_user.organization_id,
    )
    if result.cost_total > 0:
        try:
            await queue_po_for_sync(po_id)
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning("Failed to queue PO %s for Xero sync: %s", po_id, e)
    return result
