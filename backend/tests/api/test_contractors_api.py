"""Contractors API tests — list, search."""

import pytest


class TestContractorsList:
    """GET /api/beta/operations/contractors"""

    def test_requires_auth(self, client):
        r = client.get("/api/beta/operations/contractors")
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures("_db")
    def test_list_returns_contractors(self, client, auth_headers):
        """With seeded contractor, list returns at least one."""
        r = client.get("/api/beta/operations/contractors", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        contractor = next(
            (c for c in data if c.get("email") == "contractor@test.com"), None
        )
        assert contractor is not None
        assert contractor["name"] == "Contractor User"
        assert contractor["company"] == "ACME"

    @pytest.mark.usefixtures("_db")
    def test_search_filters_by_name(self, client, auth_headers):
        """search param filters by name, email, company, etc."""
        r = client.get(
            "/api/beta/operations/contractors",
            params={"search": "Contractor User"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any(c["name"] == "Contractor User" for c in data)

    @pytest.mark.usefixtures("_db")
    def test_search_filters_by_company(self, client, auth_headers):
        r = client.get(
            "/api/beta/operations/contractors",
            params={"search": "ACME"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any(c.get("company") == "ACME" for c in data)

    @pytest.mark.usefixtures("_db")
    def test_search_empty_when_no_match(self, client, auth_headers):
        r = client.get(
            "/api/beta/operations/contractors",
            params={"search": "xyznonexistent123"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data == []
