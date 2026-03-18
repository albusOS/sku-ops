"""Catalog context router - departments, product_families, products, vendor_items, sku, vendors, units."""

from fastapi import APIRouter

from api.beta.routers.catalog.sub_routers import (
    departments_router,
    product_families_router,
    products_router,
    sku_router,
    units_router,
    vendor_items_router,
    vendors_router,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

SUB_ROUTERS = (
    departments_router,
    product_families_router,
    products_router,
    vendor_items_router,
    sku_router,
    units_router,
    vendors_router,
)

for sub_router in SUB_ROUTERS:
    router.include_router(sub_router)
