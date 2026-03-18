"""Purchasing agent tool implementations — vendor analytics and procurement planning."""

import asyncio
import json
import logging

from assistant.agents.inventory.tools import _forecast_stockout
from assistant.agents.tools.models import (
    ErrorResult,
    PoSummaryResult,
    ProcurementSnapshotResult,
    PurchaseHistoryResult,
    ReorderContextResult,
    SkuVendorOptionsResult,
    SmartReorderResult,
    VendorCatalogResult,
    VendorDetail,
    VendorDirectoryResult,
    VendorLeadTimesResult,
    VendorPerformanceResult,
)
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


async def _resolve_vendor_id(vendor_id: str, name: str) -> tuple[str | None, str | None]:
    """Resolve vendor_id from name if needed. Returns (vendor_id, error_json) — one is always None."""
    vendor_id = vendor_id.strip()
    if vendor_id:
        return vendor_id, None
    name = name.strip()
    if name:
        vendor = await find_vendor_by_name(name)
        if vendor:
            return vendor.id, None
        return None, ErrorResult(error=f"Vendor '{name}' not found").serialize()
    return None, ErrorResult(error="vendor_id or name required").serialize()


async def _get_vendor_catalog(vendor_id: str = "", name: str = "") -> str:
    """Vendor catalog lookup. Best for "what does this vendor sell" questions."""
    vid, err = await _resolve_vendor_id(vendor_id, name)
    if err:
        return err
    vendor = await get_vendor_by_id(vid)
    items = await vendor_catalog(vid)
    return VendorCatalogResult(
        vendor_id=vid,
        vendor_name=vendor.name if vendor else "",
        sku_count=len(items),
        items=items,
    ).serialize()


async def _get_vendor_performance(vendor_id: str = "", name: str = "", days: int = 90) -> str:
    """Vendor scorecard. Use for vendor quality, spend, fill-rate, and reliability questions."""
    days = min(days, 365)
    vid, err = await _resolve_vendor_id(vendor_id, name)
    if err:
        return err
    vendor = await get_vendor_by_id(vid)
    perf = await vendor_performance(vid, days, vendor_name=vendor.name if vendor else "")
    return VendorPerformanceResult(
        vendor_id=perf.vendor_id,
        vendor_name=perf.vendor_name,
        days=perf.days,
        po_count=perf.po_count,
        total_spend=float(perf.total_spend),
        received_count=perf.received_count,
        avg_lead_time_days=float(perf.avg_lead_time_days)
        if perf.avg_lead_time_days is not None
        else None,
        fill_rate=float(perf.fill_rate) if perf.fill_rate is not None else None,
    ).serialize()


async def _get_sku_vendor_options(sku_id: str = "") -> str:
    """SKU sourcing lookup. Use for alternative vendors, pricing, and lead-time comparison."""
    sku_id = sku_id.strip()
    if not sku_id:
        return ErrorResult(error="sku_id required").serialize()
    if "-" not in sku_id:
        sku = await find_sku_by_sku_code(sku_id.upper())
        if not sku:
            return ErrorResult(error=f"SKU '{sku_id}' not found").serialize()
        sku_id = sku.id
    options = await sku_vendor_options(sku_id)
    return SkuVendorOptionsResult(
        sku_id=sku_id,
        vendor_count=len(options),
        vendors=options,
    ).serialize()


async def _get_purchase_history(
    vendor_id: str = "", name: str = "", days: int = 90, limit: int = 20
) -> str:
    """Vendor evidence lookup. Use only when recent PO examples are needed to support a conclusion."""
    days = min(days, 365)
    limit = min(limit, 50)
    vid, err = await _resolve_vendor_id(vendor_id, name)
    if err:
        return err
    vendor = await get_vendor_by_id(vid)
    history = await purchase_history(vid, days, limit)
    return PurchaseHistoryResult(
        vendor_id=vid,
        vendor_name=vendor.name if vendor else "",
        period_days=days,
        po_count=len(history),
        purchase_orders=history,
    ).serialize()


async def _get_po_summary() -> str:
    """PO counts and totals by status."""
    summary = await po_summary_by_status()
    total_count = sum(v["count"] for v in summary.values())
    total_value = round(sum(float(v["total"]) for v in summary.values()), 2)
    return PoSummaryResult(
        total_pos=total_count,
        total_value=total_value,
        by_status=summary,
    ).serialize()


async def _get_reorder_with_vendor_context(limit: int = 30) -> str:
    """Raw reorder list. Use when the agent needs the low-stock items plus vendor options per SKU."""
    limit = min(limit, 50)
    items = await reorder_with_vendor_context(limit)
    return ReorderContextResult(count=len(items), items=items).serialize()


async def _list_all_vendors() -> str:
    """List all vendors with contact details."""
    vendors = await list_vendors()
    details = [
        VendorDetail(
            id=v.id,
            name=v.name,
            contact_name=v.contact_name,
            email=v.email,
            phone=v.phone,
        )
        for v in vendors
    ]
    return VendorDirectoryResult(count=len(details), vendors=details).serialize()


async def _get_vendor_lead_times(vendor_id: str = "", name: str = "", days: int = 180) -> str:
    """Vendor lead-time lookup. Use for actual lead times, P90 risk, and drift detection."""
    days = min(days, 365)
    vid, err = await _resolve_vendor_id(vendor_id, name)
    if err:
        return err
    vendor = await get_vendor_by_id(vid)
    data = await vendor_lead_time_actual(vid, days)
    data["vendor_name"] = vendor.name if vendor else ""
    return VendorLeadTimesResult(data=data).serialize()


async def _get_smart_reorder_points(limit: int = 30) -> str:
    """Reorder-policy lookup. Use for min_stock calibration and smart reorder-point analysis."""
    limit = min(limit, 50)
    items = await reorder_point_smart(limit=limit)
    return SmartReorderResult(count=len(items), items=items).serialize()


async def _get_procurement_snapshot(limit: int = 20) -> str:
    """Broad procurement snapshot. Start here for weekly buy-plan and "what needs attention" questions."""
    limit = min(limit, 50)
    reorder_raw, smart_raw, stockout_raw = await asyncio.gather(
        _get_reorder_with_vendor_context(limit=limit),
        _get_smart_reorder_points(limit=limit),
        _forecast_stockout(limit=limit),
    )
    reorder_data = json.loads(reorder_raw)
    smart_data = json.loads(smart_raw)
    stockout_data = json.loads(stockout_raw)

    smart_by_sku = {item["sku"]: item for item in smart_data.get("items", [])}
    stockout_by_sku = {item["sku"]: item for item in stockout_data.get("forecast", [])}

    snapshot: list[dict] = []
    seen_skus: set[str] = set()

    for item in reorder_data.get("items", []):
        sku = item.get("sku", "")
        if not sku:
            continue
        seen_skus.add(sku)
        smart = smart_by_sku.get(sku, {})
        stockout = stockout_by_sku.get(sku, {})
        vendor_options = item.get("vendor_options", [])[:2]
        preferred = next((opt for opt in vendor_options if opt.get("is_preferred")), None)
        top_vendor = preferred or (vendor_options[0] if vendor_options else {})
        snapshot.append(
            {
                "sku_id": item.get("sku_id"),
                "sku": sku,
                "name": item.get("name"),
                "department": item.get("department"),
                "quantity": item.get("quantity"),
                "sell_uom": item.get("sell_uom"),
                "current_min_stock": item.get("min_stock"),
                "recommended_min_stock": smart.get("recommended_min_stock"),
                "min_stock_gap": smart.get("gap"),
                "min_stock_risk": smart.get("risk"),
                "reorder_deficit": item.get("deficit"),
                "days_until_stockout": stockout.get("days_until_stockout"),
                "avg_daily_use": stockout.get("avg_daily_use"),
                "preferred_vendor": top_vendor.get("vendor_name"),
                "vendor_lead_days": smart.get("vendor_lead_days")
                or top_vendor.get("lead_time_days"),
                "vendor_options": vendor_options,
            }
        )

    for item in smart_data.get("items", []):
        sku = item.get("sku", "")
        if not sku or sku in seen_skus:
            continue
        stockout = stockout_by_sku.get(sku, {})
        snapshot.append(
            {
                "sku_id": item.get("sku_id"),
                "sku": sku,
                "name": item.get("name"),
                "department": None,
                "quantity": item.get("quantity"),
                "sell_uom": item.get("sell_uom"),
                "current_min_stock": item.get("current_min_stock"),
                "recommended_min_stock": item.get("recommended_min_stock"),
                "min_stock_gap": item.get("gap"),
                "min_stock_risk": item.get("risk"),
                "reorder_deficit": None,
                "days_until_stockout": stockout.get("days_until_stockout"),
                "avg_daily_use": stockout.get("avg_daily_use"),
                "preferred_vendor": item.get("vendor_name"),
                "vendor_lead_days": item.get("vendor_lead_days"),
                "vendor_options": [],
            }
        )

    snapshot.sort(
        key=lambda item: (
            item.get("days_until_stockout") is None,
            item.get("days_until_stockout") or 10**9,
            -(item.get("reorder_deficit") or 0),
            -(item.get("min_stock_gap") or 0),
        )
    )
    return ProcurementSnapshotResult(
        count=len(snapshot[:limit]), items=snapshot[:limit]
    ).serialize()


# ── Registry ──────────────────────────────────────────────────────────────────

_reg(
    "get_vendor_catalog",
    "purchasing",
    _get_vendor_catalog,
    use_cases=["vendor catalog", "what does vendor sell", "vendor assortment", "items from vendor"],
)
_reg(
    "get_vendor_performance",
    "purchasing",
    _get_vendor_performance,
    use_cases=[
        "vendor reliability",
        "vendor metrics",
        "vendor scorecard",
        "fill rate",
        "vendor quality",
    ],
)
_reg(
    "get_sku_vendor_options",
    "purchasing",
    _get_sku_vendor_options,
    use_cases=["vendor options", "alternative vendors", "best vendor for sku", "source this sku"],
)
_reg(
    "get_purchase_history",
    "purchasing",
    _get_purchase_history,
    use_cases=[
        "purchase history",
        "recent POs",
        "purchase order evidence",
        "recent orders from vendor",
    ],
)
_reg("get_po_summary", "purchasing", _get_po_summary, use_cases=["PO summary", "order status"])
_reg(
    "get_reorder_with_vendor_context",
    "purchasing",
    _get_reorder_with_vendor_context,
    use_cases=["reorder plan", "what to buy", "low stock with vendors", "raw order candidates"],
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
    use_cases=["lead times", "delivery time", "vendor delay", "delivery drift", "p90 lead time"],
)
_reg(
    "get_smart_reorder_points",
    "purchasing",
    _get_smart_reorder_points,
    use_cases=["smart reorder", "reorder calibration", "min stock too low", "reorder policy"],
)
_reg(
    "get_procurement_snapshot",
    "purchasing",
    _get_procurement_snapshot,
    use_cases=[
        "what should I order",
        "weekly buy plan",
        "procurement snapshot",
        "what needs attention this week",
        "biggest procurement risks",
    ],
)
