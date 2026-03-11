"""Fiscal period domain model."""

from pydantic import BaseModel


class FiscalPeriodCreate(BaseModel):
    name: str = ""
    start_date: str
    end_date: str
