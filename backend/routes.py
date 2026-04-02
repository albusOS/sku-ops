"""Route aggregation — beta API under /api/beta."""

from fastapi import APIRouter

from api.beta import api_router as beta_api_router

api_router = APIRouter(prefix="/api")

api_router.include_router(beta_api_router)


@api_router.get("/")
async def root():
    return {"message": "Supply Yard API - Material Management System"}
