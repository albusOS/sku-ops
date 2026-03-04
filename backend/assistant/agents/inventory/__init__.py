"""Inventory agent package — backward-compatible re-exports."""
from .agent import run, _agent, SYSTEM_PROMPT
from .tools import (
    _search_products, _search_semantic, _get_product_details,
    _get_inventory_stats, _list_low_stock, _list_departments,
    _list_vendors, _get_usage_velocity, _get_reorder_suggestions,
    _get_department_health, _get_slow_movers,
)
