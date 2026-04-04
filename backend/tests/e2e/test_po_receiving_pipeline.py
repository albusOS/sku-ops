"""E2E: PO receiving pipeline — create PO, mark delivery, receive items.

Verifies the full chain: POST purchase-order → delivery → receive →
stock increased → stock history → WS events.
"""

import pytest

from tests.e2e.helpers import create_po, create_product, receive_po
from tests.helpers.auth import admin_headers


@pytest.mark.timeout(30)
class TestPOReceivingPipeline:
    """Full PO receiving lifecycle through the live HTTP API."""

    def test_po_receive_increases_stock(self, client, ws_events, seed_dept_id):
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=10, cost=5.0, name="PO-Recv")
        po = create_po(client, headers, product, quantity=20, vendor_name="PO-E2E-Vendor")
        po_id = po["id"]
        assert po_id
        ws_events.clear()
        receive_po(client, headers, po_id)
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.status_code == 200
        updated_qty = resp.json()["quantity"]
        assert updated_qty > 10, f"Stock should have increased from 10, got {updated_qty}"
        ws_inv = ws_events.wait_for("inventory.updated", timeout=3)
        assert ws_inv is not None, "inventory.updated event not received after PO receive"

    def test_po_receive_records_stock_history(self, client, seed_dept_id):
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=0, cost=4.0, name="PO-History")
        po = create_po(client, headers, product, quantity=15, vendor_name="PO-History-Vendor")
        receive_po(client, headers, po["id"])
        resp = client.get(f"/api/beta/inventory/stock/{product['id']}/history", headers=headers)
        assert resp.status_code == 200
        history = resp.json()["history"]
        receiving_entries = [h for h in history if h["reference_type"] == "receiving"]
        assert len(receiving_entries) >= 1, "Should have at least one receiving stock entry"
        assert receiving_entries[0]["quantity_delta"] > 0

    def test_po_status_after_receive(self, client, seed_dept_id):
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=5, cost=3.0, name="PO-Status")
        po = create_po(client, headers, product, quantity=10, vendor_name="PO-Status-Vendor")
        receive_po(client, headers, po["id"])
        resp = client.get(f"/api/beta/purchasing/purchase-orders/{po['id']}", headers=headers)
        assert resp.status_code == 200
        po_detail = resp.json()
        assert po_detail["status"] in ("partial", "received"), (
            f"PO should be partial or received, got {po_detail['status']}"
        )

    def test_po_listed(self, client, seed_dept_id):
        """Created POs appear in GET /api/beta/purchasing/purchase-orders."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=5, cost=2.0, name="PO-List")
        po = create_po(client, headers, product, quantity=5, vendor_name="PO-List-Vendor")
        resp = client.get("/api/beta/purchasing/purchase-orders", headers=headers)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert po["id"] in ids
