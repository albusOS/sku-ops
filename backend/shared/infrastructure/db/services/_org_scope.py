"""Bind ambient ``org_id`` for code paths that still call ``get_org_id()``."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def scoped_org(org_id: str) -> AsyncIterator[None]:
    from shared.infrastructure.logging_config import org_id_var

    token = org_id_var.set(org_id)
    try:
        yield None
    finally:
        org_id_var.reset(token)


async def run_with_org(org_id: str, fn, /, *args, **kwargs):
    """Run ``await fn(*args, **kwargs)`` while ``get_org_id()`` resolves to ``org_id``."""
    async with scoped_org(org_id):
        return await fn(*args, **kwargs)
