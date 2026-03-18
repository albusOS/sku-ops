from api.beta.routers.catalog.sub_routers.departments import router as departments_router
from api.beta.routers.catalog.sub_routers.product_families import router as product_families_router
from api.beta.routers.catalog.sub_routers.products import router as products_router
from api.beta.routers.catalog.sub_routers.sku import router as sku_router
from api.beta.routers.catalog.sub_routers.units import router as units_router
from api.beta.routers.catalog.sub_routers.vendor_items import router as vendor_items_router
from api.beta.routers.catalog.sub_routers.vendors import router as vendors_router

__all__ = [
    "departments_router",
    "product_families_router",
    "products_router",
    "sku_router",
    "units_router",
    "vendor_items_router",
    "vendors_router",
]
