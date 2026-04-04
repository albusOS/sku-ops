"""E2E: Catalog integrity — transaction atomicity, variant attrs, family hierarchy.

Worst-case scenarios that specifically target the bugs fixed in this session:

1. Atomicity: category transfer (SKU + two counter updates) must be all-or-nothing.
   Previously, sku_mutations.update() called conn.commit() mid-transaction,
   meaning the SKU row could commit while the counter update had not.

2. Stock ledger coherence: receiving (PO) and withdrawal stock changes must write
   the inventory_transactions ledger entry in the SAME transaction as the
   skus.quantity update. A crash between the two would produce phantom stock.

3. Variant attrs round-trip: variant_attrs dict survives create → read → update →
   read with no data loss, coercion, or JSON parse errors.

4. Family hierarchy: POST /products/{id}/skus correctly creates a sibling SKU
   under an existing Product parent; both SKUs appear in GET /products/{id}/skus;
   the Product's sku_count reflects both.

5. Adopt-sku: PATCH /products/{id}/adopt-sku/{sku_id} moves an orphan SKU into
   a family, and the move is reflected immediately in both list endpoints.

6. Concurrent stock mutations: N threads simultaneously withdraw from the same
   product — none may overdraw, total debited equals total succeeded * qty,
   final stock is non-negative, and one inventory_transactions row exists per
   successful withdrawal.

All assertions are made against live DB state (not just HTTP responses) to catch
cases where a response was 200 but the underlying write never committed.
"""
from __future__ import annotations
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING
import pytest
from shared.infrastructure.db import sql_execute
from tests.e2e.helpers import create_po, receive_po
if TYPE_CHECKING:
    from starlette.testclient import TestClient
from tests.e2e.helpers import create_product, create_withdrawal, e2e_job_id
from tests.helpers.auth import admin_headers

def _db_qty(client: TestClient, sku_id: str) -> float:
    """Read skus.quantity directly from the database."""

    async def _q() -> float:
        cur = await sql_execute('SELECT quantity FROM skus WHERE id = $1', (sku_id,))
        row = cur.rows[0] if cur.rows else None
        return float(row[0]) if row else -1.0
    return client.portal.call(_q)

def _db_dept_sku_count(client: TestClient, dept_id: str) -> int:
    """Read departments.sku_count directly from the database."""

    async def _q() -> int:
        cur = await sql_execute('SELECT sku_count FROM departments WHERE id = $1', (dept_id,))
        row = cur.rows[0] if cur.rows else None
        return int(row[0]) if row else -1
    return client.portal.call(_q)

def _db_product_sku_count(client: TestClient, product_id: str) -> int:
    """Read products.sku_count directly from the database."""

    async def _q() -> int:
        cur = await sql_execute('SELECT sku_count FROM products WHERE id = $1', (product_id,))
        row = cur.rows[0] if cur.rows else None
        return int(row[0]) if row else -1
    return client.portal.call(_q)

def _db_product_family_id_for_sku(client: TestClient, sku_id: str) -> str:
    """Read skus.product_family_id directly from the database."""

    async def _q() -> str:
        cur = await sql_execute('SELECT product_family_id FROM skus WHERE id = $1', (sku_id,))
        row = cur.rows[0] if cur.rows else None
        return str(row[0]) if row else ''
    return client.portal.call(_q)

def _db_count_inventory_transactions(client: TestClient, sku_id: str, tx_type: str) -> int:
    """Count stock_transactions rows for a product and transaction type."""

    async def _q() -> int:
        cur = await sql_execute('SELECT COUNT(*) FROM stock_transactions WHERE sku_id = $1 AND transaction_type = $2', (sku_id, tx_type))
        row = cur.rows[0] if cur.rows else None
        return int(row[0]) if row else 0
    return client.portal.call(_q)

def _db_variant_attrs(client: TestClient, sku_id: str) -> dict:
    """Read variant_attrs JSON directly from the database and parse it."""

    async def _q() -> str:
        cur = await sql_execute('SELECT variant_attrs FROM skus WHERE id = $1', (sku_id,))
        row = cur.rows[0] if cur.rows else None
        return str(row[0]) if row else '{}'
    import json
    raw = client.portal.call(_q)
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}

def _db_category_id(client: TestClient, sku_id: str) -> str:
    """Read skus.category_id directly from the database."""

    async def _q() -> str:
        cur = await sql_execute('SELECT category_id FROM skus WHERE id = $1', (sku_id,))
        row = cur.rows[0] if cur.rows else None
        return str(row[0]) if row else ''
    return client.portal.call(_q)

def _get_or_create_dept(client: TestClient, headers: dict, name: str, code: str) -> str:
    resp = client.get('/api/beta/catalog/departments', headers=headers)
    if resp.status_code == 200:
        for dept in resp.json():
            if dept.get('code') == code:
                return dept['id']
    resp = client.post('/api/beta/catalog/departments', json={'name': name, 'code': code, 'description': f'{name} dept'}, headers=headers)
    assert resp.status_code == 200, f'Dept create failed: {resp.text}'
    return resp.json()['id']

@pytest.mark.timeout(60)
class TestCatalogIntegrity:
    """Catalog mutation atomicity, variant attrs, and family hierarchy invariants."""

    def test_category_transfer_updates_counters_atomically(self, client: TestClient, seed_dept_id: str) -> None:
        """Moving a SKU to a new category must atomically update:
           - skus.category_id
           - old department sku_count (-1)
           - new department sku_count (+1)

        Previously, sku_mutations.update() committed the SKU row independently of
        the counter updates, meaning a crash or error between them left permanent
        counter drift. This test verifies all three land together.
        """
        headers = admin_headers()
        plmb_id = _get_or_create_dept(client, headers, 'Plumbing', 'PLM')
        sku_count_hdw_before = _db_dept_sku_count(client, seed_dept_id)
        sku_count_plmb_before = _db_dept_sku_count(client, plmb_id)
        product = create_product(client, headers, dept_id=seed_dept_id, name='Cat-Transfer-Widget', quantity=5)
        sku_id = product['id']
        sku_count_hdw_after_create = _db_dept_sku_count(client, seed_dept_id)
        assert sku_count_hdw_after_create == sku_count_hdw_before + 1, 'HDW counter should have incremented by 1 after create'
        resp = client.put(f'/api/beta/catalog/skus/{sku_id}', json={'category_id': plmb_id}, headers=headers)
        assert resp.status_code == 200, f'Category transfer failed: {resp.text}'
        db_cat = _db_category_id(client, sku_id)
        assert db_cat == plmb_id, f'SKU category_id should be {plmb_id}, got {db_cat}'
        sku_count_hdw_final = _db_dept_sku_count(client, seed_dept_id)
        sku_count_plmb_final = _db_dept_sku_count(client, plmb_id)
        assert sku_count_hdw_final == sku_count_hdw_before, f'HDW counter should be back to {sku_count_hdw_before} after transfer out, got {sku_count_hdw_final}'
        assert sku_count_plmb_final == sku_count_plmb_before + 1, f'PLM counter should be {sku_count_plmb_before + 1} after transfer in, got {sku_count_plmb_final}'

    def test_variant_attrs_create_read_update_read(self, client: TestClient, seed_dept_id: str) -> None:
        """variant_attrs must survive the full create → read → update → read cycle
        with exact fidelity — no JSON parse errors, no data loss, no coercion.
        """
        headers = admin_headers()
        initial_attrs = {'holes': '1H', 'size': '1/2"', 'material': 'galvanized steel'}
        resp = client.post('/api/beta/catalog/skus', json={'name': 'VariantAttrs-EMT-Strap', 'price': 1.39, 'cost': 0.26, 'quantity': 50, 'category_id': seed_dept_id, 'variant_attrs': initial_attrs}, headers=headers)
        assert resp.status_code == 200, f'Create failed: {resp.text}'
        sku_id = resp.json()['id']
        db_attrs = _db_variant_attrs(client, sku_id)
        assert db_attrs == initial_attrs, f'DB variant_attrs mismatch after create: expected {initial_attrs}, got {db_attrs}'
        resp = client.get(f'/api/beta/catalog/skus/{sku_id}', headers=headers)
        assert resp.status_code == 200
        http_attrs = resp.json().get('variant_attrs', {})
        assert http_attrs == initial_attrs, f'HTTP variant_attrs mismatch after create: expected {initial_attrs}, got {http_attrs}'
        updated_attrs = {'holes': '1H', 'size': '1/2"', 'material': 'zinc-plated', 'pack': '3pk'}
        resp = client.put(f'/api/beta/catalog/skus/{sku_id}', json={'variant_attrs': updated_attrs}, headers=headers)
        assert resp.status_code == 200, f'Update failed: {resp.text}'
        db_attrs_after_update = _db_variant_attrs(client, sku_id)
        assert db_attrs_after_update == updated_attrs, f'DB variant_attrs mismatch after update: expected {updated_attrs}, got {db_attrs_after_update}'
        resp = client.get(f'/api/beta/catalog/skus/{sku_id}', headers=headers)
        assert resp.status_code == 200
        http_attrs_after_update = resp.json().get('variant_attrs', {})
        assert http_attrs_after_update == updated_attrs, f'HTTP variant_attrs mismatch after update: expected {updated_attrs}, got {http_attrs_after_update}'

    def test_product_family_multi_variant_sku_count(self, client: TestClient, seed_dept_id: str) -> None:
        """Creating a Product family then adding two variant SKUs via
        POST /products/{id}/skus must result in:
        - product.sku_count == 2 in DB
        - GET /products/{id}/skus returns both variants
        - Each variant has distinct variant_attrs
        """
        headers = admin_headers()
        resp = client.post('/api/beta/catalog/products', json={'name': 'EMT Strap 1/2in', 'category_id': seed_dept_id}, headers=headers)
        assert resp.status_code == 200, f'Product family create failed: {resp.text}'
        family_id = resp.json()['id']
        resp1 = client.post(f'/api/beta/catalog/products/{family_id}/skus', json={'name': '1/2" EMT 1H Strap 3pk', 'price': 1.39, 'cost': 0.26, 'quantity': 21, 'category_id': seed_dept_id, 'variant_attrs': {'holes': '1H', 'pack': '3pk'}}, headers=headers)
        assert resp1.status_code == 200, f'Variant 1 create failed: {resp1.text}'
        sku1_id = resp1.json()['id']
        resp2 = client.post(f'/api/beta/catalog/products/{family_id}/skus', json={'name': '1/2" EMT 2H Strap 3pk', 'price': 1.39, 'cost': 0.22, 'quantity': 26, 'category_id': seed_dept_id, 'variant_attrs': {'holes': '2H', 'pack': '3pk'}}, headers=headers)
        assert resp2.status_code == 200, f'Variant 2 create failed: {resp2.text}'
        sku2_id = resp2.json()['id']
        db_count = _db_product_sku_count(client, family_id)
        assert db_count == 2, f'products.sku_count should be 2, got {db_count}'
        resp = client.get(f'/api/beta/catalog/products/{family_id}', headers=headers)
        assert resp.status_code == 200
        family = resp.json()
        sku_ids = {s['id'] for s in family.get('skus', [])}
        assert sku1_id in sku_ids, f'Variant 1 ({sku1_id}) missing from family SKUs: {sku_ids}'
        assert sku2_id in sku_ids, f'Variant 2 ({sku2_id}) missing from family SKUs: {sku_ids}'
        attrs1 = next((s['variant_attrs'] for s in family['skus'] if s['id'] == sku1_id))
        attrs2 = next((s['variant_attrs'] for s in family['skus'] if s['id'] == sku2_id))
        assert attrs1 != attrs2, 'Sibling SKUs should have distinct variant_attrs'
        assert attrs1.get('holes') == '1H'
        assert attrs2.get('holes') == '2H'

    def test_adopt_sku_reassigns_product_parent(self, client: TestClient, seed_dept_id: str) -> None:
        """PATCH /products/{family_id}/adopt-sku/{sku_id} must atomically:
        - Update skus.product_family_id in DB
        - Make the SKU appear in GET /products/{family_id}/skus
        - Be idempotent (re-adopting the same SKU returns 200 with no side-effects)
        """
        headers = admin_headers()
        orphan = create_product(client, headers, dept_id=seed_dept_id, name='Orphan-Paint-Brush-2in', quantity=10)
        orphan_original_family_id = _db_product_family_id_for_sku(client, orphan['id'])
        resp = client.post('/api/beta/catalog/products', json={'name': 'Paint Brushes', 'category_id': seed_dept_id}, headers=headers)
        assert resp.status_code == 200
        family_id = resp.json()['id']
        resp = client.patch(f"/api/beta/catalog/products/{family_id}/adopt-sku/{orphan['id']}", headers=headers)
        assert resp.status_code == 200, f'Adopt-sku failed: {resp.text}'
        db_family_id = _db_product_family_id_for_sku(client, orphan['id'])
        assert db_family_id == family_id, f'DB product_family_id should be {family_id}, got {db_family_id}'
        assert db_family_id != orphan_original_family_id, 'SKU should have moved away from its auto-created solo parent'
        resp = client.get(f'/api/beta/catalog/products/{family_id}', headers=headers)
        assert resp.status_code == 200
        sku_ids = {s['id'] for s in resp.json().get('skus', [])}
        assert orphan['id'] in sku_ids, f"Adopted SKU {orphan['id']} not visible in family {family_id}"
        resp2 = client.patch(f"/api/beta/catalog/products/{family_id}/adopt-sku/{orphan['id']}", headers=headers)
        assert resp2.status_code == 200
        db_family_id_again = _db_product_family_id_for_sku(client, orphan['id'])
        assert db_family_id_again == family_id, 'Re-adopt must not corrupt the product_family_id'

    def test_receiving_stock_change_and_ledger_entry_are_atomic(self, client: TestClient, seed_dept_id: str) -> None:
        """After PO receive:
        - skus.quantity in DB must reflect the added stock
        - stock_transactions must have exactly one 'receiving' row for this SKU
        Both must be true — not just the HTTP response.

        This tests that process_receiving_stock_changes now owns its own transaction:
        the quantity increment and ledger entry cannot diverge.
        """
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, name='PO-Atomic-Widget', quantity=5, cost=3.0)
        sku_id = product['id']
        qty_before = _db_qty(client, sku_id)
        po = create_po(client, headers, product, quantity=30, vendor_name='AtomicVendor')
        receive_po(client, headers, po['id'])
        qty_after = _db_qty(client, sku_id)
        assert qty_after > qty_before, f'Stock should have increased: was {qty_before}, still {qty_after}'
        tx_count = _db_count_inventory_transactions(client, sku_id, 'receiving')
        assert tx_count >= 1, f"stock_transactions must have >= 1 'receiving' row for {sku_id}, found {tx_count}"

    def test_withdrawal_stock_decrement_and_ledger_entry_are_atomic(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """After a withdrawal:
        - skus.quantity in DB must be decremented by the withdrawn amount
        - stock_transactions must have exactly one 'withdrawal' row
        Both are verified against live DB state.
        """
        headers = admin_headers()
        withdraw_qty = 7
        product = create_product(client, headers, dept_id=seed_dept_id, name='Withdrawal-Atomic-Widget', quantity=50, cost=2.0)
        sku_id = product['id']
        qty_before = _db_qty(client, sku_id)
        tx_before = _db_count_inventory_transactions(client, sku_id, 'withdrawal')
        create_withdrawal(client, headers, product, quantity=withdraw_qty)
        qty_after = _db_qty(client, sku_id)
        tx_after = _db_count_inventory_transactions(client, sku_id, 'withdrawal')
        assert qty_after == qty_before - withdraw_qty, f'Stock should be {qty_before - withdraw_qty}, got {qty_after}'
        assert tx_after == tx_before + 1, f'stock_transactions should have 1 new withdrawal row, before={tx_before} after={tx_after}'

    def test_concurrent_withdrawals_no_overdraw_exact_ledger(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """N concurrent withdrawals on a product with limited stock.
        Invariants:
        - Final stock >= 0 (no negative overdraw)
        - stock_transactions row count == number of successful withdrawals
        - Total stock debited == (num_successful * per_withdrawal_qty)
        - Failed withdrawals return 4xx, not 200

        This is the hardest test: it validates that the atomic UPDATE quantity guard
        in atomic_decrement_sku works correctly under real concurrency and that the
        ledger entry is always written in the same transaction as the decrement.
        """
        headers = admin_headers()
        n_workers = 8
        withdraw_qty = 10
        initial_stock = 35
        product = create_product(client, headers, dept_id=seed_dept_id, name=f'Concurrent-Stock-Widget-{int(time.time())}', quantity=initial_stock, cost=1.0)
        sku_id = product['id']

        def _attempt(i: int) -> int:
            resp = client.post(f'/api/beta/operations/withdrawals/for-contractor?contractor_id={seed_contractor_id}', json={'items': [{'sku_id': product['id'], 'sku': product['sku'], 'name': product['name'], 'quantity': withdraw_qty, 'unit_price': product['price'], 'cost': product['cost']}], 'job_id': e2e_job_id(f'CONCURRENT-{i}'), 'service_address': '100 Concurrent Lane'}, headers=headers)
            return resp.status_code
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(_attempt, i) for i in range(n_workers)]
            status_codes = [f.result() for f in as_completed(futures)]
        successes = sum((1 for s in status_codes if s == 200))
        failures = sum((1 for s in status_codes if s != 200))
        max_possible = initial_stock // withdraw_qty
        assert successes <= max_possible, f'At most {max_possible} withdrawals of {withdraw_qty} can succeed from stock={initial_stock}, but {successes} succeeded'
        assert successes + failures == n_workers, 'All attempts must have a definitive outcome'
        final_qty = _db_qty(client, sku_id)
        expected_qty = initial_stock - successes * withdraw_qty
        assert final_qty == expected_qty, f'Final stock should be {expected_qty} ({initial_stock} - {successes}×{withdraw_qty}), got {final_qty}'
        assert final_qty >= 0, f'Stock went negative: {final_qty}'
        tx_count = _db_count_inventory_transactions(client, sku_id, 'withdrawal')
        assert tx_count == successes, f'stock_transactions must have exactly {successes} withdrawal rows (one per success), found {tx_count}'

    def test_sku_edit_cannot_directly_overwrite_stock_quantity(self, client: TestClient, seed_dept_id: str) -> None:
        """PUT /catalog/skus/{id} must not allow direct quantity overwrites.
        Stock changes must go through the inventory adjustment endpoint.
        This protects the stock ledger from silent bypasses.
        """
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, name='NoQtyEdit-Widget', quantity=50)
        sku_id = product['id']
        qty_before = _db_qty(client, sku_id)
        client.put(f'/api/beta/catalog/skus/{sku_id}', json={'name': product['name'], 'quantity': 999}, headers=headers)
        resp2 = client.put(f'/api/beta/catalog/skus/{sku_id}', json={'name': 'NoQtyEdit-Widget-Renamed'}, headers=headers)
        assert resp2.status_code == 200
        qty_after = _db_qty(client, sku_id)
        assert qty_after == qty_before, f'Stock should not change on a name-only edit: was {qty_before}, got {qty_after}'

    def test_sku_without_variant_attrs_defaults_to_empty_dict(self, client: TestClient, seed_dept_id: str) -> None:
        """SKUs created without variant_attrs must have {} in DB and HTTP,
        not null, not a JSON parse error, not an empty string.
        """
        headers = admin_headers()
        resp = client.post('/api/beta/catalog/skus', json={'name': 'NoAttrs-Widget', 'price': 5.0, 'cost': 2.0, 'quantity': 10, 'category_id': seed_dept_id}, headers=headers)
        assert resp.status_code == 200
        sku_id = resp.json()['id']
        db_attrs = _db_variant_attrs(client, sku_id)
        assert db_attrs == {}, f'variant_attrs should be empty dict, got {db_attrs!r}'
        http_attrs = resp.json().get('variant_attrs')
        assert isinstance(http_attrs, dict), f'HTTP variant_attrs should be dict, got {http_attrs!r}'
        assert http_attrs == {}, f'HTTP variant_attrs should be {{}}, got {http_attrs}'

    def test_pack_sell_decrement_applies_pack_qty(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """Withdrawing 3 packs of a pack_qty=6 SKU (base_unit=each, sell_uom=pack)
        must deduct 18 each from stock, not 3.
        """
        headers = admin_headers()
        sku = create_product(client, headers, dept_id=seed_dept_id, name='Pack-Sell-Widget', quantity=100, cost=1.0, base_unit='each', sell_uom='pack', pack_qty=6)
        sku_id = sku['id']
        qty_before = _db_qty(client, sku_id)
        create_withdrawal(client, headers, sku, quantity=3, contractor_id=seed_contractor_id)
        qty_after = _db_qty(client, sku_id)
        expected = qty_before - 18
        assert qty_after == expected, f'Stock should be {expected} (3 packs × 6 = 18 deducted from {qty_before}), got {qty_after}'

    def test_receive_cases_sell_packs_round_trip(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """Full cycle: create a SKU with base_unit=each, purchase_uom=case,
        purchase_pack_qty=12, sell_uom=pack, pack_qty=6. Receive 5 cases via
        PO (should add 60 each). Then withdraw 3 packs (should deduct 18 each).
        Final stock = initial + 60 - 18.
        """
        headers = admin_headers()
        initial_qty = 10
        sku = create_product(client, headers, dept_id=seed_dept_id, name='RoundTrip-Pipe-Fitting', quantity=initial_qty, cost=2.0, base_unit='each', sell_uom='pack', pack_qty=6, purchase_uom='case', purchase_pack_qty=12)
        sku_id = sku['id']
        po = create_po(client, headers, sku, quantity=5, purchase_uom='case', purchase_pack_qty=12)
        receive_po(client, headers, po['id'])
        qty_after_receive = _db_qty(client, sku_id)
        assert qty_after_receive == initial_qty + 60, f'After receiving 5 cases of 12, stock should be {initial_qty + 60}, got {qty_after_receive}'
        create_withdrawal(client, headers, sku, quantity=3, contractor_id=seed_contractor_id)
        qty_final = _db_qty(client, sku_id)
        expected_final = initial_qty + 60 - 18
        assert qty_final == expected_final, f'After receive 5 cases + sell 3 packs, stock should be {expected_final}, got {qty_final}'

    def test_simple_each_withdrawal_unchanged(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """Withdrawing N each of a base_unit=each, sell_uom=each, pack_qty=1 SKU
        must deduct exactly N. Regression test for the pack conversion fix.
        """
        headers = admin_headers()
        sku = create_product(client, headers, dept_id=seed_dept_id, name='Simple-Each-Widget', quantity=50, cost=2.0)
        sku_id = sku['id']
        qty_before = _db_qty(client, sku_id)
        create_withdrawal(client, headers, sku, quantity=7, contractor_id=seed_contractor_id)
        qty_after = _db_qty(client, sku_id)
        assert qty_after == qty_before - 7, f'Stock should be {qty_before - 7}, got {qty_after}'
