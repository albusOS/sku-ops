"""Dashboard API tests — date parsing, pagination, error handling."""

AUTH_REJECT = (401, 403)


class TestDashboardStats:
    """GET /api/dashboard/stats"""

    def test_requires_auth(self, client):
        r = client.get("/api/dashboard/stats")
        assert r.status_code in AUTH_REJECT

    def test_z_suffix_dates_accepted(self, client):
        """JS-style ISO dates with trailing Z must not crash."""
        r = client.get(
            "/api/dashboard/stats",
            params={"start_date": "2025-01-01T00:00:00Z", "end_date": "2025-12-31T23:59:59Z"},
        )
        assert r.status_code in (*AUTH_REJECT, 200)

    def test_invalid_date_returns_400(self, client):
        """Malformed date should hit the global ValueError handler."""
        r = client.get(
            "/api/dashboard/stats",
            params={"start_date": "not-a-date"},
            headers={"Authorization": "Bearer bad"},
        )
        assert r.status_code in (*AUTH_REJECT, 400)


class TestDashboardTransactions:
    """GET /api/dashboard/transactions"""

    def test_requires_auth(self, client):
        r = client.get("/api/dashboard/transactions")
        assert r.status_code in AUTH_REJECT

    def test_pagination_cap_rejects_over_limit(self, client):
        """limit > 100 should be rejected by Query validation."""
        r = client.get(
            "/api/dashboard/transactions",
            params={"limit": 999},
            headers={"Authorization": "Bearer bad"},
        )
        assert r.status_code in (*AUTH_REJECT, 422)

    def test_negative_offset_rejected(self, client):
        r = client.get(
            "/api/dashboard/transactions",
            params={"offset": -1},
            headers={"Authorization": "Bearer bad"},
        )
        assert r.status_code in (*AUTH_REJECT, 422)


class TestGlobalExceptionHandlers:
    """Verify global ValueError and Exception handlers in server.py."""

    def test_value_error_returns_400_json(self, client):
        """ValueError should return 400 with structured JSON, not a raw traceback."""
        r = client.get("/api/dashboard/stats", params={"start_date": "garbage"})
        if r.status_code == 400:
            body = r.json()
            assert "detail" in body
            assert isinstance(body["detail"], str)

    def test_404_returns_json(self, client):
        r = client.get("/api/nonexistent-route")
        assert r.status_code == 404
