"""Fiscal period domain model."""

from pydantic import BaseModel

from finance.domain.enums import FiscalPeriodStatus


class FiscalPeriodCreate(BaseModel):
    name: str = ""
    start_date: str
    end_date: str


class FiscalPeriod(BaseModel):
    """Read model for a fiscal period row."""

    id: str
    name: str
    start_date: str
    end_date: str
    status: FiscalPeriodStatus
    organization_id: str
    created_at: str
    closed_by_id: str | None = None
    closed_at: str | None = None
