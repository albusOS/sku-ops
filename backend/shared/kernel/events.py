"""WebSocket relay event types — the wire format for real-time UI notifications.

This module owns:
- ``Event`` — the untyped envelope delivered over the WebSocket channel
- ``SHUTDOWN`` — sentinel used to signal subscriber queues to exit
- ``is_shutdown`` — predicate for the sentinel
- String event-type constants — the ``type`` field values sent to the browser
- ``CONTRACTOR_VISIBLE_EVENTS`` — visibility policy for contractor WS connections

For domain logic that reacts to business facts, use the typed dataclasses in
``shared.kernel.domain_events`` and the dispatcher in
``shared.infrastructure.domain_events``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """Untyped envelope published to the WebSocket / Redis relay channel."""

    type: str
    org_id: str
    data: dict[str, Any] = field(default_factory=dict)
    user_id: str = ""


SHUTDOWN = Event(type="__shutdown__", org_id="")
"""Sentinel pushed to a subscriber queue to signal the reader to exit."""


def is_shutdown(event: Event) -> bool:
    return event.type == "__shutdown__"


# ── Event type constants ──────────────────────────────────────────────────────
# These are the ``type`` strings that reach the browser via WebSocket.

INVENTORY_UPDATED = "inventory.updated"
CATALOG_UPDATED = "catalog.updated"

WITHDRAWAL_CREATED = "withdrawal.created"
WITHDRAWAL_UPDATED = "withdrawal.updated"

INVOICE_UPDATED = "invoice.updated"

MATERIAL_REQUEST_CREATED = "material_request.created"
MATERIAL_REQUEST_PROCESSED = "material_request.processed"

CHAT_DONE = "chat.done"
CHAT_ERROR = "chat.error"
CHAT_CHUNK = "chat.chunk"
CHAT_COST = "chat.cost"
CHAT_TOOL_CALL = "chat.tool_call"


# ── Visibility policy ─────────────────────────────────────────────────────────

CONTRACTOR_VISIBLE_EVENTS = frozenset(
    {
        MATERIAL_REQUEST_CREATED,
        MATERIAL_REQUEST_PROCESSED,
        WITHDRAWAL_CREATED,
        WITHDRAWAL_UPDATED,
    }
)
