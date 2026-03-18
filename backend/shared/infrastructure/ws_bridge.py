"""WebSocket bridge — translates typed domain events to legacy WS notifications.

Registered as domain event handlers so the API layer no longer needs to call
``event_hub.emit()`` directly. The bridge also forwards inventory/catalog
changes to the search index invalidation path.
"""

from __future__ import annotations

from shared.infrastructure import event_hub
from shared.infrastructure.domain_events import on
from shared.kernel import events as ev
from shared.kernel.domain_events import (
    CatalogChanged,
    CreditNoteApplied,
    InventoryChanged,
    InvoiceApproved,
    InvoiceCreated,
    InvoiceDeleted,
    MaterialRequestCreated,
    MaterialRequestProcessed,
    PaymentRecorded,
    POItemsReceived,
    ReturnCreated,
    WithdrawalCreated,
    WithdrawalPaid,
)


@on(WithdrawalCreated)
async def _ws_withdrawal_created(event: WithdrawalCreated) -> None:
    await event_hub.emit(
        ev.WITHDRAWAL_CREATED,
        org_id=event.org_id,
        id=event.withdrawal_id,
    )


@on(WithdrawalPaid)
async def _ws_withdrawal_paid(event: WithdrawalPaid) -> None:
    await event_hub.emit(
        ev.WITHDRAWAL_UPDATED,
        org_id=event.org_id,
        id=event.withdrawal_id,
    )


@on(ReturnCreated)
async def _ws_return_created(event: ReturnCreated) -> None:
    await event_hub.emit(
        ev.WITHDRAWAL_UPDATED,
        org_id=event.org_id,
        id=event.withdrawal_id,
    )


@on(InventoryChanged)
async def _ws_inventory_changed(event: InventoryChanged) -> None:
    await event_hub.emit(
        ev.INVENTORY_UPDATED,
        org_id=event.org_id,
        ids=list(event.sku_ids),
    )


@on(POItemsReceived)
async def _ws_po_items_received(event: POItemsReceived) -> None:
    await event_hub.emit(
        ev.INVENTORY_UPDATED,
        org_id=event.org_id,
    )


@on(MaterialRequestCreated)
async def _ws_material_request_created(event: MaterialRequestCreated) -> None:
    await event_hub.emit(
        ev.MATERIAL_REQUEST_CREATED,
        org_id=event.org_id,
        id=event.request_id,
    )


@on(MaterialRequestProcessed)
async def _ws_material_request_processed(event: MaterialRequestProcessed) -> None:
    await event_hub.emit(
        ev.MATERIAL_REQUEST_PROCESSED,
        org_id=event.org_id,
        id=event.request_id,
        withdrawal_id=event.withdrawal_id,
    )


@on(PaymentRecorded)
async def _ws_payment_recorded(event: PaymentRecorded) -> None:
    await event_hub.emit(
        ev.WITHDRAWAL_UPDATED,
        org_id=event.org_id,
        ids=list(event.withdrawal_ids),
    )


# ── Invoice lifecycle ─────────────────────────────────────────────────────────


@on(InvoiceCreated)
async def _ws_invoice_created(event: InvoiceCreated) -> None:
    await event_hub.emit(
        ev.INVOICE_UPDATED,
        org_id=event.org_id,
        id=event.invoice_id,
    )


@on(InvoiceApproved)
async def _ws_invoice_approved(event: InvoiceApproved) -> None:
    await event_hub.emit(
        ev.INVOICE_UPDATED,
        org_id=event.org_id,
        id=event.invoice_id,
    )


@on(InvoiceDeleted)
async def _ws_invoice_deleted(event: InvoiceDeleted) -> None:
    await event_hub.emit(
        ev.INVOICE_UPDATED,
        org_id=event.org_id,
        id=event.invoice_id,
    )
    if event.withdrawal_ids:
        await event_hub.emit(
            ev.WITHDRAWAL_UPDATED,
            org_id=event.org_id,
            ids=list(event.withdrawal_ids),
        )


@on(CreditNoteApplied)
async def _ws_credit_note_applied(event: CreditNoteApplied) -> None:
    await event_hub.emit(
        ev.WITHDRAWAL_UPDATED,
        org_id=event.org_id,
    )
    if event.invoice_id:
        await event_hub.emit(
            ev.INVOICE_UPDATED,
            org_id=event.org_id,
            id=event.invoice_id,
        )


# ── Catalog changes ──────────────────────────────────────────────────────────


@on(CatalogChanged)
async def _ws_catalog_changed(event: CatalogChanged) -> None:
    await event_hub.emit(
        ev.CATALOG_UPDATED,
        org_id=event.org_id,
        ids=list(event.sku_ids),
    )
