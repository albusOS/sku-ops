"""Base class for per-context database services (SQLModel / session access)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from shared.infrastructure.db import uow

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.infrastructure.db.base import BaseDatabaseService


class DomainDatabaseService:
    def __init__(self, db_service: BaseDatabaseService) -> None:
        self.db_service = db_service

    @staticmethod
    async def end_write_session(session: AsyncSession) -> None:
        """Commit standalone sessions; flush when participating in ambient transaction."""
        ambient = uow._tx_session.get()
        if ambient is not None and ambient is session:
            await session.flush()
        else:
            await session.commit()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        # Deferred import: package __init__ imports this module during startup.
        from shared.infrastructure.db import get_session  # noqa: PLC0415

        async with get_session() as session:
            yield session
