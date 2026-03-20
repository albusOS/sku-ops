from api.beta.routers.shared.sub_routers.addresses import (
    router as addresses_router,
)
from api.beta.routers.shared.sub_routers.audit import router as audit_router
from api.beta.routers.shared.sub_routers.auth import router as auth_router
from api.beta.routers.shared.sub_routers.health import router as health_router
from api.beta.routers.shared.sub_routers.websocket import (
    router as websocket_router,
)

__all__ = [
    "addresses_router",
    "audit_router",
    "auth_router",
    "health_router",
    "websocket_router",
]
