from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    agent_type: Literal["auto", "inventory", "ops", "finance"] = "auto"
