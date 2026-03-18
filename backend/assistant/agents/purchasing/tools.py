"""Purchasing agent tool implementations — vendor analytics and procurement planning."""

import json
import logging

from assistant.agents.tools.registry import register as _reg
from catalog.application.queries import (
    find_sku_by_sku_code,
    find_vendor_by_name,
    get_vendor_by_id,
    list_vendors,
    sku_vendor_options,
)
from purchasing.application.analytics import (
    reorder_point_smart,
    vendor_lead_time_actual,
)
from purchasing.application.queries import (
    po_summary_by_status,
    purchase_history,
    reorder_with_vendor_context,
    vendor_catalog,
    vendor_performance,
)

logger = logging.getLogger(__name__)


async def _get_vendor_catalog(vendor_id: str = "", name: str = "") -> str:
    """SKUs supplied by a vendor with cost, lead time, MOQ."""
    vendor_id = vendor_id.strip()
    if not vendor_id:
        name = name.strip()
        if name:
            vendor = await find_vendor_by_name(name)
            if vendor:
                vendor_id = vendor.id
            else:
                return json.dumps({"error": f"Vendor '{name}' not found"})
        else:
            return json.dumps({"error": "vendor_id or name required"})

    vendor = await get_vendor_by_id(vendor_id)
    items = await vendor_catalog(vendor_id)
    return json.dumps(
        {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name if vendor else "",
            "sku_count": len(items),
            "items": items,
        }
    )


async def _get_vendor_performance(vendor_id: str = "", name: str = "", days: int = 90) -> str:
    """Vendor reliability: PO count, spend, avg lead time, fill rate."""
    vendor_id = vendor_id.strip()
    days = min(days, 365)
    if not vendor_id:
        name = name.strip()
        if name:
            vendor = await find_vendor_by_name(name)
            if vendor:
                vendor_id = vendor.id
            else:
                return json.dumps({"error": f"Vendor '{name}' not found"})
        else:
            return json.dumps({"error": "vendor_id or name required"})

    vendor = await get_vendor_by_id(vendor_id)
    perf = await vendor_performance(vendor_id, days, vendor_name=vendor.name if vendor else "")
    return json.dumps(
        {
            "vendor_id": perf.vendor_id,
            "vendor_name": perf.vendor_name,
            "days": perf.days,
            "po_count": perf.po_count,
            "total_spend": perf.total_spend,
            "received_count": perf.received_count,
            "avg_lead_time_days": perf.avg_lead_time_days,
            "fill_rate": perf.fill_rate,
        }
    )


async def _get_sku_vendor_options(sku_id: str = "") -> str:
    """All vendors for a SKU with comparative pricing and lead times."""
    sku_id = sku_id.strip()
    if not sku_id:
        return json.dumps({"error": "sku_id required"})
    if "-" not in sku_id:
        sku = await find_sku_by_sku_code(sku_id.upper())
        if not sku:
            return json.dumps({"error": f"SKU '{sku_id}' not found"})
        sku_id = sku.id
    options = await sku_vendor_options(sku_id)
    return json.dumps(
        {
            "sku_id": sku_id,
            "vendor_count": len(options),
            "vendors": options,
        }
    )


async def _get_purchase_history(
    vendor_id: str = "", name: str = "", days: int = 90, limit: int = 20
) -> str:
    """Recent POs for a vendor with item summaries."""
    vendor_id = vendor_id.strip()
    days = min(days, 365)
    limit = min(limit, 50)
    if not vendor_id:
        name = name.strip()
        if name:
            vendor = await find_vendor_by_name(name)
            if vendor:
                vendor_id = vendor.id
            else:
                return json.dumps({"error": f"Vendor '{name}' not found"})
        else:
            return json.dumps({"error": "vendor_id or name required"})

    vendor = await get_vendor_by_id(vendor_id)
    history = await purchase_history(vendor_id, days, limit)
    return json.dumps(
        {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name if vendor else "",
            "period_days": days,
            "po_count": len(history),
            "purchase_orders": history,
        }
    )


async def _get_po_summary() -> str:
    """PO counts and totals by status."""
    summary = await po_summary_by_status()
    total_count = sum(v["count"] for v in summary.values())
    total_value = round(sum(v["total"] for v in summary.values()), 2)
    return json.dumps(
        {
            "total_pos": total_count,
            "total_value": total_value,
            "by_status": summary,
        }
    )


async def _get_reorder_with_vendor_context(limit: int = 30) -> str:
    """Low-stock SKUs with vendor options for procurement planning."""
    limit = min(limit, 50)
    items = await reorder_with_vendor_context(limit)
    return json.dumps(
        {
            "count": len(items),
            "items": items,
        }
    )


async def _list_all_vendors() -> str:
    """List all vendors with contact details."""
    vendors = await list_vendors()
    out = [
        {
            "id": v.id,
            "name": v.name,
            "contact_name": v.contact_name,
            "email": v.email,
            "phone": v.phone,
        }
        for v in vendors
    ]
    return json.dumps({"count": len(out), "vendors": out})


async def _get_vendor_lead_times(vendor_id: str = "", name: str = "", days: int = 180) -> str:
    """Actual vendor lead times from PO data, with drift detection."""
    vendor_id = vendor_id.strip()
    days = min(days, 365)
    if not vendor_id:
        name = name.strip()
        if name:
            vendor = await find_vendor_by_name(name)
            if vendor:
                vendor_id = vendor.id
            else:
                return json.dumps({"error": f"Vendor '{name}' not found"})
        else:
            return json.dumps({"error": "vendor_id or name required"})

    vendor = await get_vendor_by_id(vendor_id)
    data = await vendor_lead_time_actual(vendor_id, days)
    data["vendor_name"] = vendor.name if vendor else ""
    return json.dumps(data)


async def _get_smart_reorder_points(limit: int = 30) -> str:
    """Velocity-based reorder points compared to static min_stock."""
    limit = min(limit, 50)
    items = await reorder_point_smart(limit=limit)
    return json.dumps(
        {
            "count": len(items),
            "items": items,
            "_note": "recommended_min_stock = normalized_daily_velocity * actual_vendor_lead_days * 1.5 safety factor",
        }
    )


# ── Registry ──────────────────────────────────────────────────────────────────

_reg(
    "get_vendor_catalog",
    "purchasing",
    _get_vendor_catalog,
    use_cases=["vendor catalog", "what does vendor sell"],
)
_reg(
    "get_vendor_performance",
    "purchasing",
    _get_vendor_performance,
    use_cases=["vendor reliability", "vendor metrics"],
)
_reg(
    "get_sku_vendor_options",
    "purchasing",
    _get_sku_vendor_options,
    use_cases=["vendor options", "alternative vendors"],
)
_reg(
    "get_purchase_history",
    "purchasing",
    _get_purchase_history,
    use_cases=["purchase history", "recent POs"],
)
_reg("get_po_summary", "purchasing", _get_po_summary, use_cases=["PO summary", "order status"])
_reg(
    "get_reorder_with_vendor_context",
    "purchasing",
    _get_reorder_with_vendor_context,
    use_cases=["reorder plan", "what to buy"],
)
_reg(
    "list_all_vendors",
    "purchasing",
    _list_all_vendors,
    use_cases=["all vendors", "vendor directory"],
)
_reg(
    "get_vendor_lead_times",
    "purchasing",
    _get_vendor_lead_times,
    use_cases=["lead times", "delivery time"],
)
_reg(
    "get_smart_reorder_points",
    "purchasing",
    _get_smart_reorder_points,
    use_cases=["smart reorder", "reorder calibration"],
)
