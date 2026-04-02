"""VendorItem CRUD routes - manage vendor-to-SKU relationships."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _db_catalog():
    return get_database_manager().catalog


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
    sku = await _db_catalog().get_sku_by_id(sku_id, get_org_id())
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    items = await _db_catalog().list_vendor_items_by_sku(sku_id, get_org_id())
    return [vi.model_dump() for vi in items]


@router.post("/{sku_id}/vendors")
async def add_sku_vendor(
    sku_id: str, data: VendorItemCreateRequest, current_user: AdminDep
):
    sku = await _db_catalog().get_sku_by_id(sku_id, get_org_id())
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    item = await _db_catalog().add_vendor_item(
        get_org_id(),
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
        result = await _db_catalog().modify_vendor_item(
            get_org_id(), item_id, update_data
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result.model_dump()


@router.delete("/{sku_id}/vendors/{item_id}")
async def remove_sku_vendor(sku_id: str, item_id: str, current_user: AdminDep):
    org_id = get_org_id()
    cat = _db_catalog()
    existing = await cat.get_vendor_item_by_id(item_id, org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Vendor item not found")
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
    return {"message": "Vendor item removed"}


@router.post("/{sku_id}/vendors/{item_id}/set-preferred")
async def set_sku_preferred_vendor(
    sku_id: str, item_id: str, current_user: AdminDep
):
    try:
        await _db_catalog().set_preferred_vendor_item(
            get_org_id(), sku_id, item_id
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"message": "Preferred vendor set"}
