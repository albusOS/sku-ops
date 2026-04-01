"""Row types for ledger analytics (shared by application queries and DB reporting)."""

from typing import TypedDict


class TrendPoint(TypedDict):
    date: str
    revenue: float
    cost: float
    shrinkage: float
    profit: float
    transaction_count: int


class ArAgingRow(TypedDict):
    billing_entity: str
    total_ar: float
    current_not_due: float
    overdue_1_30: float
    overdue_31_60: float
    overdue_61_90: float
    overdue_90_plus: float


class ProductMarginRow(TypedDict):
    sku_id: str
    revenue: float
    cost: float
    profit: float
    margin_pct: float
