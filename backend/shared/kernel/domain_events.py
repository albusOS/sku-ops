"""Typed domain events — structured facts that happened in the system.

Each bounded context emits these after its transaction commits. Other contexts
react by registering handlers via ``shared.infrastructure.domain_events.on()``.

Import rule: application and infrastructure layers import from here.
The kernel layer (this file) has zero imports from any bounded context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.kernel.event_payloads import LedgerItem, ReceivedItemSummary

from shared.helpers.uuid import new_uuid7_str

__all__ = [
    "CatalogChanged",
    "CreditNoteApplied",
    "DomainEvent",
    "InventoryChanged",
    "InvoiceApproved",
    "InvoiceCreated",
    "InvoiceDeleted",
    "LowStockDetected",
    "MaterialRequestCreated",
    "MaterialRequestProcessed",
    "POItemsReceived",
    "PaymentRecorded",
    "ReturnCreated",
    "WithdrawalCreated",
    "WithdrawalPaid",
]


@dataclass(frozen=True)
class DomainEvent:
    """Base for all typed domain events. Every event is scoped to an org.

    ``event_id`` is auto-generated so handlers can deduplicate processing.
    """

    org_id: str
    event_id: str = field(default_factory=new_uuid7_str)


# ── Operations context ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class WithdrawalCreated(DomainEvent):
    """Emitted after a material withdrawal is persisted and stock decremented."""

    withdrawal_id: str = ""
    sku_ids: tuple[str, ...] = ()
    contractor_id: str = ""
    job_id: str = ""
    billing_entity: str = ""
    tax: float = 0.0
    total: float = 0.0
    performed_by_user_id: str = ""
    ledger_items: tuple[LedgerItem, ...] = ()


@dataclass(frozen=True)
class WithdrawalPaid(DomainEvent):
    """Emitted after a withdrawal's payment_status is set to 'paid'."""

    withdrawal_id: str = ""
    amount: float = 0.0
    billing_entity: str = ""
    contractor_id: str = ""
    performed_by_user_id: str = ""


@dataclass(frozen=True)
class ReturnCreated(DomainEvent):
    """Emitted after a material return is persisted and stock restocked."""

    return_id: str = ""
    withdrawal_id: str = ""
    contractor_id: str = ""
    job_id: str = ""
    billing_entity: str = ""
    tax: float = 0.0
    total: float = 0.0
    performed_by_user_id: str = ""
    sku_ids: tuple[str, ...] = ()
    ledger_items: tuple[LedgerItem, ...] = ()
    invoice_id: str | None = None


@dataclass(frozen=True)
class MaterialRequestCreated(DomainEvent):
    """Emitted after a contractor's material request is persisted."""

    request_id: str = ""
    contractor_id: str = ""


@dataclass(frozen=True)
class MaterialRequestProcessed(DomainEvent):
    """Emitted after a material request is converted into a withdrawal."""

    request_id: str = ""
    withdrawal_id: str = ""


# ── Purchasing context ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class POItemsReceived(DomainEvent):
    """Emitted after PO items are received into inventory."""

    po_id: str = ""
    vendor_name: str = ""
    performed_by_user_id: str = ""
    items: tuple[ReceivedItemSummary, ...] = ()
    sku_ids: tuple[str, ...] = ()


# ── Inventory context ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InventoryChanged(DomainEvent):
    """Emitted whenever stock levels change.

    change_type is one of: withdrawal, receiving, adjustment, return, cycle_count.
    sku_ids is empty for bulk changes (e.g. cycle count).
    """

    sku_ids: tuple[str, ...] = ()
    change_type: str = ""


@dataclass(frozen=True)
class LowStockDetected(DomainEvent):
    """Emitted when a product's quantity drops to or below its reorder point (min_stock)."""

    sku_id: str = ""
    product_name: str = ""
    sku: str = ""
    current_qty: float = 0.0
    min_stock: float = 0.0


# ── Finance context ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PaymentRecorded(DomainEvent):
    """Emitted after a payment is recorded against one or more withdrawals."""

    withdrawal_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvoiceCreated(DomainEvent):
    """Emitted after an invoice is created from withdrawals."""

    invoice_id: str = ""
    withdrawal_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvoiceApproved(DomainEvent):
    """Emitted after a draft invoice is approved and locked."""

    invoice_id: str = ""


@dataclass(frozen=True)
class InvoiceDeleted(DomainEvent):
    """Emitted after a draft invoice is soft-deleted and withdrawals unlinked."""

    invoice_id: str = ""
    withdrawal_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CreditNoteApplied(DomainEvent):
    """Emitted after a credit note is applied to an invoice."""

    credit_note_id: str = ""
    invoice_id: str = ""


# ── Catalog context ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CatalogChanged(DomainEvent):
    """Emitted when products, SKUs, departments, or vendors are created/updated/deleted."""

    sku_ids: tuple[str, ...] = ()
    change_type: str = ""
