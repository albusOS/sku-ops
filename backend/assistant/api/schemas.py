from typing import Literal, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: Literal["fast", "deep"] = "fast"
    agent_type: Literal["auto", "general", "inventory", "ops", "finance", "insights"] = "auto"
