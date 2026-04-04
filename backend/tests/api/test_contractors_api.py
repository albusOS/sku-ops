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
        contractor = next((c for c in data if c.get("email") == "sarah@summitpm.com"), None)
        assert contractor is not None
        assert contractor["name"] == "Sarah Okafor"
        assert contractor["company"] == "Summit Property Group"

    @pytest.mark.usefixtures("_db")
    def test_search_filters_by_name(self, client, auth_headers):
        """search param filters by name, email, company, etc."""
        r = client.get(
            "/api/beta/operations/contractors",
            params={"search": "Sarah Okafor"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any(c["name"] == "Sarah Okafor" for c in data)

    @pytest.mark.usefixtures("_db")
    def test_search_filters_by_company(self, client, auth_headers):
        r = client.get(
            "/api/beta/operations/contractors",
            params={"search": "Summit"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any(c.get("company") == "Summit Property Group" for c in data)

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
