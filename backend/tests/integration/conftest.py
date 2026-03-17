"""Integration test fixtures — TestClient with portal for org-scoped operations.

Uses its own session-scoped _app_client so the event loop is independent
from the api/ test suite. Each test gets a clean DB via the autouse
_clean_db fixture.
"""

import pytest

from tests.helpers.auth import admin_headers, contractor_headers


@pytest.fixture(scope="session")
def _app_client():
    """Session-scoped TestClient for integration tests — independent event loop."""
    from starlette.testclient import TestClient

    from server import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(autouse=True)
def _clean_db(_app_client):
    """Truncate and seed before each test for isolation."""
    from tests.conftest import _truncate_and_seed

    _app_client.portal.call(_truncate_and_seed)


@pytest.fixture
def client(_app_client):
    """Per-test alias for the TestClient."""
    return _app_client


@pytest.fixture
def auth() -> dict[str, str]:
    """Admin auth headers."""
    return admin_headers()


@pytest.fixture
def contractor_auth() -> dict[str, str]:
    """Contractor auth headers."""
    return contractor_headers()


@pytest.fixture
def call(_app_client):
    """Execute an async callable in the ASGI event loop with org context.

    Usage::

        def test_something(call):
            async def _body():
                result = await some_async_fn()
                assert result is not None

            call(_body)
    """

    def _call(async_fn):
        async def _with_ctx():
            from shared.infrastructure.logging_config import org_id_var, user_id_var

            org_id_var.set("default")
            user_id_var.set("user-1")
            return await async_fn()

        return _app_client.portal.call(_with_ctx)

    return _call
