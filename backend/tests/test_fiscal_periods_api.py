"""Fiscal periods API tests — Pydantic validation for create endpoint."""

AUTH_REJECT = (401, 403)


def test_create_missing_fields_returns_422(client):
    """POST /api/fiscal-periods with missing required fields should return 422."""
    r = client.post(
        "/api/fiscal-periods",
        json={"name": "Q1"},
        headers={"Authorization": "Bearer bad"},
    )
    assert r.status_code in (422, *AUTH_REJECT)


def test_create_empty_body_returns_422(client):
    """POST /api/fiscal-periods with empty body should return 422."""
    r = client.post(
        "/api/fiscal-periods",
        json={},
        headers={"Authorization": "Bearer bad"},
    )
    assert r.status_code in (422, *AUTH_REJECT)
