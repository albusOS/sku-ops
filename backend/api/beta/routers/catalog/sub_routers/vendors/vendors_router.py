"""Vendor CRUD routes."""

from fastapi import APIRouter, HTTPException, Request

from catalog.domain.vendor import Vendor, VendorCreate
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log

router = APIRouter(prefix="/vendors", tags=["vendors"])


def _db_catalog():
    return get_database_manager().catalog


@router.get("", response_model=list[Vendor])
async def get_vendors(current_user: AdminDep):
    return await _db_catalog().list_vendors(get_org_id())


@router.post("", response_model=Vendor)
async def create_vendor(data: VendorCreate, current_user: AdminDep):
    vendor = Vendor(
        **data.model_dump(), organization_id=current_user.organization_id
    )
    async with transaction():
        await _db_catalog().insert_vendor(vendor)
    return vendor


@router.put("/{vendor_id}", response_model=Vendor)
async def update_vendor(
    vendor_id: str, data: VendorCreate, current_user: AdminDep
):
    oid = get_org_id()
    existing = await _db_catalog().get_vendor_by_id(vendor_id, oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = await _db_catalog().update_vendor(
        vendor_id, oid, data.model_dump()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return result


@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: str, request: Request, current_user: AdminDep
):
    oid = get_org_id()
    existing = await _db_catalog().get_vendor_by_id(vendor_id, oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Vendor not found")
    deleted = await _db_catalog().soft_delete_vendor(vendor_id, oid)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await audit_log(
        user_id=current_user.id,
        action="vendor.delete",
        resource_type="vendor",
        resource_id=vendor_id,
        details={"name": existing.name},
        request=request,
        org_id=current_user.organization_id,
    )
    return {"message": "Vendor deleted"}
