"""Inventory context router - cycle counts and stock."""

from fastapi import APIRouter

from api.beta.routers.inventory.sub_routers import (
    cycle_counts_router,
    stock_router,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

router.include_router(cycle_counts_router)
router.include_router(stock_router)
