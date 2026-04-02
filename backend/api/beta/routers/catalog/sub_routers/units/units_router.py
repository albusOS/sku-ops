"""Units of measure CRUD routes."""

from fastapi import APIRouter, HTTPException

from catalog.domain.unit_of_measure import UnitOfMeasure, UnitOfMeasureCreate
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager

router = APIRouter(prefix="/units", tags=["units"])


def _db_catalog():
    return get_database_manager().catalog


@router.get("", response_model=list[UnitOfMeasure])
async def list_units(current_user: CurrentUserDep):
    return await _db_catalog().list_uoms(get_org_id())


@router.post("", response_model=UnitOfMeasure)
async def create_unit(data: UnitOfMeasureCreate, current_user: AdminDep):
    oid = get_org_id()
    existing = await _db_catalog().get_uom_by_code(oid, data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Unit code already exists")

    uom = UnitOfMeasure(
        code=data.code,
        name=data.name,
        family=data.family,
        organization_id=current_user.organization_id,
    )
    async with transaction():
        await _db_catalog().insert_uom(uom)
    return uom


@router.delete("/{uom_id}")
async def delete_unit(uom_id: str, current_user: AdminDep):
    oid = get_org_id()
    existing = await _db_catalog().get_uom_by_id(uom_id, oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Unit not found")
    deleted = await _db_catalog().soft_delete_uom(uom_id, oid)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {"message": "Unit deleted"}
