"""API test fixtures — uses the root session-scoped TestClient.

The DB is truncated and seeded before each test via portal.call()
for proper isolation.
"""

import pytest

from tests.helpers.auth import admin_headers, contractor_headers


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
def auth_headers() -> dict[str, str]:
    """Admin auth headers."""
    return admin_headers()


@pytest.fixture
def contractor_auth_headers() -> dict[str, str]:
    """Contractor auth headers."""
    return contractor_headers()
