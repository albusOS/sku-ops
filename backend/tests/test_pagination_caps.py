"""Pagination cap tests — verify all list endpoints reject unbounded limits."""
import pytest

AUTH_REJECT = (401, 403)

PAGINATION_ENDPOINTS = [
    ("GET", "/api/products", {"limit": 999}, 422),
    ("GET", "/api/stock/fake-id/history", {"limit": 999}, 422),
    ("GET", "/api/audit-log", {"limit": 999}, 422),
    ("GET", "/api/dashboard/transactions", {"limit": 999}, 422),
]


@pytest.mark.parametrize(("method", "path", "params", "expected"), PAGINATION_ENDPOINTS)
def test_pagination_cap_rejects_over_limit(client, method, path, params, expected):
    """Endpoints must reject limit values above their configured maximum."""
    r = getattr(client, method.lower())(path, params=params)
    assert r.status_code in (expected, *AUTH_REJECT), (
        f"{method} {path} returned {r.status_code}, expected {expected} or auth reject"
    )


NEGATIVE_OFFSET_ENDPOINTS = [
    ("GET", "/api/products", {"offset": -1}),
    ("GET", "/api/audit-log", {"offset": -1}),
    ("GET", "/api/dashboard/transactions", {"offset": -1}),
]


@pytest.mark.parametrize(("method", "path", "params"), NEGATIVE_OFFSET_ENDPOINTS)
def test_negative_offset_rejected(client, method, path, params):
    """Negative offsets should be rejected."""
    r = getattr(client, method.lower())(path, params=params)
    assert r.status_code in (422, *AUTH_REJECT)
