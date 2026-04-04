"""E2E: Return accounting — verify sales report numbers, ledger balance,
and stock after single returns, partial returns, and multi-return scenarios.

Covers the specific fix: returns_total was previously hardcoded to 0.
"""

import pytest

from tests.e2e.helpers import create_product, create_withdrawal
from tests.helpers.auth import admin_headers


def _sales_report(client, headers):
    resp = client.get("/api/beta/reports/sales", headers=headers)
    assert resp.status_code == 200, f"Sales report failed: {resp.text}"
    return resp.json()


def _stock(client, headers, sku_id):
    resp = client.get(f"/api/beta/catalog/skus/{sku_id}", headers=headers)
    assert resp.status_code == 200
    return resp.json()["quantity"]


def _create_return(client, headers, withdrawal_id, product, quantity, reason="other"):
    resp = client.post(
        "/api/beta/operations/returns",
        json={
            "withdrawal_id": withdrawal_id,
            "items": [{"sku_id": product["id"], "sku": product["sku"], "name": product["name"], "quantity": quantity}],
            "reason": reason,
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"Return failed: {resp.text}"
    return resp.json()


@pytest.mark.timeout(60)
class TestReturnAccounting:
    """Accounting invariants specific to returns."""

    def test_sales_report_returns_total_is_populated(self, client, seed_dept_id):
        """returns_total should reflect the actual refund amount, not zero."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, price=20.0, cost=8.0, name="ACCT-RetTotal"
        )
        before = _sales_report(client, headers)
        ret_total_before = before["returns_total"]
        wd = create_withdrawal(client, headers, product, quantity=10)
        _create_return(client, headers, wd["id"], product, quantity=4)
        after = _sales_report(client, headers)
        return_refund = 4 * product["price"]
        assert after["returns_total"] >= ret_total_before + return_refund - 0.02
        assert after["returns_total"] > 0, "returns_total must not be hardcoded to 0"

    def test_gross_vs_net_revenue_after_return(self, client, seed_dept_id):
        """gross_revenue = net_revenue + returns_total."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, price=25.0, cost=10.0, name="ACCT-GrossNet"
        )
        wd = create_withdrawal(client, headers, product, quantity=8)
        _create_return(client, headers, wd["id"], product, quantity=3)
        report = _sales_report(client, headers)
        assert report["gross_revenue"] == pytest.approx(report["net_revenue"] + report["returns_total"], abs=0.02)

    def test_return_count_increments(self, client, seed_dept_id):
        """Each return should increment return_count."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, price=15.0, cost=6.0, name="ACCT-RetCount"
        )
        before = _sales_report(client, headers)
        count_before = before["return_count"]
        wd = create_withdrawal(client, headers, product, quantity=10)
        _create_return(client, headers, wd["id"], product, quantity=2)
        _create_return(client, headers, wd["id"], product, quantity=3)
        after = _sales_report(client, headers)
        assert after["return_count"] >= count_before + 2

    def test_multiple_partial_returns_same_withdrawal(self, client, seed_dept_id):
        """Two partial returns against the same sale should both be reflected correctly."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, price=30.0, cost=12.0, name="ACCT-MultiPartial"
        )
        wd = create_withdrawal(client, headers, product, quantity=10)
        assert _stock(client, headers, product["id"]) == 90
        _create_return(client, headers, wd["id"], product, quantity=3)
        assert _stock(client, headers, product["id"]) == 93
        _create_return(client, headers, wd["id"], product, quantity=4)
        assert _stock(client, headers, product["id"]) == 97
        _create_return(client, headers, wd["id"], product, quantity=3)
        assert _stock(client, headers, product["id"]) == 100
        resp = client.post(
            "/api/beta/operations/returns",
            json={
                "withdrawal_id": wd["id"],
                "items": [{"sku_id": product["id"], "sku": product["sku"], "name": product["name"], "quantity": 1}],
            },
            headers=headers,
        )
        assert resp.status_code in (400, 422)

    def test_profit_correct_after_return(self, client, seed_dept_id):
        """Gross profit = net_revenue - COGS (both reduced by the return)."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=100, price=50.0, cost=20.0, name="ACCT-Profit"
        )
        before = _sales_report(client, headers)
        rev_before = before["net_revenue"]
        cogs_before = before["total_cogs"]
        wd = create_withdrawal(client, headers, product, quantity=10)
        _create_return(client, headers, wd["id"], product, quantity=6)
        after = _sales_report(client, headers)
        net_sale_revenue = 4 * product["price"]
        net_sale_cogs = 4 * product["cost"]
        assert after["net_revenue"] == pytest.approx(rev_before + net_sale_revenue, abs=0.1)
        assert after["total_cogs"] == pytest.approx(cogs_before + net_sale_cogs, abs=0.1)
        assert after["gross_profit"] == pytest.approx(after["net_revenue"] - after["total_cogs"], abs=0.1)

    def test_stock_transaction_type_is_return(self, client, seed_dept_id):
        """Stock history should show a RETURN transaction after a return."""
        headers = admin_headers()
        product = create_product(
            client, headers, dept_id=seed_dept_id, quantity=50, price=10.0, cost=4.0, name="ACCT-StockTx"
        )
        wd = create_withdrawal(client, headers, product, quantity=5)
        _create_return(client, headers, wd["id"], product, quantity=2)
        resp = client.get(f"/api/beta/inventory/stock/{product['id']}/history", headers=headers)
        assert resp.status_code == 200
        history = resp.json().get("history", [])
        return_txns = [t for t in history if t.get("transaction_type") == "return"]
        assert len(return_txns) >= 1
        assert return_txns[0]["quantity_delta"] == 2
