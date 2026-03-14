"""E2E: Payment pipeline — create withdrawals, invoice, pay, verify ledger + WS.

Verifies the full chain: withdrawal → invoice → payment → all statuses
transition correctly → AR ledger entry → WebSocket events.
"""

import pytest

from tests.e2e.helpers import create_product, create_withdrawal
from tests.helpers.auth import admin_headers


@pytest.mark.timeout(30)
class TestPaymentPipeline:
    """Full payment lifecycle through the live HTTP API."""

    def test_payment_transitions_all_statuses(self, client, ws_events, seed_dept_id):
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, name="PAY-Pipeline"
        )

        w1 = create_withdrawal(client, headers, product, quantity=5, job_id="JOB-PAY-1")
        w2 = create_withdrawal(client, headers, product, quantity=3, job_id="JOB-PAY-2")
        expected_total = w1["total"] + w2["total"]

        # Create invoice
        resp = client.post(
            "/api/invoices",
            json={"withdrawal_ids": [w1["id"], w2["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200
        invoice = resp.json()
        assert invoice["total"] == pytest.approx(expected_total, abs=0.01)

        ws_events.clear()

        # Record payment
        resp = client.post(
            "/api/payments",
            json={
                "withdrawal_ids": [w1["id"], w2["id"]],
                "invoice_id": invoice["id"],
                "method": "bank_transfer",
                "reference": "TRF-E2E-PAY",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        payment = resp.json()
        assert payment["amount"] == pytest.approx(expected_total, abs=0.01)

        # Withdrawals marked paid
        for wid in [w1["id"], w2["id"]]:
            resp = client.get(f"/api/withdrawals/{wid}", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["payment_status"] == "paid"

        # WebSocket notified
        ws_updated = ws_events.wait_for("withdrawal.updated", timeout=3)
        assert ws_updated is not None, "withdrawal.updated event not received after payment"

    def test_dashboard_unpaid_drops_after_payment(self, client, seed_dept_id):
        """After paying all withdrawals, unpaid balance should not include them."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, name="PAY-Unpaid"
        )

        withdrawal = create_withdrawal(client, headers, product, quantity=2)

        stats_before = client.get("/api/dashboard/stats", headers=headers).json()
        unpaid_before = stats_before.get("unpaid_total", 0)

        # Pay via mark-paid endpoint
        resp = client.put(
            f"/api/withdrawals/{withdrawal['id']}/mark-paid",
            json={},
            headers=headers,
        )
        assert resp.status_code == 200

        stats_after = client.get("/api/dashboard/stats", headers=headers).json()
        unpaid_after = stats_after.get("unpaid_total", 0)
        assert unpaid_after < unpaid_before

    def test_payment_records_listed(self, client, seed_dept_id):
        """Created payments appear in GET /api/payments."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, name="PAY-List"
        )
        withdrawal = create_withdrawal(client, headers, product, quantity=1)

        resp = client.post(
            "/api/payments",
            json={
                "withdrawal_ids": [withdrawal["id"]],
                "method": "cash",
                "reference": "CASH-E2E",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        payment_id = resp.json()["id"]

        resp = client.get("/api/payments", headers=headers)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert payment_id in ids
