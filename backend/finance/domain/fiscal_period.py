"""Fiscal period domain model."""

from datetime import datetime

from pydantic import BaseModel

from finance.domain.enums import FiscalPeriodStatus


class FiscalPeriodCreate(BaseModel):
    name: str = ""
    start_date: datetime
    end_date: datetime


class FiscalPeriod(BaseModel):
    """Read model for a fiscal period row."""

    id: str
    name: str
    start_date: datetime
    end_date: datetime
    status: FiscalPeriodStatus
    organization_id: str
    created_at: datetime
    closed_by_id: str | None = None
    closed_at: datetime | None = None
