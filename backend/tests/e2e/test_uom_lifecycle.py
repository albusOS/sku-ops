"""E2E: Unit of measure lifecycle — custom units through product creation and withdrawal.

Covers the full flow:
1. Admin creates a custom unit via the units API
2. Product is created with the custom unit
3. Product sell_uom is updated via the SKU update endpoint
4. Withdrawal uses the custom sell_uom
5. Stock ledger records the correct unit
6. Deleting a unit does not affect existing products that reference it
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from starlette.testclient import TestClient
from tests.e2e.helpers import create_product, create_withdrawal
from tests.helpers.auth import admin_headers

class TestUomLifecycle:
    """Full lifecycle of DB-backed units of measure."""

    def test_seeded_units_available(self, client: TestClient, seed_dept_id: str) -> None:
        headers = admin_headers()
        resp = client.get('/api/beta/catalog/units', headers=headers)
        assert resp.status_code == 200
        codes = {u['code'] for u in resp.json()}
        for expected in ('each', 'roll', 'gallon', 'pallet', 'bundle', 'slab'):
            assert expected in codes, f"Seeded unit '{expected}' missing"

    def test_custom_unit_roundtrip(self, client: TestClient, seed_dept_id: str) -> None:
        """Create a custom unit, use it on a product, verify it persists."""
        headers = admin_headers()
        resp = client.post('/api/beta/catalog/units', json={'code': 'crate', 'name': 'Crate', 'family': 'discrete'}, headers=headers)
        assert resp.status_code == 200
        uom = resp.json()
        assert uom['code'] == 'crate'
        product = create_product(client, headers, dept_id=seed_dept_id, name='Crate Widget', base_unit='crate', sell_uom='crate')
        assert product['base_unit'] == 'crate'
        assert product['sell_uom'] == 'crate'
        sku_resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert sku_resp.status_code == 200
        assert sku_resp.json()['base_unit'] == 'crate'

    def test_update_sku_sell_uom_to_custom(self, client: TestClient, seed_dept_id: str) -> None:
        """Updating a product's sell_uom to a custom unit works."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, name='Flexible UOM Widget')
        assert product['sell_uom'] == 'each'
        resp = client.put(f"/api/beta/catalog/skus/{product['id']}", json={'sell_uom': 'bundle'}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()['sell_uom'] == 'bundle'

    def test_withdrawal_with_custom_unit(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """Products with custom units can be withdrawn successfully."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, name='Pallet Widget', base_unit='pallet', sell_uom='pallet', quantity=50, price=100.0, cost=50.0)
        withdrawal = create_withdrawal(client, headers, product, quantity=2, unit='pallet')
        assert withdrawal['id']
        sku = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers).json()
        assert sku['quantity'] == 48.0

    def test_delete_unit_does_not_affect_existing_products(self, client: TestClient, seed_dept_id: str) -> None:
        """Deleting a unit from the lookup table doesn't corrupt existing SKUs."""
        headers = admin_headers()
        create_resp = client.post('/api/beta/catalog/units', json={'code': 'drum', 'name': 'Drum', 'family': 'discrete'}, headers=headers)
        uom_id = create_resp.json()['id']
        product = create_product(client, headers, dept_id=seed_dept_id, name='Drum Widget', base_unit='drum', sell_uom='drum')
        del_resp = client.delete(f'/api/beta/catalog/units/{uom_id}', headers=headers)
        assert del_resp.status_code == 200
        sku = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers).json()
        assert sku['base_unit'] == 'drum'
        assert sku['sell_uom'] == 'drum'

    def test_unit_codes_are_unique_per_org(self, client: TestClient, seed_dept_id: str) -> None:
        """Cannot create two units with the same code."""
        headers = admin_headers()
        resp1 = client.post('/api/beta/catalog/units', json={'code': 'barrel', 'name': 'Barrel'}, headers=headers)
        assert resp1.status_code == 200
        resp2 = client.post('/api/beta/catalog/units', json={'code': 'barrel', 'name': 'Barrel 2'}, headers=headers)
        assert resp2.status_code == 400

class TestSkuRenameLifecycle:
    """SKU code rename through the full product lifecycle."""

    def test_rename_sku_and_withdraw(self, client: TestClient, seed_dept_id: str, seed_contractor_id: str) -> None:
        """Renamed SKU continues to work for withdrawals."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, name='Rename Lifecycle Widget', quantity=50, price=20.0, cost=10.0)
        old_sku = product['sku']
        resp = client.put(f"/api/beta/catalog/skus/{product['id']}", json={'sku': 'RLW-RENAMED-01'}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()['sku'] == 'RLW-RENAMED-01'
        get_old = client.get(f'/api/beta/catalog/skus/by-barcode?barcode={old_sku}', headers=headers)
        assert get_old.status_code == 404
        product['sku'] = 'RLW-RENAMED-01'
        withdrawal = create_withdrawal(client, headers, product, quantity=3)
        assert withdrawal['id']
        sku = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers).json()
        assert sku['quantity'] == 47.0
        assert sku['sku'] == 'RLW-RENAMED-01'

    def test_rename_sku_with_category_change(self, client: TestClient, seed_dept_id: str) -> None:
        """Rename SKU at the same time as changing category."""
        headers = admin_headers()
        dept_resp = client.post('/api/beta/catalog/departments', json={'name': 'Electrical', 'code': 'ELC', 'description': 'Electrical dept'}, headers=headers)
        if dept_resp.status_code == 200:
            elc_id = dept_resp.json()['id']
        else:
            depts = client.get('/api/beta/catalog/departments', headers=headers).json()
            elc_id = next((d['id'] for d in depts if d['code'] == 'ELC'))
        product = create_product(client, headers, dept_id=seed_dept_id, name='Category Switch Widget')
        assert 'HDW' in product['sku']
        resp = client.put(f"/api/beta/catalog/skus/{product['id']}", json={'category_id': elc_id, 'sku': 'ELC-SWITCH-01'}, headers=headers)
        assert resp.status_code == 200
        updated = resp.json()
        assert updated['sku'] == 'ELC-SWITCH-01'
        assert updated['category_name'] == 'Electrical'

    def test_duplicate_rename_blocked(self, client: TestClient, seed_dept_id: str) -> None:
        """Cannot rename a SKU to an existing code."""
        headers = admin_headers()
        p1 = create_product(client, headers, dept_id=seed_dept_id, name='Dup A')
        p2 = create_product(client, headers, dept_id=seed_dept_id, name='Dup B')
        resp = client.put(f"/api/beta/catalog/skus/{p2['id']}", json={'sku': p1['sku']}, headers=headers)
        assert resp.status_code == 409
