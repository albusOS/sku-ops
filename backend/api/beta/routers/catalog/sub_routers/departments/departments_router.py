"""Department CRUD routes."""

from fastapi import APIRouter, HTTPException, Request

from catalog.domain.department import Department, DepartmentCreate
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log

router = APIRouter(prefix="/departments", tags=["departments"])


def _db_catalog():
    return get_database_manager().catalog


@router.get("", response_model=list[Department])
async def get_departments(_current_user: CurrentUserDep):
    return await _db_catalog().list_departments(get_org_id())


@router.post("", response_model=Department)
async def create_department(data: DepartmentCreate, current_user: AdminDep):
    existing = await _db_catalog().get_department_by_code(
        data.code, get_org_id()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Department code already exists"
        )

    dept = Department(
        name=data.name,
        code=data.code.upper(),
        description=data.description or "",
        organization_id=current_user.organization_id,
    )
    async with transaction():
        await _db_catalog().insert_department(dept)
    return dept


@router.put("/{dept_id}", response_model=Department)
async def update_department(
    dept_id: str, data: DepartmentCreate, _current_user: AdminDep
):
    existing = await _db_catalog().get_department_by_id(dept_id, get_org_id())
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found")
    return await _db_catalog().update_department(
        dept_id,
        get_org_id(),
        data.name,
        data.description or "",
    )


@router.delete("/{dept_id}")
async def delete_department(
    dept_id: str, request: Request, current_user: AdminDep
):
    oid = get_org_id()
    existing = await _db_catalog().get_department_by_id(dept_id, oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found")
    sku_count = await _db_catalog().count_skus_by_department(dept_id, oid)
    if sku_count > 0:
        raise HTTPException(
            status_code=400, detail="Cannot delete department with products"
        )

    deleted = await _db_catalog().soft_delete_department(dept_id, oid)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    await audit_log(
        user_id=current_user.id,
        action="department.delete",
        resource_type="department",
        resource_id=dept_id,
        details={"name": existing.name, "code": existing.code},
        request=request,
        org_id=current_user.organization_id,
    )
    return {"message": "Department deleted"}
