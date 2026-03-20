"""Typed result models for agent tool functions.

Every tool function returns ``str`` (required by PydanticAI).  These models
define the *shape* of that JSON string so the type checker catches schema drift
and ``serialize()`` always handles Decimal → float conversion.

Convention: tool functions construct a model, call ``.serialize()``, done.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from assistant.agents.tools.serialization import dumps as _dumps

# ── Base ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolModel:
    """Base for all tool result models.  Provides Decimal-safe serialization."""

    def serialize(self) -> str:
        return _dumps(asdict(self))


@dataclass(frozen=True)
class ErrorResult(ToolModel):
    error: str


# ── Shared primitives ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SkuSummary:
    sku: str
    name: str
    quantity: float
    sell_uom: str
    min_stock: float
    department: str


@dataclass(frozen=True)
class SkuRanked:
    sku: str
    name: str
    total_units: float
    total_revenue: float


@dataclass(frozen=True)
class WithdrawalSummary:
    date: str
    job_id: str | None
    contractor: str | None
    service_address: str | None
    total: float
    payment_status: str | None
    item_count: int


@dataclass(frozen=True)
class WithdrawalDetail:
    date: str
    job_id: str | None
    service_address: str | None
    contractor: str | None
    company: str | None
    total: float
    cost_total: float
    payment_status: str | None
    item_count: int


@dataclass(frozen=True)
class JobMaterialItem:
    sku: str
    name: str
    quantity: float
    unit: str | None
    price: float
    subtotal: float


@dataclass(frozen=True)
class PendingRequest:
    id: str
    contractor: str | None
    job_id: str | None
    service_address: str | None
    notes: str | None
    item_count: int
    requested_at: str


@dataclass(frozen=True)
class DepartmentInfo:
    name: str
    code: str
    sku_count: int
    sku_format: str


@dataclass(frozen=True)
class DepartmentHealth:
    name: str
    code: str
    sku_count: int
    out_of_stock: int
    low_stock: int
    healthy: int


@dataclass(frozen=True)
class VendorSummary:
    id: str
    name: str


@dataclass(frozen=True)
class VendorDetail:
    id: str
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None


@dataclass(frozen=True)
class StockoutItem:
    sku: str
    name: str
    department: str | None
    quantity: float
    sell_uom: str | None
    min_stock: float
    avg_daily_use: float
    days_until_stockout: float
    risk: str
    outlier_days_excluded: int


@dataclass(frozen=True)
class SlowMover:
    sku: str
    name: str
    quantity: float
    sell_uom: str
    department: str | None
    units_withdrawn_30d: float


@dataclass(frozen=True)
class ReorderSuggestion:
    sku: str
    name: str
    quantity: float
    sell_uom: str | None
    min_stock: float
    avg_daily_use: float
    days_until_stockout: float | None
    urgency: str
    outlier_days_excluded: int


@dataclass(frozen=True)
class EntityBalance:
    entity: str
    balance: float
    withdrawal_count: int
    oldest_unpaid: str


@dataclass(frozen=True)
class InvoiceStatusGroup:
    count: int
    total: float


# ── Inventory results ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SkuSearchResult(ToolModel):
    count: int
    skus: list[SkuSummary]


@dataclass(frozen=True)
class SemanticSearchResult(ToolModel):
    count: int
    skus: list[SkuSummary]
    method: str


@dataclass(frozen=True)
class SkuDetail(ToolModel):
    sku: str
    name: str
    description: str | None
    price: float
    cost: float
    quantity: float
    min_stock: float
    department: str | None
    barcode: str | None
    base_unit: str | None
    sell_uom: str | None
    pack_qty: float | None
    purchase_uom: str | None
    purchase_pack_qty: float | None


@dataclass(frozen=True)
class InventoryStats(ToolModel):
    total_skus: int
    total_cost_value: float
    low_stock_count: int
    out_of_stock_count: int
    _note: str = "total_skus is the count of distinct SKUs. No meaningful total unit count exists because SKUs are measured in different units (each, gallon, box, etc.)."


@dataclass(frozen=True)
class DepartmentListResult(ToolModel):
    departments: list[DepartmentInfo]


@dataclass(frozen=True)
class VendorListResult(ToolModel):
    vendors: list[VendorSummary]


@dataclass(frozen=True)
class UsageVelocityResult(ToolModel):
    sku: str
    name: str
    sell_uom: str
    current_quantity: float
    period_days: int
    total_withdrawn: float
    avg_daily_use: float
    days_until_stockout: float | None
    _note: str | None = None


@dataclass(frozen=True)
class ReorderSuggestionsResult(ToolModel):
    count: int
    suggestions: list[ReorderSuggestion]
    _note: str = (
        "Velocity uses normalized demand (IQR outlier stripping) to exclude one-time project buys."
    )


@dataclass(frozen=True)
class DepartmentHealthResult(ToolModel):
    departments: list[DepartmentHealth]


@dataclass(frozen=True)
class TopSkusResult(ToolModel):
    period_days: int
    ranked_by: str
    count: int
    skus: list[SkuRanked]


@dataclass(frozen=True)
class DepartmentActivityResult(ToolModel):
    dept_code: str
    period_days: int
    sku_count: int
    low_stock_count: int
    withdrawals: dict[str, float]


@dataclass(frozen=True)
class StockoutForecastResult(ToolModel):
    count: int
    forecast: list[StockoutItem]
    _note: str = (
        "Velocity uses normalized demand (IQR outlier stripping) to exclude one-time project buys."
    )


@dataclass(frozen=True)
class SlowMoversResult(ToolModel):
    period_days: int
    count: int
    slow_movers: list[SlowMover]


@dataclass(frozen=True)
class SemanticEntityResult(ToolModel):
    """Generic result for semantic entity searches (vendors, POs, jobs)."""

    count: int
    items: list[dict[str, Any]]
    entity_type: str


@dataclass(frozen=True)
class DemandProfileResult(ToolModel):
    """Wraps the raw demand profile dict from inventory queries."""

    profile: dict[str, Any]


@dataclass(frozen=True)
class SeasonalPatternResult(ToolModel):
    sku: str
    name: str
    sell_uom: str
    months_requested: int
    months_with_data: int
    monthly: list[dict[str, Any]]


# ── Ops results ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContractorHistoryResult(ToolModel):
    contractor_search: str
    count: int
    total_spent: float
    unpaid_balance: float
    withdrawals: list[WithdrawalDetail]


@dataclass(frozen=True)
class JobMaterialsResult(ToolModel):
    job_id: str
    service_address: str | None
    contractor: str | None
    withdrawal_count: int
    total: float
    items: list[JobMaterialItem]


@dataclass(frozen=True)
class RecentWithdrawalsResult(ToolModel):
    period_days: int
    count: int
    total_value: float
    withdrawals: list[WithdrawalSummary]


@dataclass(frozen=True)
class PendingRequestsResult(ToolModel):
    count: int
    pending_requests: list[PendingRequest]


@dataclass(frozen=True)
class DailyActivityResult(ToolModel):
    period_days: int
    data_points: int
    activity: list[dict[str, Any]]


@dataclass(frozen=True)
class PaymentStatusResult(ToolModel):
    period_days: int
    total: float
    by_status: dict[str, float]


# ── Finance results ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InvoiceSummaryResult(ToolModel):
    total_invoices: int
    grand_total: float
    by_status: dict[str, InvoiceStatusGroup]


@dataclass(frozen=True)
class OutstandingBalancesResult(ToolModel):
    total_outstanding: float
    entity_count: int
    balances: list[EntityBalance]


@dataclass(frozen=True)
class RevenueSummaryResult(ToolModel):
    period_days: int
    transaction_count: int
    total_revenue: float
    total_tax: float
    revenue_ex_tax: float
    paid: float
    unpaid: float
    invoiced: float


@dataclass(frozen=True)
class PlSummaryResult(ToolModel):
    period_days: int
    transaction_count: int
    revenue: float
    cost_of_goods: float
    gross_profit: float
    gross_margin_pct: float


@dataclass(frozen=True)
class TrendSeriesResult(ToolModel):
    period_days: int
    group_by: str
    data_points: int
    series: list[dict[str, Any]]


@dataclass(frozen=True)
class ArAgingResult(ToolModel):
    total_ar: float
    entity_count: int
    buckets: list[dict[str, Any]]


@dataclass(frozen=True)
class SkuMarginsResult(ToolModel):
    period_days: int
    count: int
    skus: list[dict[str, Any]]


@dataclass(frozen=True)
class DeptProfitabilityResult(ToolModel):
    period_days: int
    department_count: int
    departments: list[dict[str, Any]]


@dataclass(frozen=True)
class JobProfitabilityResult(ToolModel):
    period_days: int
    total_jobs: int
    all_revenue: float
    all_cost: float
    jobs: list[dict[str, Any]]


@dataclass(frozen=True)
class EntitySummaryResult(ToolModel):
    period_days: int
    entity_count: int
    entities: list[dict[str, Any]]


@dataclass(frozen=True)
class ContractorSpendResult(ToolModel):
    period_days: int
    contractor_count: int
    contractors: list[dict[str, Any]]


@dataclass(frozen=True)
class PurchaseSpendResult(ToolModel):
    period_days: int
    total_purchase_spend: float


@dataclass(frozen=True)
class CarryingCostResult(ToolModel):
    holding_rate_pct: float
    total_carrying_cost: float
    sku_count: int
    by_department: dict[str, float]
    top_items: list[dict[str, Any]]
    _note: str = ""


# ── Purchasing results ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class VendorCatalogResult(ToolModel):
    vendor_id: str
    vendor_name: str
    sku_count: int
    items: list[dict[str, Any]]


@dataclass(frozen=True)
class VendorPerformanceResult(ToolModel):
    vendor_id: str
    vendor_name: str
    days: int
    po_count: int
    total_spend: float
    received_count: int
    avg_lead_time_days: float | None
    fill_rate: float | None


@dataclass(frozen=True)
class SkuVendorOptionsResult(ToolModel):
    sku_id: str
    vendor_count: int
    vendors: list[dict[str, Any]]


@dataclass(frozen=True)
class PurchaseHistoryResult(ToolModel):
    vendor_id: str
    vendor_name: str
    period_days: int
    po_count: int
    purchase_orders: list[dict[str, Any]]


@dataclass(frozen=True)
class PoSummaryResult(ToolModel):
    total_pos: int
    total_value: float
    by_status: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ReorderContextResult(ToolModel):
    count: int
    items: list[dict[str, Any]]


@dataclass(frozen=True)
class VendorDirectoryResult(ToolModel):
    count: int
    vendors: list[VendorDetail]


@dataclass(frozen=True)
class VendorLeadTimesResult(ToolModel):
    data: dict[str, Any]


@dataclass(frozen=True)
class SmartReorderResult(ToolModel):
    count: int
    items: list[dict[str, Any]]
    _note: str = "recommended_min_stock = normalized_daily_velocity * actual_vendor_lead_days * 1.5 safety factor"


@dataclass(frozen=True)
class ProcurementSnapshotResult(ToolModel):
    count: int
    items: list[dict[str, Any]]
    _note: str = (
        "Bundled procurement view for broad ordering questions. "
        "Combines reorder deficit, smart min_stock gap, stockout timing, and preferred vendor context."
    )


# ── Product analyst results ───────────────────────────────────────────────────


@dataclass(frozen=True)
class CatalogSearchResult(ToolModel):
    skus: list[dict[str, Any]]
    families: list[dict[str, Any]]


@dataclass(frozen=True)
class FamilySkusResult(ToolModel):
    skus: list[dict[str, Any]]


@dataclass(frozen=True)
class VendorItemMatch(ToolModel):
    match: dict[str, Any] | None
    reason: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class DepartmentCodesResult(ToolModel):
    departments: list[dict[str, Any]]
    error: str | None = None
