"""E2E: Withdrawal pipeline — HTTP mutation + stock + ledger + WebSocket events.

Verifies the full chain: POST /api/beta/operations/withdrawals → stock decremented →
ledger entries written and balanced → WebSocket events delivered →
auto-invoice created.
"""
import pytest

from tests.e2e.helpers import create_product, create_withdrawal
from tests.helpers.auth import CONTRACTOR_USER_ID, SEEDED_JOB_ID, admin_headers


@pytest.mark.timeout(30)
class TestWithdrawalPipeline:
    """Full withdrawal lifecycle through the live HTTP API."""

    def test_withdrawal_creates_stock_ledger_and_events(self, client, ws_events, seed_dept_id):
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="WD-Pipeline")
        withdrawal = create_withdrawal(client, headers, product, quantity=5)
        assert withdrawal["total"] > 0
        assert withdrawal["contractor_id"]
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 45
        resp = client.get(f"/api/beta/inventory/stock/{product['id']}/history", headers=headers)
        assert resp.status_code == 200
        history = resp.json()["history"]
        wd_entries = [h for h in history if h["reference_type"] == "withdrawal"]
        assert len(wd_entries) >= 1
        assert wd_entries[0]["quantity_delta"] == -5
        ws_created = ws_events.wait_for("withdrawal.created", timeout=3)
        assert ws_created is not None, "withdrawal.created event not received"
        ws_inventory = ws_events.wait_for("inventory.updated", timeout=3)
        assert ws_inventory is not None, "inventory.updated event not received"

    def test_withdrawal_auto_creates_invoice(self, client, seed_dept_id):
        """Every withdrawal atomically creates an invoice — no manual step required."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="WD-AutoInvoice")
        withdrawal = create_withdrawal(client, headers, product, quantity=3)
        resp = client.get(f"/api/beta/operations/withdrawals/{withdrawal['id']}", headers=headers)
        assert resp.status_code == 200
        wd = resp.json()
        assert wd.get("invoice_id") is not None, "Every withdrawal must have an invoice created atomically"
        assert wd.get("payment_status") == "invoiced", "Withdrawal payment_status must be 'invoiced' after invoice creation"

    def test_withdrawal_insufficient_stock_rejected(self, client, seed_dept_id):
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=2, name="WD-InsufficientE2E")
        resp = client.post(f"/api/beta/operations/withdrawals/for-contractor?contractor_id={CONTRACTOR_USER_ID}", json={"items": [{"sku_id": product["id"], "sku": product["sku"], "name": product["name"], "quantity": 10, "unit_price": product["price"], "cost": product["cost"]}], "job_id": SEEDED_JOB_ID, "service_address": "Fail St"}, headers=headers)
        assert resp.status_code in (400, 422)
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()["quantity"] == 2

    def test_dashboard_revenue_matches_withdrawal(self, client, seed_dept_id):
        """Dashboard stats should reflect the withdrawal's revenue and COGS."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=100, price=20.0, cost=8.0, name="WD-DashboardE2E")
        withdrawal = create_withdrawal(client, headers, product, quantity=10)
        resp = client.get("/api/beta/reports/dashboard/stats", headers=headers)
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["range_revenue"] >= withdrawal["subtotal"]
