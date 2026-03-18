"""Units of measure CRUD routes."""

from fastapi import APIRouter, HTTPException

from catalog.application import queries as catalog_queries
from catalog.domain.unit_of_measure import UnitOfMeasure, UnitOfMeasureCreate
from shared.api.deps import AdminDep, CurrentUserDep

router = APIRouter(prefix="/units", tags=["units"])


@router.get("", response_model=list[UnitOfMeasure])
async def list_units(current_user: CurrentUserDep):
    return await catalog_queries.list_units_of_measure()


@router.post("", response_model=UnitOfMeasure)
async def create_unit(data: UnitOfMeasureCreate, current_user: AdminDep):
    existing = await catalog_queries.get_unit_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Unit code already exists")

    uom = UnitOfMeasure(
        code=data.code,
        name=data.name,
        family=data.family,
        organization_id=current_user.organization_id,
    )
    await catalog_queries.insert_unit(uom)
    return uom


@router.delete("/{uom_id}")
async def delete_unit(uom_id: str, current_user: AdminDep):
    existing = await catalog_queries.get_unit_by_id(uom_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Unit not found")
    deleted = await catalog_queries.delete_unit(uom_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {"message": "Unit deleted"}
