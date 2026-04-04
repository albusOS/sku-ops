"""Integration test fixtures — TestClient with portal for org-scoped operations.

Reuses the root session-scoped _app_client so there is only ever one
TestClient lifespan per pytest session. Multiple TestClient instances
against the same app object fight over the shared _state["backend"]
pool singleton, causing intermittent ConnectionDoesNotExistError when
one client's close_db() races with another's active queries.
"""
import pytest
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import ADMIN_USER_ID, admin_headers, contractor_headers

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
            org_id_var.set(DEFAULT_ORG_ID)
            user_id_var.set(ADMIN_USER_ID)
            return await async_fn()
        return _app_client.portal.call(_with_ctx)
    return _call
