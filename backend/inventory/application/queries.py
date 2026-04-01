"""Inventory application queries — safe for cross-context import.

Exposes stock transaction analytics without leaking infrastructure details.
"""

from datetime import datetime

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def withdrawal_velocity(
    sku_ids: list[str],
    since: datetime,
) -> dict[str, float]:
    """Total units withdrawn per SKU since a date. Keyed by sku_id."""
    db = get_database_manager()
    return await db.inventory.withdrawal_velocity(get_org_id(), sku_ids, since)


async def daily_withdrawal_activity(
    since: datetime,
    sku_id: str | None = None,
) -> list[dict]:
    """Daily withdrawal activity: transaction_count + units_moved per day."""
    db = get_database_manager()
    return await db.inventory.daily_withdrawal_activity(
        get_org_id(), since, sku_id=sku_id
    )


async def demand_normalized_velocity(
    sku_ids: list[str],
    days: int = 30,
) -> dict[str, dict]:
    """Per-SKU withdrawal velocity with IQR outlier stripping."""
    db = get_database_manager()
    return await db.inventory.demand_normalized_velocity(
        get_org_id(), sku_ids, days=days
    )


async def seasonal_pattern(
    sku_id: str,
    months: int = 12,
) -> list[dict]:
    """Monthly withdrawal totals for a SKU over the last N months."""
    db = get_database_manager()
    return await db.inventory.seasonal_pattern(
        get_org_id(), sku_id, months=months
    )


async def sku_demand_profile(
    sku_id: str,
    days: int = 60,
) -> dict:
    """Deep demand profile for a single SKU."""
    db = get_database_manager()
    return await db.inventory.sku_demand_profile(
        get_org_id(), sku_id, days=days
    )
