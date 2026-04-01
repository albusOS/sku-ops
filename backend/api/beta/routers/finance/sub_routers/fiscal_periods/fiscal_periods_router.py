"""Fiscal period management routes."""

from fastapi import APIRouter, HTTPException, Request

from finance.application.fiscal_period_service import (
    close_fiscal_period,
    create_fiscal_period,
)
from finance.domain.fiscal_period import FiscalPeriodCreate
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log

router = APIRouter(prefix="/fiscal-periods", tags=["fiscal-periods"])


@router.get("")
async def list_periods(
    current_user: AdminDep,
    status: str | None = None,
):
    return await get_database_manager().finance.fiscal_list_periods(
        get_org_id(), status=status
    )


@router.post("")
async def create_period(
    body: FiscalPeriodCreate,
    current_user: AdminDep,
):
    return await create_fiscal_period(body)


@router.post("/{period_id}/close")
async def close_period(
    period_id: str,
    request: Request,
    current_user: AdminDep,
):
    """Close a fiscal period - prevents new ledger entries in this date range."""
    try:
        result = await close_fiscal_period(period_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await audit_log(
        user_id=current_user.id,
        action="fiscal_period.close",
        resource_type="fiscal_period",
        resource_id=period_id,
        details={
            "name": result.name,
            "start_date": result.start_date,
            "end_date": result.end_date,
        },
        request=request,
        org_id=current_user.organization_id,
    )
    return result
