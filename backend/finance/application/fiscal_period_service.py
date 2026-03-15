"""Fiscal period application service."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from finance.domain.enums import FiscalPeriodStatus
from finance.domain.fiscal_period import FiscalPeriod, FiscalPeriodCreate
from finance.infrastructure.fiscal_period_repo import (
    close_period,
    find_closed_period_covering,
    get_period,
    insert_period,
    list_periods,
)
from shared.infrastructure.db import get_org_id, transaction
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


async def check_period_open(entry_date: str) -> None:
    """Raise ValueError if the entry date falls in a closed fiscal period."""
    period = await find_closed_period_covering(entry_date)
    if period:
        period_id, period_name = period
        raise ValueError(
            f"Cannot create entries in closed fiscal period '{period_name or period_id}'"
        )


async def list_fiscal_periods(status: str | None = None) -> list[FiscalPeriod]:
    return await list_periods(status=status)


async def create_fiscal_period(body: FiscalPeriodCreate) -> FiscalPeriod:
    period_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    org_id = get_org_id()
    async with transaction():
        await insert_period(
            period_id=period_id,
            name=body.name,
            start_date=body.start_date,
            end_date=body.end_date,
            created_at=now,
        )
    result = await get_period(period_id)
    if not result:
        raise ResourceNotFoundError("Fiscal period not found after insert")
    logger.info(
        "fiscal_period.created",
        extra={"org_id": org_id, "period_id": period_id, "period_name": body.name},
    )
    return result


async def close_fiscal_period(
    period_id: str,
    closed_by_id: str,
) -> FiscalPeriod:
    period = await get_period(period_id)
    if not period:
        raise ResourceNotFoundError("Fiscal period not found")
    if period.status != FiscalPeriodStatus.OPEN:
        raise ValueError("Period is already closed")

    now = datetime.now(UTC).isoformat()
    async with transaction():
        await close_period(period_id, closed_by_id=closed_by_id, closed_at=now)
    result = await get_period(period_id)
    if not result:
        raise ResourceNotFoundError("Fiscal period not found after close")
    logger.info(
        "fiscal_period.closed",
        extra={"org_id": get_org_id(), "period_id": period_id, "closed_by_id": closed_by_id},
    )
    return result
