"""Return routes - process material returns against previous withdrawals.

Both admins and contractors can create returns. Admins see all returns;
contractors see only their own. Ownership is enforced by filtering on
contractor_id (for list) and checking the return's contractor_id (for detail).
"""

from fastapi import APIRouter, HTTPException, Request

from operations.application.return_service import create_return
from operations.domain.returns import ReturnCreate
from shared.api.deps import CurrentUserDep
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log


def _db_operations():
    return get_database_manager().operations


router = APIRouter(prefix="/returns", tags=["returns"])


@router.post("")
async def create_material_return(
    data: ReturnCreate,
    request: Request,
    current_user: CurrentUserDep,
):
    """Process a return against a previous withdrawal. Restocks inventory and creates credit note.

    Contractors may only return their own withdrawals.
    """
    if current_user.role == "contractor":
        withdrawal = await _db_operations().get_withdrawal_by_id(
            current_user.organization_id, data.withdrawal_id
        )
        if not withdrawal or withdrawal.contractor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your withdrawal")

    try:
        result = await create_return(data, current_user)
        await audit_log(
            user_id=current_user.id,
            action="return.create",
            resource_type="return",
            resource_id=result.id,
            details={
                "withdrawal_id": data.withdrawal_id,
                "total": result.total,
                "item_count": len(data.items),
            },
            request=request,
            org_id=current_user.organization_id,
        )
    except (ValueError, RuntimeError, OSError) as e:
        status = getattr(e, "status_hint", 400)
        raise HTTPException(status_code=status, detail=str(e)) from e
    else:
        return result


@router.get("")
async def list_returns(
    current_user: CurrentUserDep,
    contractor_id: str | None = None,
    withdrawal_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Admins see all (optionally filtered). Contractors always see only their own."""
    if current_user.role == "contractor":
        contractor_id = current_user.id

    return await _db_operations().list_returns(
        current_user.organization_id,
        contractor_id=contractor_id,
        withdrawal_id=withdrawal_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{return_id}")
async def get_return(
    return_id: str,
    current_user: CurrentUserDep,
):
    ret = await _db_operations().get_return_by_id(current_user.organization_id, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    if current_user.role == "contractor" and ret.contractor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your return")
    return ret
