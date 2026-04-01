"""VendorItem CRUD routes - manage vendor-to-SKU relationships."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from catalog.application.queries import get_sku_by_id
from catalog.application.vendor_item_lifecycle import (
    add_vendor_item,
    remove_vendor_item,
    set_preferred_vendor,
    update_vendor_item,
)
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.errors import ResourceNotFoundError

router = APIRouter(prefix="/skus", tags=["catalog-vendor-items"])


class VendorItemCreateRequest(BaseModel):
    vendor_id: str
    vendor_sku: str | None = None
    purchase_uom: str = "each"
    purchase_pack_qty: int = 1
    cost: float = 0.0
    lead_time_days: int | None = None
    moq: float | None = None
    is_preferred: bool = False
    notes: str | None = None


class VendorItemUpdateRequest(BaseModel):
    vendor_sku: str | None = None
    purchase_uom: str | None = None
    purchase_pack_qty: int | None = None
    cost: float | None = None
    lead_time_days: int | None = None
    moq: float | None = None
    is_preferred: bool | None = None
    notes: str | None = None


@router.get("/{sku_id}/vendors")
async def list_sku_vendors(sku_id: str, current_user: CurrentUserDep):
    sku = await get_sku_by_id(sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    items = await get_database_manager().catalog.list_vendor_items_by_sku(
        sku_id, get_org_id()
    )
    return [vi.model_dump() for vi in items]


@router.post("/{sku_id}/vendors")
async def add_sku_vendor(
    sku_id: str, data: VendorItemCreateRequest, current_user: AdminDep
):
    sku = await get_sku_by_id(sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    item = await add_vendor_item(
        sku_id=sku_id,
        vendor_id=data.vendor_id,
        vendor_sku=data.vendor_sku,
        purchase_uom=data.purchase_uom,
        purchase_pack_qty=data.purchase_pack_qty,
        cost=data.cost,
        lead_time_days=data.lead_time_days,
        moq=data.moq,
        is_preferred=data.is_preferred,
        notes=data.notes,
    )
    return item.model_dump()


@router.put("/{sku_id}/vendors/{item_id}")
async def update_sku_vendor(
    sku_id: str,
    item_id: str,
    data: VendorItemUpdateRequest,
    current_user: AdminDep,
):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        result = await update_vendor_item(item_id, update_data)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result.model_dump()


@router.delete("/{sku_id}/vendors/{item_id}")
async def remove_sku_vendor(sku_id: str, item_id: str, current_user: AdminDep):
    try:
        await remove_vendor_item(item_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"message": "Vendor item removed"}


@router.post("/{sku_id}/vendors/{item_id}/set-preferred")
async def set_sku_preferred_vendor(
    sku_id: str, item_id: str, current_user: AdminDep
):
    try:
        await set_preferred_vendor(sku_id, item_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"message": "Preferred vendor set"}
