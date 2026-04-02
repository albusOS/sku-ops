"""Material withdrawal (POS) routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from operations.application.contractor_service import get_contractor_by_id
from operations.application.withdrawal_service import (
    bulk_mark_withdrawals_paid,
    create_withdrawal_wired,
    mark_single_withdrawal_paid,
)
from operations.domain.withdrawal import (
    ContractorContext,
    MaterialWithdrawal,
    MaterialWithdrawalCreate,
)
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])


class BulkMarkPaidRequest(BaseModel):
    withdrawal_ids: list[str]


@router.post("", response_model=MaterialWithdrawal)
async def create_withdrawal(
    data: MaterialWithdrawalCreate,
    request: Request,
    current_user: CurrentUserDep,
):
    """Create a material withdrawal - Contractors withdraw materials charged to their account."""
    contractor_record = await get_contractor_by_id(current_user.id)
    if not contractor_record:
        raise HTTPException(
            status_code=404, detail="Contractor profile not found"
        )
    contractor = ContractorContext(
        id=contractor_record.id,
        name=contractor_record.name,
        company=contractor_record.company,
        billing_entity=contractor_record.billing_entity,
        billing_entity_id=contractor_record.billing_entity_id,
    )
    result = await create_withdrawal_wired(data, contractor, current_user)
    await audit_log(
        user_id=current_user.id,
        action="withdrawal.create",
        resource_type="withdrawal",
        resource_id=result.id,
        details={"total": result.total, "job_id": data.job_id},
        request=request,
        org_id=current_user.organization_id,
    )
    return result


@router.post("/for-contractor")
async def create_withdrawal_for_contractor(
    contractor_id: str,
    data: MaterialWithdrawalCreate,
    request: Request,
    current_user: AdminDep,
):
    """Admin creates withdrawal on behalf of a contractor."""
    contractor = await get_contractor_by_id(contractor_id)
    if not contractor or contractor.role != "contractor":
        raise HTTPException(status_code=404, detail="Contractor not found")
    if (
        contractor.organization_id
        and contractor.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Contractor belongs to different organization",
        )
    contractor_ctx = ContractorContext(
        id=contractor.id,
        name=contractor.name,
        company=contractor.company,
        billing_entity=contractor.billing_entity,
        billing_entity_id=contractor.billing_entity_id,
    )
    result = await create_withdrawal_wired(data, contractor_ctx, current_user)
    await audit_log(
        user_id=current_user.id,
        action="withdrawal.create_for_contractor",
        resource_type="withdrawal",
        resource_id=result.id,
        details={"contractor_id": contractor_id, "total": result.total},
        request=request,
        org_id=current_user.organization_id,
    )
    return result


@router.get("")
async def get_withdrawals(
    current_user: CurrentUserDep,
    contractor_id: str | None = None,
    payment_status: str | None = None,
    billing_entity: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    cid = (
        current_user.id if current_user.role == "contractor" else contractor_id
    )
    return await get_database_manager().operations.list_withdrawals(
        current_user.organization_id,
        contractor_id=cid,
        payment_status=payment_status,
        billing_entity=billing_entity,
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )


@router.get("/{withdrawal_id}")
async def get_withdrawal(withdrawal_id: str, current_user: CurrentUserDep):
    withdrawal = await get_database_manager().operations.get_withdrawal_by_id(
        current_user.organization_id, withdrawal_id
    )
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")

    if (
        current_user.role == "contractor"
        and withdrawal.contractor_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return withdrawal


@router.put("/{withdrawal_id}/mark-paid")
async def mark_withdrawal_paid(
    withdrawal_id: str, request: Request, current_user: AdminDep
):
    try:
        result = await mark_single_withdrawal_paid(
            withdrawal_id=withdrawal_id,
            performed_by_user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await audit_log(
        user_id=current_user.id,
        action="payment.mark_paid",
        resource_type="withdrawal",
        resource_id=withdrawal_id,
        details={},
        request=request,
        org_id=current_user.organization_id,
    )
    return result


@router.put("/bulk-mark-paid")
async def bulk_mark_paid(
    body: BulkMarkPaidRequest, request: Request, current_user: AdminDep
):
    try:
        updated = await bulk_mark_withdrawals_paid(
            withdrawal_ids=body.withdrawal_ids,
            performed_by_user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await audit_log(
        user_id=current_user.id,
        action="payment.bulk_mark_paid",
        resource_type="withdrawal",
        resource_id=None,
        details={
            "withdrawal_ids": body.withdrawal_ids,
            "count": len(body.withdrawal_ids),
        },
        request=request,
        org_id=current_user.organization_id,
    )
    return {"updated": updated}
