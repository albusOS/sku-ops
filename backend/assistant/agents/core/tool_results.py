"""Typed tool result wrapper — text for LLM context, optional blocks for frontend.

Block schemas:
- data_table: {type, title, columns, rows, actions?}
- stat_group: {type, stats: [{label, value, trend?, status?}]}
- entity_card: {type, entity_type, entity_id, data, actions?}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Wrapper for tool output: text for LLM context, optional blocks for frontend."""

    text: str
    data: dict[str, Any] | None = None
    blocks: list[dict[str, Any]] | None = None


def _safe_parse(data: str) -> dict[str, Any] | None:
    """Parse JSON safely; return None on failure."""
    try:
        return json.loads(data) if isinstance(data, str) else data
    except (json.JSONDecodeError, TypeError):
        return None


def blocks_from_inventory_stats(raw: str) -> list[dict[str, Any]]:
    """Build stat_group block from get_inventory_stats JSON."""
    d = _safe_parse(raw)
    if not d:
        return []
    stats = [
        {"label": "Total SKUs", "value": str(d.get("total_skus", 0))},
        {"label": "Cost value", "value": f"${d.get('total_cost_value', 0):,.2f}"},
        {"label": "Low stock", "value": str(d.get("low_stock_count", 0))},
        {"label": "Out of stock", "value": str(d.get("out_of_stock_count", 0))},
    ]
    return [{"type": "stat_group", "stats": stats}]


def blocks_from_list_data(raw: str, title: str, columns: list[str]) -> list[dict[str, Any]]:
    """Build data_table block from list-based tool JSON (products, suggestions, balances)."""
    d = _safe_parse(raw)
    if not d:
        return []
    if "products" in d:
        rows = [[str(item.get(c, "")) for c in columns] for item in d["products"][:50]]
    elif "suggestions" in d:
        rows = [[str(item.get(c, "")) for c in columns] for item in d["suggestions"][:50]]
    elif "balances" in d:
        rows = [[str(item.get(c, "")) for c in columns] for item in d["balances"][:50]]
    else:
        return []
    return [{"type": "data_table", "title": title, "columns": columns, "rows": rows}]


def blocks_from_pl_summary(raw: str) -> list[dict[str, Any]]:
    """Build stat_group block from get_pl_summary JSON."""
    d = _safe_parse(raw)
    if not d:
        return []
    stats = [
        {"label": "Revenue", "value": f"${d.get('revenue', 0):,.2f}"},
        {"label": "COGS", "value": f"${d.get('cost_of_goods', 0):,.2f}"},
        {"label": "Gross profit", "value": f"${d.get('gross_profit', 0):,.2f}"},
        {"label": "Margin", "value": f"{d.get('gross_margin_pct', 0)}%"},
    ]
    return [{"type": "stat_group", "stats": stats}]


def blocks_from_trend_series(raw: str) -> list[dict[str, Any]]:
    """Build chart block from get_trend_series JSON."""
    d = _safe_parse(raw)
    if not d or "series" not in d:
        return []
    series_data = d["series"]
    if not series_data:
        return []
    return [
        {
            "type": "chart",
            "chart_type": "line",
            "title": "Revenue & profit trend",
            "data": series_data,
            "x_key": "date",
            "series": [
                {"key": "revenue", "label": "Revenue"},
                {"key": "cost", "label": "Cost"},
                {"key": "profit", "label": "Profit"},
            ],
            "value_format": "currency",
        }
    ]


def blocks_from_department_health(raw: str) -> list[dict[str, Any]]:
    """Build chart block from get_department_health JSON."""
    d = _safe_parse(raw)
    if not d or "departments" not in d:
        return []
    depts = d["departments"]
    if not depts:
        return []
    return [
        {
            "type": "chart",
            "chart_type": "stacked_bar",
            "title": "Department stock health",
            "data": depts,
            "category_key": "name",
            "series": [
                {"key": "healthy", "label": "Healthy"},
                {"key": "low_stock", "label": "Low stock"},
                {"key": "out_of_stock", "label": "Out of stock"},
            ],
        }
    ]


def blocks_from_top_products(raw: str) -> list[dict[str, Any]]:
    """Build chart block from get_top_products JSON."""
    d = _safe_parse(raw)
    if not d or "products" not in d:
        return []
    products = d["products"][:10]
    if not products:
        return []
    # Detect if revenue-ranked or volume-ranked
    has_revenue = any(p.get("revenue") for p in products)
    value_key = "revenue" if has_revenue else "total_withdrawn"
    value_label = "Revenue" if has_revenue else "Units"
    value_format = "currency" if has_revenue else "number"
    return [
        {
            "type": "chart",
            "chart_type": "bar",
            "title": f"Top products by {value_label.lower()}",
            "data": products,
            "category_key": "name",
            "series": [{"key": value_key, "label": value_label}],
            "value_format": value_format,
        }
    ]
