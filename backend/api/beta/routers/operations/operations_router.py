"""Operations context router - contractors, material requests, returns, withdrawals."""

from fastapi import APIRouter

from api.beta.routers.operations.sub_routers import (
    contractors_router,
    material_requests_router,
    returns_router,
    withdrawals_router,
)

router = APIRouter(prefix="/operations", tags=["operations"])

router.include_router(contractors_router)
router.include_router(material_requests_router)
router.include_router(returns_router)
router.include_router(withdrawals_router)
