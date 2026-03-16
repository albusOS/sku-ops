"""Beta API composition - all context routers under /api/beta."""

from fastapi import APIRouter

from api.beta.routers import (
    assistant,
    catalog,
    documents,
    finance,
    inventory,
    jobs,
    operations,
    purchasing,
    reports,
    shared,
)

api_router = APIRouter(prefix="/beta")

ROUTER_MODULES = (
    shared,
    documents,
    finance,
    assistant,
    catalog,
    inventory,
    jobs,
    operations,
    purchasing,
    reports,
)

for router_module in ROUTER_MODULES:
    api_router.include_router(router_module.router)
