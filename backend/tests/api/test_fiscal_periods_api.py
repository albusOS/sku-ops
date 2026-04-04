"""Fiscal periods API - list, create, close."""

import time

import pytest


def _period_body():
    ts = time.time_ns()
    return {"name": f"pytest-fp-{ts}", "start_date": "2026-01-01T00:00:00Z", "end_date": "2026-01-31T23:59:59Z"}


class TestFiscalPeriods:
    def test_requires_auth(self, client):
        r = client.get("/api/beta/finance/fiscal-periods")
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures("_db")
    def test_list_ok(self, client, auth_headers):
        r = client.get("/api/beta/finance/fiscal-periods", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.usefixtures("_db")
    def test_create_list_close(self, client, auth_headers):
        r = client.post("/api/beta/finance/fiscal-periods", headers=auth_headers, json=_period_body())
        assert r.status_code == 200
        created = r.json()
        pid = created["id"]
        assert created.get("status") == "open"
        r2 = client.post(f"/api/beta/finance/fiscal-periods/{pid}/close", headers=auth_headers)
        assert r2.status_code == 200
        closed = r2.json()
        assert closed.get("status") == "closed"
        r3 = client.post(f"/api/beta/finance/fiscal-periods/{pid}/close", headers=auth_headers)
        assert r3.status_code == 400
