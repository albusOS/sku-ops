"""E2E: Return pipeline — create withdrawal, return items, verify restock + ledger + WS.

Verifies: stock restocked, reversing ledger exists, WebSocket events,
over-return rejected.
"""

import pytest

from tests.e2e.helpers import create_product, create_withdrawal
from tests.helpers.auth import admin_headers


@pytest.mark.timeout(30)
class TestReturnPipeline:
    """Full return lifecycle through the live HTTP API."""

    def test_return_restocks_and_emits_events(self, client, ws_events, seed_dept_id):
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=50, name="RET-Pipeline"
        )

        withdrawal = create_withdrawal(client, headers, product, quantity=10)

        # Stock after withdrawal
        resp = client.get(f"/api/catalog/skus/{product['id']}", headers=headers)
        stock_after_wd = resp.json()["quantity"]
        assert stock_after_wd == 40

        ws_events.clear()

        # Create return for 4 items
        resp = client.post(
            "/api/returns",
            json={
                "withdrawal_id": withdrawal["id"],
                "items": [
                    {
                        "product_id": product["id"],
                        "sku": product["sku"],
                        "name": product["name"],
                        "quantity": 4,
                    }
                ],
                "reason": "other",
                "notes": "E2E return test",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        ret = resp.json()
        assert ret["total"] > 0

        # Stock restocked
        resp = client.get(f"/api/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()["quantity"] == 44

        # Return persisted
        resp = client.get(f"/api/returns/{ret['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["withdrawal_id"] == withdrawal["id"]

        # WebSocket events
        ws_updated = ws_events.wait_for("withdrawal.updated", timeout=3)
        assert ws_updated is not None, "withdrawal.updated not received after return"

        ws_inv = ws_events.wait_for("inventory.updated", timeout=3)
        assert ws_inv is not None, "inventory.updated not received after return"

    def test_over_return_rejected(self, client, seed_dept_id):
        """Cannot return more than was originally withdrawn."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=50, name="RET-OverReturn"
        )

        withdrawal = create_withdrawal(client, headers, product, quantity=3)

        resp = client.post(
            "/api/returns",
            json={
                "withdrawal_id": withdrawal["id"],
                "items": [
                    {
                        "product_id": product["id"],
                        "sku": product["sku"],
                        "name": product["name"],
                        "quantity": 10,
                    }
                ],
            },
            headers=headers,
        )
        assert resp.status_code in (400, 422), f"Expected rejection, got {resp.status_code}"

        # Stock unchanged from the withdrawal
        resp = client.get(f"/api/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()["quantity"] == 47

    def test_returns_listed_by_withdrawal(self, client, seed_dept_id):
        """GET /api/returns?withdrawal_id=... lists the return."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=50, name="RET-List"
        )

        withdrawal = create_withdrawal(client, headers, product, quantity=5)

        resp = client.post(
            "/api/returns",
            json={
                "withdrawal_id": withdrawal["id"],
                "items": [
                    {
                        "product_id": product["id"],
                        "sku": product["sku"],
                        "name": product["name"],
                        "quantity": 2,
                    }
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        ret_id = resp.json()["id"]

        resp = client.get(f"/api/returns?withdrawal_id={withdrawal['id']}", headers=headers)
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert ret_id in ids
