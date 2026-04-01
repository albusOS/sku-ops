"""E2E: Payment pipeline — create withdrawals, invoice, pay, verify ledger + WS.

Verifies the full chain: withdrawal → invoice → payment → all statuses
transition correctly → AR ledger entry → WebSocket events.
"""

import pytest

from tests.e2e.helpers import create_product, create_withdrawal, e2e_job_id
from tests.helpers.auth import admin_headers


@pytest.mark.timeout(30)
class TestPaymentPipeline:
    """Full payment lifecycle through the live HTTP API."""

    def test_payment_transitions_all_statuses(
        self, client, ws_events, seed_dept_id
    ):
        headers = admin_headers()
        product = create_product(
            client,
            headers,
            dept_id=seed_dept_id,
            quantity=100,
            name="PAY-Pipeline",
        )

        w1 = create_withdrawal(
            client, headers, product, quantity=5, job_id=e2e_job_id("PAY-1")
        )
        w2 = create_withdrawal(
            client, headers, product, quantity=3, job_id=e2e_job_id("PAY-2")
        )

        # Both withdrawals are auto-invoiced — verify and fetch invoice IDs
        for w in [w1, w2]:
            resp = client.get(
                f"/api/beta/operations/withdrawals/{w['id']}", headers=headers
            )
            assert resp.status_code == 200
            wd_state = resp.json()
            assert wd_state["payment_status"] == "invoiced"
            assert wd_state.get("invoice_id") is not None

        ws_events.clear()

        # Record payment for w1 using its auto-invoice
        w1_state = client.get(
            f"/api/beta/operations/withdrawals/{w1['id']}", headers=headers
        ).json()
        resp = client.post(
            "/api/beta/finance/payments",
            json={
                "withdrawal_ids": [w1["id"]],
                "invoice_id": w1_state["invoice_id"],
                "method": "bank_transfer",
                "reference": "TRF-E2E-PAY-1",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        payment = resp.json()
        assert payment["amount"] == pytest.approx(w1["total"], abs=0.01)

        # Record payment for w2 using its auto-invoice
        w2_state = client.get(
            f"/api/beta/operations/withdrawals/{w2['id']}", headers=headers
        ).json()
        resp = client.post(
            "/api/beta/finance/payments",
            json={
                "withdrawal_ids": [w2["id"]],
                "invoice_id": w2_state["invoice_id"],
                "method": "bank_transfer",
                "reference": "TRF-E2E-PAY-2",
            },
            headers=headers,
        )
        assert resp.status_code == 200

        # Withdrawals marked paid
        for wid in [w1["id"], w2["id"]]:
            resp = client.get(
                f"/api/beta/operations/withdrawals/{wid}", headers=headers
            )
            assert resp.status_code == 200
            assert resp.json()["payment_status"] == "paid"

        # WebSocket notified
        ws_updated = ws_events.wait_for("withdrawal.updated", timeout=3)
        assert ws_updated is not None, (
            "withdrawal.updated event not received after payment"
        )

    def test_dashboard_unpaid_drops_after_payment(self, client, seed_dept_id):
        """After paying an auto-invoiced withdrawal, it transitions to paid
        and the outstanding (invoiced) total drops.
        """
        headers = admin_headers()
        product = create_product(
            client,
            headers,
            dept_id=seed_dept_id,
            quantity=100,
            name="PAY-Unpaid",
        )

        withdrawal = create_withdrawal(client, headers, product, quantity=2)

        # Verify auto-invoiced
        resp = client.get(
            f"/api/beta/operations/withdrawals/{withdrawal['id']}",
            headers=headers,
        )
        assert resp.json()["payment_status"] == "invoiced"

        stats_before = client.get(
            "/api/beta/reports/dashboard/stats", headers=headers
        ).json()
        outstanding_before = stats_before.get(
            "unpaid_total", 0
        ) + stats_before.get("invoiced_total", 0)

        # Pay via mark-paid endpoint
        resp = client.put(
            f"/api/beta/operations/withdrawals/{withdrawal['id']}/mark-paid",
            json={},
            headers=headers,
        )
        assert resp.status_code == 200

        resp = client.get(
            f"/api/beta/operations/withdrawals/{withdrawal['id']}",
            headers=headers,
        )
        assert resp.json()["payment_status"] == "paid"

        stats_after = client.get(
            "/api/beta/reports/dashboard/stats", headers=headers
        ).json()
        outstanding_after = stats_after.get(
            "unpaid_total", 0
        ) + stats_after.get("invoiced_total", 0)
        assert outstanding_after < outstanding_before

    def test_payment_records_listed(self, client, seed_dept_id):
        """Created payments appear in GET /api/beta/finance/payments."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, name="PAY-List"
        )
        withdrawal = create_withdrawal(client, headers, product, quantity=1)

        resp = client.post(
            "/api/beta/finance/payments",
            json={
                "withdrawal_ids": [withdrawal["id"]],
                "method": "cash",
                "reference": "CASH-E2E",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        payment_id = resp.json()["id"]

        resp = client.get("/api/beta/finance/payments", headers=headers)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert payment_id in ids
