"""Integration test fixtures for SQLModel DB tests.

Requires a running local Supabase/Postgres instance.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession


@pytest.fixture(scope="session")
def database_url():
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


@pytest.fixture(scope="session")
def async_engine(database_url):
    return create_async_engine(database_url, echo=False)


@pytest.fixture
async def session(async_engine):
    async with SQLModelAsyncSession(async_engine) as session:
        yield session
        await session.rollback()
