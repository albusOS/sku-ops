"""Fiscal period application service."""

import logging
from datetime import UTC, datetime

from finance.domain.enums import FiscalPeriodStatus
from finance.domain.fiscal_period import FiscalPeriod, FiscalPeriodCreate
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _db_finance():
    return get_database_manager().finance


async def create_fiscal_period(body: FiscalPeriodCreate) -> FiscalPeriod:
    period_id = new_uuid7_str()
    now = datetime.now(UTC)
    org_id = get_org_id()
    async with transaction():
        await _db_finance().fiscal_insert_period(
            org_id,
            period_id,
            body.name,
            body.start_date,
            body.end_date,
            now,
        )
    result = await _db_finance().fiscal_get_period(org_id, period_id)
    if not result:
        raise ResourceNotFoundError("Fiscal period not found after insert")
    logger.info(
        "fiscal_period.created",
        extra={
            "org_id": org_id,
            "period_id": period_id,
            "period_name": body.name,
        },
    )
    return result


async def close_fiscal_period(
    period_id: str,
    closed_by_id: str,
) -> FiscalPeriod:
    period = await _db_finance().fiscal_get_period(get_org_id(), period_id)
    if not period:
        raise ResourceNotFoundError("Fiscal period not found")
    if period.status != FiscalPeriodStatus.OPEN:
        raise ValueError("Period is already closed")

    now = datetime.now(UTC)
    org_id = get_org_id()
    async with transaction():
        await _db_finance().fiscal_close_period(
            org_id, period_id, closed_by_id, now
        )
    result = await _db_finance().fiscal_get_period(org_id, period_id)
    if not result:
        raise ResourceNotFoundError("Fiscal period not found after close")
    logger.info(
        "fiscal_period.closed",
        extra={
            "org_id": org_id,
            "period_id": period_id,
            "closed_by_id": closed_by_id,
        },
    )
    return result
