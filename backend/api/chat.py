"""Chat assistant route."""
from fastapi import APIRouter, Depends

from auth import get_current_user
from config import GEMINI_AVAILABLE, LLM_SETUP_URL

from .schemas import ChatRequest

router = APIRouter(tags=["chat"])


@router.get("/chat/status")
async def chat_status(current_user: dict = Depends(get_current_user)):
    """Return whether AI assistant is configured. Frontend can show setup prompt when false."""
    return {
        "available": GEMINI_AVAILABLE,
        "provider": "gemini" if GEMINI_AVAILABLE else None,
        "setup_url": LLM_SETUP_URL if not GEMINI_AVAILABLE else None,
    }


@router.post("/chat")
async def chat_assistant(
    data: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Chat with AI assistant that can search products, inventory stats, low stock, departments, vendors."""
    from services.assistant import chat

    messages = data.messages or []
    result = await chat(messages, (data.message or "").strip(), history=data.history)
    return result
