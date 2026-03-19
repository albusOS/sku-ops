"""Base entity types — the mechanical pattern every domain entity shares."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditedEntity(Entity):
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
