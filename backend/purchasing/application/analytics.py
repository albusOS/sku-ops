"""Purchasing analytics — vendor lead time computation and smart reorder points.

Cross-context consumers import from here. Uses inventory and catalog facades
for demand velocity and SKU data.
"""

from __future__ import annotations

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def vendor_lead_time_actual(
    vendor_id: str,
    days: int = 180,
) -> dict:
    """Actual lead time from PO data vs. stated lead_time_days.

    Computes median and P90 from fully received POs. Detects trend drift
    by comparing the most recent 3 POs against all prior POs.
    """
    return await get_database_manager().purchasing.vendor_lead_time_actual(
        get_org_id(), vendor_id, days=days
    )


async def reorder_point_smart(
    limit: int = 30,
    velocity_days: int = 30,
    safety_factor: float = 1.5,
) -> list[dict]:
    """Velocity-based reorder points vs. static min_stock.

    For each low-stock SKU: recommended_min = normalized_daily_velocity *
    actual_vendor_lead_time * safety_factor. Flags where the current min_stock
    is miscalibrated.
    """
    low_stock = await get_database_manager().catalog.list_low_stock_skus(
        get_org_id(), limit=100
    )
    if not low_stock:
        return []

    sku_ids = [s.id for s in low_stock]
    org_id = get_org_id()
    vel_map = await get_database_manager().inventory.demand_normalized_velocity(
        org_id, sku_ids, days=velocity_days
    )
    vendor_items_by_sku = (
        await get_database_manager().catalog.list_vendor_items_by_skus_grouped(
            org_id, sku_ids
        )
    )
    lead_time_cache: dict[str, float | None] = {}

    results = []
    for sku in low_stock[:limit]:
        vel = vel_map.get(sku.id)
        norm_daily = vel["normalized_daily"] if vel else 0

        # Get preferred vendor's actual lead time
        vendor_items = vendor_items_by_sku.get(sku.id, [])
        preferred = next((vi for vi in vendor_items if vi.is_preferred), None)
        if not preferred and vendor_items:
            preferred = vendor_items[0]

        actual_lead = None
        if preferred:
            if preferred.vendor_id not in lead_time_cache:
                lt_data = await vendor_lead_time_actual(
                    preferred.vendor_id, days=180
                )
                lead_time_cache[preferred.vendor_id] = lt_data.get(
                    "actual_median_days"
                )
            actual_lead = lead_time_cache[preferred.vendor_id]

        lead_days = actual_lead or 7.0
        recommended = round(norm_daily * lead_days * safety_factor, 0)

        gap = recommended - sku.min_stock
        if recommended > 0 and gap > 0:
            risk = "under_stocked"
        elif recommended > 0 and gap < -recommended * 0.5:
            risk = "over_stocked"
        else:
            risk = "ok"

        results.append(
            {
                "sku_id": sku.id,
                "sku": sku.sku,
                "name": sku.name,
                "quantity": sku.quantity,
                "current_min_stock": sku.min_stock,
                "recommended_min_stock": int(recommended),
                "gap": int(gap),
                "risk": risk,
                "normalized_daily_velocity": norm_daily,
                "vendor_lead_days": round(lead_days, 1),
                "vendor_name": preferred.vendor_name if preferred else None,
                "sell_uom": sku.sell_uom,
            }
        )

    results.sort(key=lambda r: r["gap"], reverse=True)
    return results
