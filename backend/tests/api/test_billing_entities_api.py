"""Billing entities API - list, search, get, create, update."""
import time

import pytest


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{time.time_ns()}"

class TestBillingEntitiesList:

    def test_requires_auth(self, client):
        r = client.get("/api/beta/finance/billing-entities")
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures("_db")
    def test_list_empty_ok(self, client, auth_headers):
        r = client.get("/api/beta/finance/billing-entities", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

class TestBillingEntitiesSearch:

    @pytest.mark.usefixtures("_db")
    def test_search_with_empty_query_lists_active(self, client, auth_headers):
        r = client.get("/api/beta/finance/billing-entities/search", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

class TestBillingEntitiesCrud:

    @pytest.mark.usefixtures("_db")
    def test_create_requires_name(self, client, auth_headers):
        r = client.post("/api/beta/finance/billing-entities", headers=auth_headers, json={"contact_name": "x"})
        assert r.status_code in (400, 422)

    @pytest.mark.usefixtures("_db")
    def test_create_and_get(self, client, auth_headers):
        name = _unique_name("Pytest Billing Co")
        r = client.post("/api/beta/finance/billing-entities", headers=auth_headers, json={"name": name, "contact_email": "billing@example.com", "payment_terms": "net_15"})
        assert r.status_code == 200
        created = r.json()
        be_id = created["id"]
        assert created["name"] == name
        r2 = client.get(f"/api/beta/finance/billing-entities/{be_id}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["name"] == name
        r3 = client.get("/api/beta/finance/billing-entities", params={"q": name[:12]}, headers=auth_headers)
        assert r3.status_code == 200
        assert any(x["id"] == be_id for x in r3.json())

    @pytest.mark.usefixtures("_db")
    def test_create_conflict_same_name(self, client, auth_headers):
        name = _unique_name("Duplicate BE")
        r1 = client.post("/api/beta/finance/billing-entities", headers=auth_headers, json={"name": name})
        assert r1.status_code == 200
        r2 = client.post("/api/beta/finance/billing-entities", headers=auth_headers, json={"name": name})
        assert r2.status_code == 409

    @pytest.mark.usefixtures("_db")
    def test_update_entity(self, client, auth_headers):
        name = _unique_name("Update BE")
        r = client.post("/api/beta/finance/billing-entities", headers=auth_headers, json={"name": name})
        assert r.status_code == 200
        be_id = r.json()["id"]
        r2 = client.put(f"/api/beta/finance/billing-entities/{be_id}", headers=auth_headers, json={"contact_name": "Jane Doe", "is_active": False})
        assert r2.status_code == 200
        body = r2.json()
        assert body.get("contact_name") == "Jane Doe"
        assert body.get("is_active") is False

    @pytest.mark.usefixtures("_db")
    def test_get_not_found(self, client, auth_headers):
        r = client.get("/api/beta/finance/billing-entities/019a0000-0000-7000-8000-000000000099", headers=auth_headers)
        assert r.status_code == 404

class TestBillingEntitiesContractorBlocked:

    @pytest.mark.usefixtures("_db")
    def test_contractor_cannot_list(self, client, contractor_auth_headers):
        r = client.get("/api/beta/finance/billing-entities", headers=contractor_auth_headers)
        assert r.status_code == 403
