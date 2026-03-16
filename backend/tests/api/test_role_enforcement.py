"""Role enforcement — verify admin-only endpoints reject contractors.

Contractors should be able to access CurrentUserDep endpoints (material
requests, withdrawals list, products read, etc.) but must be rejected
from AdminDep endpoints with 403.
"""

import pytest

from tests.helpers.auth import admin_headers, contractor_headers, expired_token, make_token

# ── Admin-only endpoints (AdminDep) — contractors must get 403 ───────────────

ADMIN_ONLY_ENDPOINTS = [
    ("GET", "/api/reports/sales"),
    ("GET", "/api/reports/inventory"),
    ("GET", "/api/audit-log"),
    ("POST", "/api/departments", {"name": "Test", "code": "TST"}),
    ("GET", "/api/vendors"),
    ("POST", "/api/vendors", {"name": "Test Vendor"}),
    ("GET", "/api/invoices"),
    ("GET", "/api/contractors"),
]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [(m, p, b if len(t) > 2 else {}) for t in ADMIN_ONLY_ENDPOINTS for m, p, *b in [t]],
    ids=[f"{m} {p}" for m, p, *_ in ADMIN_ONLY_ENDPOINTS],
)
def test_contractor_rejected_from_admin_endpoint(client, method, path, body):
    """Contractors must receive 403 from admin-only endpoints."""
    resp = client.request(method, path, headers=contractor_headers(), json=body)
    assert resp.status_code == 403, (
        f"{method} {path} returned {resp.status_code} for contractor — expected 403"
    )


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [(m, p, b if len(t) > 2 else {}) for t in ADMIN_ONLY_ENDPOINTS for m, p, *b in [t]],
    ids=[f"{m} {p}" for m, p, *_ in ADMIN_ONLY_ENDPOINTS],
)
def test_admin_accepted_at_admin_endpoint(client, method, path, body):
    """Admins must not get 401/403 from admin-only endpoints."""
    resp = client.request(method, path, headers=admin_headers(), json=body)
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for admin — expected access granted"
    )


# ── Contractor-accessible endpoints (CurrentUserDep) ────────────────────────

CONTRACTOR_ACCESSIBLE_ENDPOINTS = [
    ("GET", "/api/departments"),
    ("GET", "/api/material-requests"),
    ("GET", "/api/withdrawals"),
    ("GET", "/api/catalog/skus"),
]


@pytest.mark.parametrize(
    ("method", "path"),
    CONTRACTOR_ACCESSIBLE_ENDPOINTS,
    ids=[f"{m} {p}" for m, p in CONTRACTOR_ACCESSIBLE_ENDPOINTS],
)
def test_contractor_can_access_shared_endpoints(client, method, path):
    """Contractors must be able to access CurrentUserDep endpoints."""
    resp = client.request(method, path, headers=contractor_headers())
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for contractor — expected access granted"
    )


# ── Token edge cases on HTTP endpoints ───────────────────────────────────────


def test_expired_token_rejected(client):
    """Expired JWT must return 401, not 500."""
    headers = {"Authorization": f"Bearer {expired_token()}"}
    resp = client.get("/api/departments", headers=headers)
    assert resp.status_code == 401
    assert "expired" in resp.json().get("detail", "").lower()


def test_garbage_token_rejected(client):
    """Malformed token must return 401."""
    headers = {"Authorization": "Bearer not-a-real-token"}
    resp = client.get("/api/departments", headers=headers)
    assert resp.status_code in (401, 403)


def test_missing_org_id_works_in_dev(client):
    """In dev/test, missing organization_id should not cause a crash."""
    token = make_token(org_id="")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/departments", headers=headers)
    # Should not be 500 — either serves with default org or rejects cleanly
    assert resp.status_code != 500


def test_unknown_role_rejected(client):
    """Unrecognized role should be rejected from admin endpoints."""
    token = make_token(role="viewer")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/vendors", headers=headers)
    assert resp.status_code == 403
