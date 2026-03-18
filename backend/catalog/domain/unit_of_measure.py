"""Unit of measure domain models."""

from pydantic import BaseModel, field_validator

from shared.kernel.entity import Entity


class UnitOfMeasureCreate(BaseModel):
    code: str
    name: str
    family: str = "discrete"

    @field_validator("code")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        v = (v or "").lower().strip()
        if not v:
            raise ValueError("Unit code must not be empty")
        return v

    @field_validator("family")
    @classmethod
    def valid_family(cls, v: str) -> str:
        allowed = {"length", "volume", "weight", "area", "discrete"}
        v = (v or "discrete").lower().strip()
        if v not in allowed:
            raise ValueError(f"Family must be one of: {sorted(allowed)}")
        return v


class UnitOfMeasure(Entity):
    """Global units have organization_id=None; org-specific units have it set."""

    organization_id: str | None = None  # type: ignore[assignment]
    code: str
    name: str
    family: str = "discrete"
