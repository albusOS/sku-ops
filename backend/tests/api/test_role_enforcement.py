"""Role enforcement — verify admin-only endpoints reject contractors.

Contractors should be able to access CurrentUserDep endpoints (material
requests, withdrawals list, products read, etc.) but must be rejected
from AdminDep endpoints with 403.
"""

import pytest

from tests.helpers.auth import (
    SEEDED_JOB_ID,
    admin_headers,
    contractor_headers,
    expired_token,
    make_token,
)

ADMIN_ONLY_ENDPOINTS = [
    ("GET", "/api/beta/reports/sales"),
    ("GET", "/api/beta/reports/inventory"),
    ("GET", "/api/beta/shared/audit-log"),
    ("POST", "/api/beta/catalog/departments", {"name": "Test", "code": "TST"}),
    ("GET", "/api/beta/catalog/vendors"),
    ("POST", "/api/beta/catalog/vendors", {"name": "Test Vendor"}),
    ("GET", "/api/beta/finance/invoices"),
    ("GET", "/api/beta/operations/contractors"),
    ("GET", "/api/beta/jobs"),
    ("POST", "/api/beta/jobs", {"code": "ROLE-TEST-JOB", "name": "role test"}),
    ("PUT", f"/api/beta/jobs/{SEEDED_JOB_ID}", {"name": "Role test name"}),
    ("GET", "/api/beta/finance/billing-entities"),
    ("GET", "/api/beta/shared/addresses"),
    ("GET", "/api/beta/documents"),
]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [(m, p, b if len(t) > 2 else {}) for t in ADMIN_ONLY_ENDPOINTS for m, p, *b in [t]],
    ids=[f"{m} {p}" for m, p, *_ in ADMIN_ONLY_ENDPOINTS],
)
def test_contractor_rejected_from_admin_endpoint(client, method, path, body):
    """Contractors must receive 403 from admin-only endpoints."""
    resp = client.request(method, path, headers=contractor_headers(), json=body)
    assert resp.status_code == 403, f"{method} {path} returned {resp.status_code} for contractor — expected 403"


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


CONTRACTOR_ACCESSIBLE_ENDPOINTS = [
    ("GET", "/api/beta/catalog/departments"),
    ("GET", "/api/beta/operations/material-requests"),
    ("GET", "/api/beta/operations/withdrawals"),
    ("GET", "/api/beta/catalog/skus"),
    ("GET", "/api/beta/jobs/search"),
    ("GET", f"/api/beta/jobs/{SEEDED_JOB_ID}"),
    ("GET", "/api/beta/shared/addresses/search"),
]


@pytest.mark.parametrize(
    ("method", "path"), CONTRACTOR_ACCESSIBLE_ENDPOINTS, ids=[f"{m} {p}" for m, p in CONTRACTOR_ACCESSIBLE_ENDPOINTS]
)
def test_contractor_can_access_shared_endpoints(client, method, path):
    """Contractors must be able to access CurrentUserDep endpoints."""
    resp = client.request(method, path, headers=contractor_headers())
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for contractor — expected access granted"
    )


def test_expired_token_rejected(client):
    """Expired JWT must return 401, not 500."""
    headers = {"Authorization": f"Bearer {expired_token()}"}
    resp = client.get("/api/beta/catalog/departments", headers=headers)
    assert resp.status_code == 401
    assert "expired" in resp.json().get("detail", "").lower()


def test_garbage_token_rejected(client):
    """Malformed token must return 401."""
    headers = {"Authorization": "Bearer not-a-real-token"}
    resp = client.get("/api/beta/catalog/departments", headers=headers)
    assert resp.status_code in (401, 403)


def test_missing_org_id_works_in_dev(client):
    """In dev/test, missing organization_id should not cause a crash."""
    token = make_token(org_id="")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/beta/catalog/departments", headers=headers)
    assert resp.status_code != 500


def test_unknown_role_rejected(client):
    """Unrecognized role should be rejected from admin endpoints."""
    token = make_token(role="viewer")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/beta/catalog/vendors", headers=headers)
    assert resp.status_code == 403
