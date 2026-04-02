"""Ambient contextvar for transactional ORM session."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_tx_session: ContextVar[AsyncSession | None] = ContextVar(
    "_tx_session", default=None
)


def get_tx_session() -> AsyncSession | None:
    return _tx_session.get()
