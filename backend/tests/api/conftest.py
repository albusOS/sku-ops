"""API test fixtures — HTTP client and auth headers."""

import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from tests.helpers.auth import admin_headers, contractor_headers


@pytest.fixture
def client():
    """HTTP client for in-process API tests (no network)."""
    from server import app

    return TestClient(app)


@pytest_asyncio.fixture
async def db():
    """Initialize in-memory DB, seed minimal data. Cleanup on teardown.

    Duplicated from integration/conftest.py because API workflow tests
    that exercise the full stack also need a seeded DB.
    """
    from shared.infrastructure.database import close_db, get_connection, init_db

    await init_db()
    conn = get_connection()
    await conn.execute(
        """INSERT OR REPLACE INTO departments (id, name, code, description, product_count, organization_id, created_at)
           VALUES ('dept-1', 'Hardware', 'HDW', 'Hardware dept', 0, 'default', datetime('now'))"""
    )
    await conn.execute(
        """INSERT OR REPLACE INTO users (id, email, password, name, role, is_active, organization_id, created_at)
           VALUES ('user-1', 'test@test.com', 'hash', 'Test User', 'admin', 1, 'default', datetime('now'))"""
    )
    await conn.execute(
        """INSERT OR REPLACE INTO users (id, email, password, name, role, company, billing_entity, is_active, organization_id, created_at)
           VALUES ('contractor-1', 'contractor@test.com', 'hash', 'Contractor User', 'contractor', 'ACME', 'ACME Inc', 1, 'default', datetime('now'))"""
    )
    await conn.commit()

    yield
    await close_db()


@pytest_asyncio.fixture
async def _db(db):
    """Alias for ``db``."""
    yield


@pytest.fixture
def auth_headers():
    """Admin auth headers."""
    return admin_headers()


@pytest.fixture
def contractor_auth_headers():
    """Contractor auth headers."""
    return contractor_headers()
