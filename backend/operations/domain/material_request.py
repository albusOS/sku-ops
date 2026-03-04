"""Material request models - contractor pick list before staff processes into withdrawal."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .withdrawal import WithdrawalItem


class MaterialRequestCreate(BaseModel):
    items: List[WithdrawalItem]
    job_id: Optional[str] = None
    service_address: Optional[str] = None
    notes: Optional[str] = None


class MaterialRequestProcess(BaseModel):
    job_id: str
    service_address: str
    notes: Optional[str] = None


class MaterialRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid4()))
    contractor_id: str
    contractor_name: str = ""
    items: List[WithdrawalItem]
    status: str = "pending"
    withdrawal_id: Optional[str] = None
    job_id: Optional[str] = None
    service_address: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    processed_at: Optional[str] = None
    processed_by_id: Optional[str] = None
    organization_id: str = "default"
