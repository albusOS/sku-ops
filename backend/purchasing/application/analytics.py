"""Purchasing analytics — vendor lead time computation and smart reorder points.

Cross-context consumers import from here. Uses inventory and catalog facades
for demand velocity and SKU data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from catalog.application.queries import get_vendor_items_for_sku, list_low_stock
from inventory.application.queries import demand_normalized_velocity
from shared.infrastructure.database import get_connection, get_org_id


async def vendor_lead_time_actual(
    vendor_id: str,
    days: int = 180,
) -> dict:
    """Actual lead time from PO data vs. stated lead_time_days.

    Computes median and P90 from fully received POs. Detects trend drift
    by comparing the most recent 3 POs against all prior POs.
    """
    conn = get_connection()
    org_id = get_org_id()
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    cur = await conn.execute(
        """SELECT po.id,
                  EXTRACT(EPOCH FROM (
                      po.received_at::timestamp - po.created_at::timestamp
                  )) / 86400.0 AS lead_days
           FROM purchase_orders po
           WHERE po.vendor_id = $1
             AND po.organization_id = $2
             AND po.created_at >= $3
             AND po.received_at IS NOT NULL
           ORDER BY po.received_at""",
        (vendor_id, org_id, since),
    )
    rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        return {
            "vendor_id": vendor_id,
            "po_count": 0,
            "actual_median_days": None,
            "actual_p90_days": None,
            "stated_days": None,
            "trend": "no_data",
        }

    lead_days = [float(r["lead_days"]) for r in rows]
    lead_days_sorted = sorted(lead_days)
    n = len(lead_days_sorted)
    median_days = lead_days_sorted[n // 2]
    p90_idx = min(int(n * 0.9), n - 1)
    p90_days = lead_days_sorted[p90_idx]

    trend = "stable"
    if n >= 4:
        recent_3 = lead_days[-3:]
        prior = lead_days[:-3]
        recent_avg = sum(recent_3) / len(recent_3)
        prior_avg = sum(prior) / len(prior)
        if prior_avg > 0:
            drift_pct = (recent_avg - prior_avg) / prior_avg * 100
            if drift_pct > 20:
                trend = "degrading"
            elif drift_pct < -20:
                trend = "improving"

    # Get stated lead time from vendor_items (median across SKUs for this vendor)
    stated_cur = await conn.execute(
        """SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lead_time_days) AS stated
           FROM vendor_items
           WHERE vendor_id = $1
             AND lead_time_days IS NOT NULL
             AND (organization_id = $2 OR organization_id IS NULL)
             AND deleted_at IS NULL""",
        (vendor_id, org_id),
    )
    stated_row = await stated_cur.fetchone()
    stated_days = float(stated_row["stated"]) if stated_row and stated_row["stated"] else None

    return {
        "vendor_id": vendor_id,
        "po_count": n,
        "actual_median_days": round(median_days, 1),
        "actual_p90_days": round(p90_days, 1),
        "stated_days": round(stated_days, 1) if stated_days else None,
        "trend": trend,
    }


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
    low_stock = await list_low_stock(limit=100)
    if not low_stock:
        return []

    sku_ids = [s.id for s in low_stock]
    vel_map = await demand_normalized_velocity(sku_ids, velocity_days)

    results = []
    for sku in low_stock[:limit]:
        vel = vel_map.get(sku.id)
        norm_daily = vel["normalized_daily"] if vel else 0

        # Get preferred vendor's actual lead time
        vendor_items = await get_vendor_items_for_sku(sku.id)
        preferred = next((vi for vi in vendor_items if vi.is_preferred), None)
        if not preferred and vendor_items:
            preferred = vendor_items[0]

        actual_lead = None
        if preferred:
            lt_data = await vendor_lead_time_actual(preferred.vendor_id, days=180)
            actual_lead = lt_data.get("actual_median_days")

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
