from api.beta.routers.operations.sub_routers.contractors import router as contractors_router
from api.beta.routers.operations.sub_routers.material_requests import (
    router as material_requests_router,
)
from api.beta.routers.operations.sub_routers.returns import router as returns_router
from api.beta.routers.operations.sub_routers.withdrawals import router as withdrawals_router

__all__ = [
    "contractors_router",
    "material_requests_router",
    "returns_router",
    "withdrawals_router",
]
