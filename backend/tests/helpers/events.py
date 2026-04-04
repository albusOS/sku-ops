"""Reusable domain event collector for test assertions.

Usage in tests::

    async def test_something(db, event_collector):
        await some_use_case(...)
        assert event_collector.of_type(WithdrawalCreated)
        evt = event_collector.of_type(WithdrawalCreated)[0]
        assert evt.withdrawal_id == "..."
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.kernel.domain_events import DomainEvent

class EventCollector:
    """Captures domain events dispatched during a test.

    Wraps the real ``dispatch`` so handlers still execute, but every event
    is also recorded for later assertion.
    """

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def capture(self, event: DomainEvent) -> None:
        """Append event to the captured list. Intended as a dispatch wrapper."""
        self.events.append(event)

    def of_type(self, cls: type[DomainEvent]) -> list[DomainEvent]:
        """Return all captured events matching *cls*."""
        return [e for e in self.events if isinstance(e, cls)]

    def clear(self) -> None:
        self.events.clear()

    def __len__(self) -> int:
        return len(self.events)

    def __bool__(self) -> bool:
        return bool(self.events)
