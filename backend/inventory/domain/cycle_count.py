"""Cycle count domain — snapshot-based physical inventory counting."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from shared.kernel.entity import Entity


class CycleCountStatus(StrEnum):
    OPEN = "open"
    COMMITTED = "committed"


class CycleCount(Entity):
    """A counting session scoped to an org (and optionally a department)."""

    organization_id: str
    status: CycleCountStatus = CycleCountStatus.OPEN
    # None = full warehouse count; a department name scopes to that dept only.
    scope: str | None = None
    created_by_id: str
    created_by_name: str = ""
    committed_by_id: str | None = None
    committed_at: datetime | None = None


class CycleCountItem(Entity):
    """One product line within a cycle count session.

    Inherits org context from its parent CycleCount — the cycle_count_items
    table does not store organization_id independently.
    """

    organization_id: str = ""
    cycle_count_id: str
    sku_id: str
    sku: str
    product_name: str = ""
    # Frozen at the moment the count was opened — never changes after that.
    snapshot_qty: float
    counted_qty: float | None = None
    variance: float | None = None
    unit: str = "each"
    notes: str | None = None


class CycleCountDetail(BaseModel):
    """Count header plus all its line items — returned by get_count_detail."""

    id: str
    organization_id: str
    status: CycleCountStatus
    scope: str | None
    created_by_id: str
    created_by_name: str
    committed_by_id: str | None
    committed_at: datetime | None
    created_at: datetime
    items: list[CycleCountItem]


class CommitCycleCountResult(BaseModel):
    """Result of commit_cycle_count — includes the updated count + adjustment count."""

    id: str
    organization_id: str
    status: CycleCountStatus
    scope: str | None
    created_by_id: str
    created_by_name: str
    committed_by_id: str | None
    committed_at: datetime | None
    created_at: datetime
    items_adjusted: int
