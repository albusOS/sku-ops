"""Base entity types — the mechanical pattern every domain entity shares."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from shared.helpers.uuid import new_uuid7_str


class Entity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_uuid7_str)
    organization_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditedEntity(Entity):
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
