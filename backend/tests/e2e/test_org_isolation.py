"""E2E: Multi-org data isolation — Org A data is invisible to Org B.

Seeds a second organization and user, then verifies that products and
withdrawals created by Org A are not visible to Org B, and vice versa.
"""

import pytest

from tests.e2e.helpers import create_product, create_withdrawal
from tests.helpers.auth import admin_headers, make_token

ORG_B_ID = "0195f2c0-89aa-7d6d-bb34-7f3b3f69c0bb"
ORG_B_USER = "0195f2c0-89ac-7f42-8b11-0000000000bb"


@pytest.fixture(scope="session")
def org_b_headers(app_client):
    """Seed a second org and user, return auth headers scoped to Org B."""

    async def _seed():
        from shared.infrastructure.db import sql_execute

        cursor = await sql_execute(
            "SELECT id FROM organizations WHERE id = $1", (ORG_B_ID,)
        )
        if not (cursor.rows[0] if cursor.rows else None):
            await sql_execute(
                "INSERT INTO organizations (id, name, slug, created_at) VALUES ($1, $2, $3, NOW())",
                (ORG_B_ID, "Org B", "org-b-test"),
            )
        cursor = await sql_execute(
            "SELECT id FROM users WHERE id = $1", (ORG_B_USER,)
        )
        if not (cursor.rows[0] if cursor.rows else None):
            await sql_execute(
                "INSERT INTO users (id, email, password, name, role, is_active, organization_id, created_at)"
                " VALUES ($1, $2, $3, $4, $5, TRUE, $6, NOW())",
                (
                    ORG_B_USER,
                    "orgb@test.com",
                    "unused",
                    "Org B Admin",
                    "admin",
                    ORG_B_ID,
                ),
            )

    app_client.portal.call(_seed)

    token = make_token(
        user_id=ORG_B_USER, org_id=ORG_B_ID, role="admin", name="Org B Admin"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def org_b_dept_id(app_client, org_b_headers):
    """Seed a department in Org B."""
    resp = app_client.get(
        "/api/beta/catalog/departments", headers=org_b_headers
    )
    if resp.status_code == 200:
        for dept in resp.json():
            if dept.get("code") == "ORB":
                return dept["id"]

    resp = app_client.post(
        "/api/beta/catalog/departments",
        json={
            "name": "Org B Dept",
            "code": "ORB",
            "description": "Org B department",
        },
        headers=org_b_headers,
    )
    assert resp.status_code == 200, f"Org B dept seed failed: {resp.text}"
    return resp.json()["id"]


@pytest.mark.timeout(30)
class TestOrgIsolation:
    """Verify that data from one org is invisible to another."""

    def test_org_a_products_invisible_to_org_b(
        self, client, seed_dept_id, org_b_headers, org_b_dept_id
    ):
        headers_a = admin_headers()
        product_a = create_product(
            client,
            headers_a,
            dept_id=seed_dept_id,
            quantity=10,
            name="OrgA-Only",
        )

        resp = client.get("/api/beta/catalog/skus", headers=org_b_headers)
        assert resp.status_code == 200
        org_b_sku_ids = [p["id"] for p in resp.json()]
        assert product_a["id"] not in org_b_sku_ids, (
            "Org A's product should not be visible to Org B"
        )

    def test_org_b_products_invisible_to_org_a(
        self, client, seed_dept_id, org_b_headers, org_b_dept_id
    ):
        headers_a = admin_headers()
        product_b = create_product(
            client,
            org_b_headers,
            dept_id=org_b_dept_id,
            quantity=10,
            name="OrgB-Only",
        )

        resp = client.get("/api/beta/catalog/skus", headers=headers_a)
        assert resp.status_code == 200
        org_a_sku_ids = [p["id"] for p in resp.json()]
        assert product_b["id"] not in org_a_sku_ids, (
            "Org B's product should not be visible to Org A"
        )

    def test_org_a_withdrawals_invisible_to_org_b(
        self, client, seed_dept_id, org_b_headers
    ):
        headers_a = admin_headers()
        product = create_product(
            client,
            headers_a,
            dept_id=seed_dept_id,
            quantity=50,
            name="OrgA-WD-Iso",
        )
        wd = create_withdrawal(client, headers_a, product, quantity=5)

        resp = client.get(
            "/api/beta/operations/withdrawals", headers=org_b_headers
        )
        assert resp.status_code == 200
        org_b_wd_ids = [w["id"] for w in resp.json()]
        assert wd["id"] not in org_b_wd_ids, (
            "Org A's withdrawal should not be visible to Org B"
        )

    def test_ws_org_isolation(self, client, seed_dept_id, org_b_headers):
        """WS events for Org A should NOT arrive on Org B's connection."""
        from tests.e2e.conftest import WSEventCollector
        from tests.helpers.auth import make_token

        org_b_token = make_token(
            user_id=ORG_B_USER,
            org_id=ORG_B_ID,
            role="admin",
            name="Org B Admin",
        )
        collector_b = WSEventCollector()
        collector_b.start(client, token=org_b_token)

        try:
            headers_a = admin_headers()
            product = create_product(
                client,
                headers_a,
                dept_id=seed_dept_id,
                quantity=50,
                name="WS-OrgIso",
            )
            create_withdrawal(client, headers_a, product, quantity=3)

            import time

            time.sleep(1)
            wd_events = collector_b.all_of_type("withdrawal.created")
            assert len(wd_events) == 0, (
                "Org B should not receive Org A's withdrawal.created events"
            )
        finally:
            collector_b.close()
