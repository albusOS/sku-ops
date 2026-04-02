"""Smoke tests — health probes, auth enforcement, router mounting.

These run without DB and verify the API surface is correctly wired.
"""

import pytest

from tests.helpers.auth import admin_headers

PROTECTED_ENDPOINTS = [
    ("GET", "/api/beta/catalog/skus"),
    ("GET", "/api/beta/catalog/skus/by-barcode"),
    ("GET", "/api/beta/catalog/vendors"),
    ("GET", "/api/beta/catalog/departments"),
    ("GET", "/api/beta/operations/withdrawals"),
    ("GET", "/api/beta/operations/material-requests"),
    ("GET", "/api/beta/purchasing/purchase-orders"),
    ("GET", "/api/beta/finance/invoices"),
    ("GET", "/api/beta/finance/financials/summary"),
    ("POST", "/api/beta/assistant/chat"),
    ("GET", "/api/beta/shared/audit-log"),
    ("GET", "/api/beta/reports/dashboard/stats"),
    ("GET", "/api/beta/reports/dashboard/transactions"),
]


# ── Auth enforcement ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_endpoint_requires_auth(client, method, path):
    """Every protected endpoint must reject unauthenticated requests with 401 or 403."""
    response = client.request(method, path, json={})
    assert response.status_code in (401, 403), (
        f"{method} {path} returned {response.status_code} — "
        "expected 401/403 for unauthenticated request"
    )


# ── Router mount verification ─────────────────────────────────────────────────


def test_all_context_routers_mounted(client):
    """
    Verify every bounded context router is mounted by checking that a known
    endpoint returns 401/403 (auth required) rather than 404 (route not found).
    """
    context_probes = {
        "catalog": ("GET", "/api/beta/catalog/skus"),
        "operations": ("GET", "/api/beta/operations/withdrawals"),
        "purchasing": ("GET", "/api/beta/purchasing/purchase-orders"),
        "finance": ("GET", "/api/beta/finance/invoices"),
        "documents": ("POST", "/api/beta/documents/parse"),
        "assistant": ("POST", "/api/beta/assistant/chat"),
        "health": ("GET", "/api/beta/shared/health"),
    }
    not_mounted = []
    for ctx, (method, path) in context_probes.items():
        resp = client.request(method, path, json={})
        if resp.status_code == 404:
            not_mounted.append(f"{ctx}: {method} {path}")

    assert not not_mounted, (
        "These context routers appear unmounted (got 404):\n"
        + "\n".join(f"  {m}" for m in not_mounted)
    )


# ── Auth endpoint surface ─────────────────────────────────────────────────────


def test_auth_me_requires_auth(client):
    """/api/beta/shared/auth/me must reject unauthenticated requests."""
    resp = client.get("/api/beta/shared/auth/me")
    assert resp.status_code in (401, 403), (
        f"GET /api/beta/shared/auth/me returned {resp.status_code} — expected 401/403"
    )


def test_auth_login_endpoint_removed(client):
    """POST /api/beta/shared/auth/login must not be mounted anymore."""
    resp = client.post(
        "/api/beta/shared/auth/login",
        json={"email": "x@x.com", "password": "wrong"},
    )
    assert resp.status_code == 404


def test_auth_register_endpoint_removed(client):
    """POST /api/beta/shared/auth/register must not be mounted anymore."""
    resp = client.post(
        "/api/beta/shared/auth/register",
        json={"email": "x@x.com", "password": "pw", "name": "X"},
    )
    assert resp.status_code == 404


def test_auth_me_with_valid_token(client):
    """/api/beta/shared/auth/me with a valid token must not 404 or 500."""
    resp = client.get("/api/beta/shared/auth/me", headers=admin_headers())
    assert resp.status_code not in (404, 500), (
        f"GET /api/beta/shared/auth/me with valid token returned unexpected {resp.status_code}"
    )
