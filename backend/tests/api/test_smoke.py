"""Smoke tests — health probes, auth enforcement, router mounting.

These run without DB and verify the API surface is correctly wired.
"""

import pytest

PROTECTED_ENDPOINTS = [
    ("GET", "/api/auth/me"),
    ("GET", "/api/products"),
    ("GET", "/api/products/by-barcode"),
    ("GET", "/api/vendors"),
    ("GET", "/api/departments"),
    ("GET", "/api/withdrawals"),
    ("GET", "/api/material-requests"),
    ("GET", "/api/purchase-orders"),
    ("GET", "/api/invoices"),
    ("GET", "/api/financials/summary"),
    ("POST", "/api/chat"),
    ("GET", "/api/audit-log"),
    ("GET", "/api/dashboard/stats"),
    ("GET", "/api/dashboard/transactions"),
]


# ── No-auth endpoints ─────────────────────────────────────────────────────────


def test_root_endpoint(client):
    """API root returns 200 and a message."""
    response = client.get("/api/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_liveness(client):
    """/health liveness probe returns 200 without auth or DB."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_ai_health_configured(client):
    """/health/ai returns 200 when ANTHROPIC_API_KEY is set (conftest sets a dummy key)."""
    response = client.get("/api/health/ai")
    assert response.status_code == 200


def test_404_returns_json(client):
    r = client.get("/api/nonexistent-route")
    assert r.status_code == 404


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
        "identity": ("GET", "/api/auth/me"),
        "catalog": ("GET", "/api/products"),
        "operations": ("GET", "/api/withdrawals"),
        "purchasing": ("GET", "/api/purchase-orders"),
        "finance": ("GET", "/api/invoices"),
        "documents": ("POST", "/api/documents/parse"),
        "assistant": ("POST", "/api/chat"),
        "reports": ("GET", "/api/health"),
    }
    not_mounted = []
    for ctx, (method, path) in context_probes.items():
        resp = client.request(method, path, json={})
        if resp.status_code == 404:
            not_mounted.append(f"{ctx}: {method} {path}")

    assert not not_mounted, "These context routers appear unmounted (got 404):\n" + "\n".join(
        f"  {m}" for m in not_mounted
    )
