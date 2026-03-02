"""Chat assistant route."""
import uuid

from fastapi import APIRouter, Depends

from auth import get_current_user
from config import ANTHROPIC_AVAILABLE, LLM_SETUP_URL, SESSION_COST_CAP

from .schemas import ChatRequest

router = APIRouter(tags=["chat"])


@router.get("/chat/status")
async def chat_status(current_user: dict = Depends(get_current_user)):
    """Return whether AI assistant is configured. Frontend can show setup prompt when false."""
    return {
        "available": ANTHROPIC_AVAILABLE,
        "provider": "anthropic" if ANTHROPIC_AVAILABLE else None,
        "setup_url": LLM_SETUP_URL if not ANTHROPIC_AVAILABLE else None,
    }


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def clear_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Clear a chat session's history server-side (e.g. user clicks 'New Chat')."""
    from services import session_store
    session_store.clear(session_id)


@router.post("/chat")
async def chat_assistant(
    data: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Chat with AI assistant. Routes to specialist agents: inventory, ops, finance, insights."""
    from services.assistant import chat
    from services import session_store

    session_id = data.session_id or str(uuid.uuid4())
    history = session_store.get_or_create(session_id)

    if SESSION_COST_CAP > 0 and session_store.get_cost(session_id) >= SESSION_COST_CAP:
        return {
            "response": (
                f"This session has reached the ${SESSION_COST_CAP:.2f} AI spend limit. "
                "Start a new chat to continue."
            ),
            "tool_calls": [],
            "thinking": [],
            "agent": None,
            "session_id": session_id,
            "usage": {"cost_usd": 0, "capped": True},
        }

    ctx = {
        "org_id": current_user.get("organization_id", "default"),
        "user_id": current_user.get("id", ""),
        "user_name": current_user.get("name", ""),
    }
    result = await chat(
        (data.message or "").strip(),
        history=history,
        ctx=ctx,
        mode=data.mode,
        agent_type=data.agent_type,
    )

    turn_cost = result.get("usage", {}).get("cost_usd", 0.0)
    session_store.update(session_id, result.pop("history", []), cost_usd=turn_cost)
    result["session_id"] = session_id
    result["usage"] = {**result.get("usage", {}), "session_cost_usd": session_store.get_cost(session_id)}
    return result
