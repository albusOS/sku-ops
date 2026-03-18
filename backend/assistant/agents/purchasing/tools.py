"""Purchasing agent tool implementations — vendor analytics and procurement planning."""

import logging

from assistant.agents.tools.models import (
    ErrorResult,
    PoSummaryResult,
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
    """SKUs supplied by a vendor with cost, lead time, MOQ."""
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
    """Vendor reliability: PO count, spend, avg lead time, fill rate."""
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
    """All vendors for a SKU with comparative pricing and lead times."""
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
    """Recent POs for a vendor with item summaries."""
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
    """Low-stock SKUs with vendor options for procurement planning."""
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
    """Actual vendor lead times from PO data, with drift detection."""
    days = min(days, 365)
    vid, err = await _resolve_vendor_id(vendor_id, name)
    if err:
        return err
    vendor = await get_vendor_by_id(vid)
    data = await vendor_lead_time_actual(vid, days)
    data["vendor_name"] = vendor.name if vendor else ""
    return VendorLeadTimesResult(data=data).serialize()


async def _get_smart_reorder_points(limit: int = 30) -> str:
    """Velocity-based reorder points compared to static min_stock."""
    limit = min(limit, 50)
    items = await reorder_point_smart(limit=limit)
    return SmartReorderResult(count=len(items), items=items).serialize()


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
