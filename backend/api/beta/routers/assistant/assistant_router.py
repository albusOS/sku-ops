"""Assistant feature router - chat, monitoring, and WebSocket chat."""

from fastapi import APIRouter

from api.beta.routers.assistant.sub_routers import (
    chat_router,
    memory_router,
    monitoring_router,
    ws_chat_router,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])

router.include_router(chat_router)
router.include_router(memory_router)
router.include_router(monitoring_router)
router.include_router(ws_chat_router)
