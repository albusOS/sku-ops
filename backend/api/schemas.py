"""API request/response schemas."""
from typing import List, Literal, Optional

from pydantic import BaseModel


class SuggestUomRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # omit to start a new session
    mode: Literal["fast", "deep"] = "fast"
    agent_type: Literal["general", "inventory", "ops", "finance", "insights"] = "general"


class DocumentImportRequest(BaseModel):
    vendor_name: str
    create_vendor_if_missing: bool = True
    department_id: Optional[str] = None
    products: List[dict]


class CreatePaymentRequest(BaseModel):
    withdrawal_id: str
    origin_url: str
