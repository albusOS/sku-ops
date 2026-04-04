"""API test fixtures — uses the root session-scoped TestClient.

The DB is truncated and seeded before each test via portal.call()
for proper isolation.
"""
import pytest

from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import BCRYPT_USER_ID, admin_headers, contractor_headers


@pytest.fixture(autouse=True)
def _clean_db(_app_client):
    """Truncate and seed before each test for isolation."""
    from tests.conftest import _truncate_and_seed
    _app_client.portal.call(_truncate_and_seed)

@pytest.fixture
def client(_app_client):
    """Per-test alias for the session-scoped TestClient."""
    return _app_client

@pytest.fixture
def db(_clean_db):
    """Legacy alias — DB is now auto-cleaned by _clean_db."""
    return

@pytest.fixture
def _db(_clean_db):
    """Legacy alias — DB is now auto-cleaned by _clean_db."""
    return

@pytest.fixture
def _db_with_bcrypt_user(db, _app_client):
    """DB with a user whose password is a real bcrypt hash."""
    import bcrypt

    from shared.infrastructure.db import sql_execute

    async def _seed():
        hashed = bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode("utf-8")
        await sql_execute(f"INSERT INTO users (id, email, password, name, role, is_active, organization_id, created_at) VALUES ('{BCRYPT_USER_ID}', 'bcrypt@test.com', $1, 'Bcrypt User', 'admin', TRUE, $2, NOW()) ON CONFLICT (id) DO UPDATE SET password = EXCLUDED.password", (hashed, DEFAULT_ORG_ID))
    _app_client.portal.call(_seed)

@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Admin auth headers."""
    return admin_headers()

@pytest.fixture
def contractor_auth_headers() -> dict[str, str]:
    """Contractor auth headers."""
    return contractor_headers()
