"""Material request routes - contractor pick list, staff processes into withdrawal."""

from fastapi import APIRouter, HTTPException

from operations.application.material_request_service import (
    MaterialRequestError,
    create_material_request,
    list_material_requests,
)
from operations.application.material_request_service import (
    process_material_request as _process_request,
)
from operations.domain.material_request import (
    MaterialRequestCreate,
    MaterialRequestProcess,
)
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db.base import get_database_manager


def _db_operations():
    return get_database_manager().operations


router = APIRouter(prefix="/material-requests", tags=["material-requests"])


@router.post("")
async def create_material_request_route(
    data: MaterialRequestCreate, current_user: CurrentUserDep
):
    """Contractor creates a material request (pick list). Staff will process it into a withdrawal."""
    try:
        result = await create_material_request(data, current_user)
    except MaterialRequestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return result


@router.get("")
async def list_material_requests_route(current_user: CurrentUserDep):
    """Contractors see own requests; admins see all pending."""
    try:
        return await list_material_requests(current_user)
    except MaterialRequestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{request_id}")
async def get_material_request(request_id: str, current_user: CurrentUserDep):
    req = await _db_operations().get_material_request_by_id(
        current_user.organization_id, request_id
    )
    if not req:
        raise HTTPException(
            status_code=404, detail="Material request not found"
        )
    if (
        current_user.role == "contractor"
        and req.contractor_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    return req


@router.post("/{request_id}/process")
async def process_material_request_route(
    request_id: str,
    data: MaterialRequestProcess,
    current_user: AdminDep,
):
    """Convert a pending material request into a withdrawal. Staff supplies job_id and service_address."""
    try:
        withdrawal = await _process_request(
            request_id=request_id,
            job_id_override=data.job_id,
            service_address_override=data.service_address,
            notes=data.notes,
            current_user_id=current_user.id,
            current_user_name=current_user.name,
        )
    except MaterialRequestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return withdrawal
