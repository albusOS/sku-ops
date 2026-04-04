"""E2E: Cycle count pipeline — open, count, commit, verify adjustments.

Verifies: open creates snapshot, counted items get variance, commit applies
adjustments, stock matches, WS events emitted, double-commit rejected.
"""
import pytest

from tests.e2e.helpers import (
    commit_cycle_count,
    create_product,
    open_cycle_count,
    update_cycle_count_item,
)
from tests.helpers.auth import admin_headers


@pytest.mark.timeout(30)
class TestCycleCountPipeline:
    """Full cycle count lifecycle through the live HTTP API."""

    def test_cycle_count_adjusts_stock(self, client, ws_events, seed_dept_id):
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="CC-Adjust")
        count = open_cycle_count(client, headers)
        count_id = count["id"]
        resp = client.get(f"/api/beta/inventory/cycle-counts/{count_id}", headers=headers)
        assert resp.status_code == 200
        detail = resp.json()
        items = detail["items"]
        target_item = next((i for i in items if i["sku_id"] == product["id"]), None)
        assert target_item is not None, "Product should appear in cycle count"
        assert target_item["snapshot_qty"] == 50
        ws_events.clear()
        update_cycle_count_item(client, headers, count_id, target_item["id"], counted_qty=45)
        result = commit_cycle_count(client, headers, count_id)
        assert result["status"] == "committed"
        assert result["items_adjusted"] >= 1
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()["quantity"] == 45
        ws_inv = ws_events.wait_for("inventory.updated", timeout=3)
        assert ws_inv is not None, "inventory.updated should fire after cycle count commit"

    def test_cycle_count_increase(self, client, seed_dept_id):
        """Cycle count can increase stock (found more than expected)."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=20, name="CC-Increase")
        count = open_cycle_count(client, headers)
        detail = client.get(f"/api/beta/inventory/cycle-counts/{count['id']}", headers=headers).json()
        target = next(i for i in detail["items"] if i["sku_id"] == product["id"])
        update_cycle_count_item(client, headers, count["id"], target["id"], counted_qty=25)
        commit_cycle_count(client, headers, count["id"])
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()["quantity"] == 25

    def test_double_commit_rejected(self, client, seed_dept_id):
        """Cannot commit a cycle count twice."""
        headers = admin_headers()
        create_product(client, headers, dept_id=seed_dept_id, quantity=10, name="CC-Double")
        count = open_cycle_count(client, headers)
        commit_cycle_count(client, headers, count["id"])
        resp = client.post(f"/api/beta/inventory/cycle-counts/{count['id']}/commit", json={}, headers=headers)
        assert resp.status_code in (400, 422), "Double commit should be rejected"

    def test_cycle_count_listed(self, client, seed_dept_id):
        """Cycle counts appear in the listing."""
        headers = admin_headers()
        create_product(client, headers, dept_id=seed_dept_id, quantity=10, name="CC-List")
        count = open_cycle_count(client, headers)
        resp = client.get("/api/beta/inventory/cycle-counts", headers=headers)
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert count["id"] in ids

    def test_stock_history_after_commit(self, client, seed_dept_id):
        """Stock history should show adjustment entries after commit."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=30, name="CC-History")
        count = open_cycle_count(client, headers)
        detail = client.get(f"/api/beta/inventory/cycle-counts/{count['id']}", headers=headers).json()
        target = next(i for i in detail["items"] if i["sku_id"] == product["id"])
        update_cycle_count_item(client, headers, count["id"], target["id"], counted_qty=28)
        commit_cycle_count(client, headers, count["id"])
        resp = client.get(f"/api/beta/inventory/stock/{product['id']}/history", headers=headers)
        assert resp.status_code == 200
        history = resp.json()["history"]
        adj_entries = [h for h in history if h["reference_type"] == "adjustment"]
        assert len(adj_entries) >= 1
        assert adj_entries[0]["quantity_delta"] == -2
