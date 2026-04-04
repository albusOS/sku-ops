"""
Repository contract tests — write -> read -> assert field names, types, values.

These tests enforce that:
  1. What the repo writes to the DB can be read back with the correct field names
  2. Numeric fields are the correct type (float, not int) after a round-trip
  3. Domain model field names match what the repo returns (e.g. unit_price vs price)
  4. Normalized child-table items (withdrawal_items, material_request_items) survive round-trip

These would have caught:
  - The price->unit_price column mapping bug in the purchasing PO service
  - Missing float coercion in credit_note_repo
  - Any schema drift between domain models and SQL columns
"""
import uuid
import pytest
from catalog.application.sku_lifecycle import create_product_with_sku
from finance.application.invoice_service import create_invoice_from_withdrawals
from inventory.application.inventory_service import process_import_stock_changes
from purchasing.domain.purchase_order import POItemStatus, POStatus, PurchaseOrder, PurchaseOrderItem
from shared.infrastructure.db import sql_execute
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import ADMIN_USER_ID, CONTRACTOR_USER_ID, SEEDED_DEPT_ID, SEEDED_JOB_ID, SEEDED_VENDOR_ID

class TestProductRepoContract:

    def test_round_trip_preserves_float_quantity(self, call):
        """Insert a SKU with float quantity, read it back, assert float."""

        async def _body():
            sku = await create_product_with_sku(category_id=SEEDED_DEPT_ID, category_name='Hardware', name='Round Trip Widget', quantity=7.25, price=12.5, cost=6.75, base_unit='foot', sell_uom='inch', user_id=ADMIN_USER_ID, user_name='Test', on_stock_import=process_import_stock_changes)
            row = await get_database_manager().catalog.get_sku_by_id(sku.id, DEFAULT_ORG_ID)
            assert row is not None
            assert isinstance(row.quantity, float), f'quantity is {type(row.quantity)}'
            assert row.quantity == pytest.approx(7.25)
            assert isinstance(row.price, float), f'price is {type(row.price)}'
            assert row.price == pytest.approx(12.5)
            assert isinstance(row.cost, float), f'cost is {type(row.cost)}'
            assert row.cost == pytest.approx(6.75)
            assert row.base_unit == 'foot'
            assert row.sell_uom == 'inch'
        call(_body)

    def test_list_skus_returns_float_quantities(self, call):
        """Listing SKUs must return float quantities, not int."""

        async def _body():
            await create_product_with_sku(category_id=SEEDED_DEPT_ID, category_name='Hardware', name='List Test', quantity=3.5, user_id=ADMIN_USER_ID, user_name='Test', on_stock_import=process_import_stock_changes)
            skus = await get_database_manager().catalog.list_skus(DEFAULT_ORG_ID, limit=10)
            assert len(skus) >= 1
            for s in skus:
                assert isinstance(s.quantity, float), f"sku '{s.name}' quantity is {type(s.quantity)}"
        call(_body)

class TestStockRepoContract:

    def test_transaction_round_trip_field_types(self, call):
        """Stock transaction read-back must have float quantity fields and unit."""

        async def _body():
            product = await create_product_with_sku(category_id=SEEDED_DEPT_ID, category_name='Hardware', name='Stock Repo Test', quantity=15.75, base_unit='gallon', user_id=ADMIN_USER_ID, user_name='Test', on_stock_import=process_import_stock_changes)
            txs = await get_database_manager().inventory.list_stock_transactions_by_product(DEFAULT_ORG_ID, product.id, limit=10)
            assert len(txs) >= 1
            tx = txs[0]
            assert tx.sku_id is not None
            assert tx.sku is not None
            assert tx.user_id is not None
            assert tx.unit is not None
            for field in ('quantity_delta', 'quantity_before', 'quantity_after'):
                assert isinstance(getattr(tx, field), float), f'stock_transaction.{field} is {type(getattr(tx, field)).__name__}, expected float'
            assert isinstance(tx.unit, str)
        call(_body)

class TestPORepoContract:

    def test_po_item_round_trip_has_unit_price_not_price(self, call):
        """PO items read from DB must use 'unit_price', not the raw column name 'price'."""

        async def _body():
            await sql_execute('INSERT INTO vendors (id, name, organization_id, created_at)\n                   VALUES ($1, $2, $3, NOW())\n                   ON CONFLICT (id) DO NOTHING', (SEEDED_VENDOR_ID, 'Acme', DEFAULT_ORG_ID))
            po = PurchaseOrder(vendor_id=SEEDED_VENDOR_ID, vendor_name='Acme', status=POStatus.ORDERED, created_by_id=ADMIN_USER_ID, created_by_name='Test', organization_id=DEFAULT_ORG_ID)
            pdb = get_database_manager().purchasing
            await pdb.insert_po(DEFAULT_ORG_ID, po)
            item = PurchaseOrderItem(po_id=po.id, name='Pipe', ordered_qty=5.5, delivered_qty=0, unit_price=12.99, cost=8.5, base_unit='foot', sell_uom='inch', pack_qty=1, suggested_department='PLU', status=POItemStatus.ORDERED, organization_id=DEFAULT_ORG_ID)
            await pdb.insert_po_items(DEFAULT_ORG_ID, [item])
            items = await pdb.get_po_items(DEFAULT_ORG_ID, po.id)
            assert len(items) == 1
            read_item = items[0]
            assert hasattr(read_item, 'unit_price'), f"PO item missing 'unit_price' — got fields: {list(read_item.model_fields)}"
            assert read_item.unit_price == pytest.approx(12.99)
            assert read_item.ordered_qty == pytest.approx(5.5)
            assert read_item.base_unit == 'foot'
        call(_body)

    def test_po_item_float_quantities(self, call):
        """PO item quantities must be float after read-back."""

        async def _body():
            await sql_execute('INSERT INTO vendors (id, name, organization_id, created_at)\n                   VALUES ($1, $2, $3, NOW())\n                   ON CONFLICT (id) DO NOTHING', (SEEDED_VENDOR_ID, 'Acme', DEFAULT_ORG_ID))
            po = PurchaseOrder(vendor_id=SEEDED_VENDOR_ID, vendor_name='Acme', status=POStatus.ORDERED, created_by_id=ADMIN_USER_ID, created_by_name='Test', organization_id=DEFAULT_ORG_ID)
            pdb = get_database_manager().purchasing
            await pdb.insert_po(DEFAULT_ORG_ID, po)
            item = PurchaseOrderItem(po_id=po.id, name='Fitting', ordered_qty=3.25, delivered_qty=1.5, unit_price=7.0, cost=4.0, base_unit='each', sell_uom='each', pack_qty=1, suggested_department='HDW', status=POItemStatus.PENDING, organization_id=DEFAULT_ORG_ID)
            await pdb.insert_po_items(DEFAULT_ORG_ID, [item])
            items = await pdb.get_po_items(DEFAULT_ORG_ID, po.id)
            read_item = items[0]
            for field in ('ordered_qty', 'delivered_qty', 'unit_price', 'cost'):
                val = getattr(read_item, field)
                assert isinstance(val, (int, float)), f'{field} is {type(val)}'
                assert float(val) == float(getattr(item, field))
        call(_body)

class TestCreditNoteRepoContract:

    def test_credit_note_line_items_have_float_amounts(self, call):
        """Credit note line items must have float quantity, unit_price, amount, cost."""

        async def _body():
            fin = get_database_manager().finance
            cn = await fin.credit_note_insert(DEFAULT_ORG_ID, str(uuid.uuid4()), None, [{'description': 'Widget return', 'quantity': 2.5, 'unit_price': 10.0, 'cost': 5.0, 'sku_id': None}], 25.0, 2.5, 27.5)
            assert cn is not None
            cn_read = await fin.credit_note_get_by_id(DEFAULT_ORG_ID, cn.id)
            assert cn_read is not None
            assert len(cn_read.line_items) == 1
            li = cn_read.line_items[0]
            for field in ('quantity', 'unit_price', 'amount', 'cost'):
                assert isinstance(getattr(li, field), float), f'credit_note line_item.{field} is {type(getattr(li, field)).__name__}, expected float'
            assert li.quantity == pytest.approx(2.5)
            assert li.unit_price == pytest.approx(10.0)
        call(_body)

class TestInvoiceRepoContract:

    def test_invoice_line_items_have_float_amounts(self, call):
        """Invoice line items must have float quantity and amounts."""

        async def _body():
            withdrawal_id = '0195f2c0-89af-7000-8000-000000000001'
            await sql_execute('INSERT INTO withdrawals\n                   (id, items, job_id, service_address, subtotal, tax, total, cost_total,\n                    contractor_id, contractor_name, contractor_company, billing_entity,\n                    payment_status, processed_by_id, processed_by_name,\n                    organization_id, created_at, invoice_id, paid_at)\n                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW(), NULL, NULL)', (withdrawal_id, None, SEEDED_JOB_ID, '123 Main St', 25.0, 2.5, 27.5, 12.5, CONTRACTOR_USER_ID, 'Contractor', 'ACME', 'ACME Inc', 'unpaid', ADMIN_USER_ID, 'Test', DEFAULT_ORG_ID))
            await sql_execute('INSERT INTO withdrawal_items\n                   (id, withdrawal_id, sku_id, sku, name, quantity, unit_price, cost, unit, amount, cost_total)\n                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)', ('0195f2c0-89af-7000-8000-000000000002', withdrawal_id, str(uuid.uuid4()), 'S', 'X', 2.5, 10.0, 5.0, 'each', 25.0, 12.5))
            inv = await create_invoice_from_withdrawals([withdrawal_id])
            assert inv is not None
            assert len(inv.line_items) >= 1
            li = inv.line_items[0]
            for field in ('quantity', 'unit_price', 'amount'):
                assert isinstance(getattr(li, field), float), f'invoice line_item.{field} is {type(getattr(li, field)).__name__}, expected float'
        call(_body)

class TestMaterialRequestRepoContract:

    def test_round_trip_preserves_items(self, call):
        """Material request items stored in material_request_items table must survive round-trip."""

        async def _body():
            from operations.domain.material_request import MaterialRequest
            from operations.domain.withdrawal import WithdrawalItem
            mr = MaterialRequest(contractor_id=CONTRACTOR_USER_ID, contractor_name='Contractor User', items=[WithdrawalItem(sku_id=str(uuid.uuid4()), sku='HDW-001', name='Widget', quantity=2.5, unit_price=10.0, cost=5.0, unit='foot')], status='pending', job_id=SEEDED_JOB_ID, service_address='456 Oak', organization_id=DEFAULT_ORG_ID)
            db = get_database_manager().operations
            await db.insert_material_request(DEFAULT_ORG_ID, mr)
            read = await db.get_material_request_by_id(DEFAULT_ORG_ID, mr.id)
            assert read is not None
            assert len(read.items) == 1
            item = read.items[0]
            assert item.quantity == 2.5
            assert item.unit == 'foot'
        call(_body)
