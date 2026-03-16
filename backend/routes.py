"""Route aggregation — beta API under /api/beta, seed under /api/seed."""

from fastapi import APIRouter

from api.beta import api_router as beta_api_router
from shared.infrastructure.config import ALLOW_RESET, is_development, is_test

api_router = APIRouter(prefix="/api")

api_router.include_router(beta_api_router)

if is_development or is_test or ALLOW_RESET:
    try:
        from devtools.api.seed import router as seed_router

        api_router.include_router(seed_router)
    except Exception as _e:
        import logging as _log

        _log.getLogger(__name__).warning("Seed router import failed: %s", _e)


@api_router.get("/")
async def root():
    return {"message": "Supply Yard API - Material Management System"}
