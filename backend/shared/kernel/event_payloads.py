"""Structured payload value objects carried inside domain events.

These are pure immutable dataclasses — no imports from any bounded context.
They exist in the kernel because they cross context boundaries as event data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LedgerItem:
    """Line-item summary carried inside withdrawal/return events for ledger recording."""

    product_id: str | None
    quantity: float
    unit: str
    unit_price: float
    cost: float
    sell_uom: str | None = None
    sell_cost: float | None = None
    category_name: str | None = None


@dataclass(frozen=True)
class ReceivedItemSummary:
    """Line-item summary carried inside POItemsReceived for ledger recording."""

    product_id: str | None
    cost: float
    delivered_qty: float
    department: str | None = None
