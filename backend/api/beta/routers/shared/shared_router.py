"""Shared context router - auth, health, websocket, audit, addresses."""

from fastapi import APIRouter

from api.beta.routers.shared.sub_routers import (
    addresses_router,
    audit_router,
    auth_dev_router,
    auth_router,
    health_router,
    websocket_router,
)
from shared.infrastructure.config import ALLOW_PUBLIC_AUTH

router = APIRouter(prefix="/shared", tags=["shared"])

SUB_ROUTERS = (
    auth_router,
    audit_router,
    health_router,
    addresses_router,
    websocket_router,
)

for sub_router in SUB_ROUTERS:
    router.include_router(sub_router)

if ALLOW_PUBLIC_AUTH:
    router.include_router(auth_dev_router)
