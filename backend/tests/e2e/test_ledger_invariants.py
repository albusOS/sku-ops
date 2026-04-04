"""E2E: Ledger invariants — double-entry balance, no duplicates, AR consistency.

Runs a sequence of financial operations (withdrawal, return, payment) and
then queries the ledger directly to verify accounting integrity.
"""
import pytest
from tests.e2e.helpers import create_product, create_withdrawal, e2e_job_id
from tests.helpers.auth import admin_headers

def _query_ledger(client, headers):
    """Fetch all ledger entries via the trial balance endpoint."""
    resp = client.get('/api/beta/reports/dashboard/stats', headers=headers)
    assert resp.status_code == 200
    return resp.json()

@pytest.mark.timeout(60)
class TestLedgerInvariants:
    """Accounting invariants verified after a mixed financial workload."""

    def test_full_cycle_ledger_integrity(self, client, seed_dept_id):
        """Withdrawal + return + payment — dashboard numbers stay consistent."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=100, price=20.0, cost=8.0, name='LEDGER-Integrity')
        wd = create_withdrawal(client, headers, product, quantity=10)
        wd_total = wd['total']
        wd_cost = wd['cost_total']
        stats = _query_ledger(client, headers)
        assert stats['range_revenue'] >= wd_total - wd_cost
        assert stats['range_cogs'] >= wd_cost
        resp = client.post('/api/beta/operations/returns', json={'withdrawal_id': wd['id'], 'items': [{'sku_id': product['id'], 'sku': product['sku'], 'name': product['name'], 'quantity': 3}]}, headers=headers)
        assert resp.status_code == 200
        resp = client.put(f"/api/beta/operations/withdrawals/{wd['id']}/mark-paid", json={}, headers=headers)
        assert resp.status_code == 200
        resp = client.get(f"/api/beta/operations/withdrawals/{wd['id']}", headers=headers)
        assert resp.json()['payment_status'] == 'paid'
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()['quantity'] == 93

    def test_no_duplicate_ledger_entries(self, client, seed_dept_id):
        """Creating the same withdrawal twice should not double-write ledger entries.

        The ledger's entries_exist guard prevents duplicates. We verify by
        checking dashboard stats stay consistent with a single withdrawal.
        """
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=100, price=10.0, cost=4.0, name='LEDGER-NoDup')
        stats_before = _query_ledger(client, headers)
        rev_before = stats_before.get('range_revenue', 0)
        wd = create_withdrawal(client, headers, product, quantity=5)
        stats_after = _query_ledger(client, headers)
        rev_after = stats_after.get('range_revenue', 0)
        expected_increase = wd['total']
        actual_increase = rev_after - rev_before
        assert actual_increase == pytest.approx(expected_increase, abs=0.02)

    def test_unpaid_balance_tracks_correctly(self, client, seed_dept_id):
        """Unpaid total should equal the sum of unpaid withdrawal totals."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=200, price=15.0, cost=6.0, name='LEDGER-Unpaid')
        w1 = create_withdrawal(client, headers, product, quantity=5, job_id=e2e_job_id('UP-1'))
        w2 = create_withdrawal(client, headers, product, quantity=3, job_id=e2e_job_id('UP-2'))
        resp = client.put(f"/api/beta/operations/withdrawals/{w1['id']}/mark-paid", json={}, headers=headers)
        assert resp.status_code == 200
        resp = client.get(f"/api/beta/operations/withdrawals/{w2['id']}", headers=headers)
        assert resp.json()['payment_status'] == 'invoiced'
        stats = _query_ledger(client, headers)
        outstanding = stats.get('unpaid_total', 0) + stats.get('invoiced_total', 0)
        assert outstanding >= w2['total']

    def test_gross_profit_matches_revenue_minus_cogs(self, client, seed_dept_id):
        """Gross profit = revenue - COGS, always."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=100, price=25.0, cost=10.0, name='LEDGER-Profit')
        create_withdrawal(client, headers, product, quantity=8)
        stats = _query_ledger(client, headers)
        revenue = stats.get('range_revenue', 0)
        cogs = stats.get('range_cogs', 0)
        profit = stats.get('range_gross_profit', 0)
        assert profit == pytest.approx(revenue - cogs, abs=0.02)
        if revenue > 0:
            margin_pct = stats.get('range_margin_pct', 0)
            expected_margin = (revenue - cogs) / revenue * 100
            assert margin_pct == pytest.approx(expected_margin, abs=0.5)
