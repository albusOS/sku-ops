"""Reports context router - dashboard and reports."""

from fastapi import APIRouter

from api.beta.routers.reports.sub_routers import (
    dashboard_router,
    reports_router,
)

router = APIRouter(prefix="/reports", tags=["reports"])

router.include_router(dashboard_router)
router.include_router(reports_router)
