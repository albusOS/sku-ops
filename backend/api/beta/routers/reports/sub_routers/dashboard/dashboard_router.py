"""Dashboard stats routes - thin controllers delegating to application layer."""

import logging

from fastapi import APIRouter, HTTPException, Query

from reports.application.dashboard_queries import (
    admin_dashboard,
    contractor_dashboard,
    dashboard_transactions,
)
from shared.api.deps import AdminDep, CurrentUserDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: CurrentUserDep,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
):
    try:
        if current_user.role == "contractor":
            return await contractor_dashboard(
                current_user.id, start_date=start_date, end_date=end_date
            )
        return await admin_dashboard(start_date=start_date, end_date=end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in get_dashboard_stats")
        raise


@router.get("/transactions")
async def get_dashboard_transactions(
    current_user: AdminDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    contractor_id: str | None = Query(None),
    payment_status: str | None = Query(None),
):
    """Paginated transactions for the dashboard. Supports date range + filters."""
    try:
        return await dashboard_transactions(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            contractor_id=contractor_id,
            payment_status=payment_status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in get_dashboard_transactions")
        raise
