"""Supabase migration source-of-truth tests."""
from pathlib import Path
import asyncpg
import pytest
from shared.infrastructure.config import DATABASE_URL
EXPECTED_TABLES = {'organizations', 'users', 'refresh_tokens', 'audit_log', 'org_settings', 'oauth_states', 'fiscal_periods', 'departments', 'vendors', 'products', 'sku_counters', 'stock_transactions', 'cycle_counts', 'cycle_count_items', 'withdrawals', 'withdrawal_items', 'material_requests', 'material_request_items', 'returns', 'return_items', 'invoices', 'invoice_withdrawals', 'invoice_line_items', 'invoice_counters', 'credit_notes', 'credit_note_line_items', 'financial_ledger', 'payments', 'payment_withdrawals', 'billing_entities', 'purchase_orders', 'purchase_order_items', 'documents', 'jobs', 'addresses', 'memory_artifacts', 'agent_runs', 'skus', 'vendor_items', 'processed_events', 'embeddings'}

async def _bootstrap() -> dict[str, list[str]]:
    """Inspect the live schema created by the Supabase migration."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch('SELECT table_name FROM information_schema.tables WHERE table_schema = $1 ORDER BY table_name', 'public')
        tables = [r['table_name'] for r in rows]
        schema: dict[str, list[str]] = {}
        for table in tables:
            col_rows = await conn.fetch('SELECT column_name FROM information_schema.columns WHERE table_schema = $1 AND table_name = $2 ORDER BY ordinal_position', 'public', table)
            schema[table] = [r['column_name'] for r in col_rows]
        return schema
    finally:
        await conn.close()

def test_supabase_migration_file_exists():
    repo_root = Path(__file__).resolve().parents[3]
    migrations = sorted((repo_root / 'supabase' / 'migrations').glob('*.sql'))
    assert migrations, 'Expected at least one Supabase migration file.'

@pytest.mark.asyncio
async def test_live_schema_creates_all_expected_tables():
    """Every expected table must be present after Supabase reset."""
    schema = await _bootstrap()
    actual = set(schema.keys())
    missing = EXPECTED_TABLES - actual
    assert not missing, f'Tables missing from context schemas: {missing}'

@pytest.mark.asyncio
async def test_live_schema_tables_have_columns():
    """Every table must have at least one column after migration apply."""
    schema = await _bootstrap()
    empty = [t for t, cols in schema.items() if not cols]
    assert not empty, f'Tables with no columns: {empty}'

@pytest.mark.asyncio
async def test_invoices_has_xero_sync_status_column():
    """invoices.xero_sync_status must exist — the sync job reads and writes it."""
    schema = await _bootstrap()
    assert 'xero_sync_status' in schema['invoices'], 'invoices table is missing xero_sync_status column. This will break the Xero sync job at runtime.'

@pytest.mark.asyncio
async def test_invoices_has_xero_invoice_id_column():
    schema = await _bootstrap()
    assert 'xero_invoice_id' in schema['invoices']

@pytest.mark.asyncio
async def test_credit_notes_has_xero_sync_status_column():
    """credit_notes.xero_sync_status must exist."""
    schema = await _bootstrap()
    assert 'xero_sync_status' in schema['credit_notes'], 'credit_notes table is missing xero_sync_status column.'

@pytest.mark.asyncio
async def test_credit_notes_has_xero_credit_note_id_column():
    schema = await _bootstrap()
    assert 'xero_credit_note_id' in schema['credit_notes']

@pytest.mark.asyncio
async def test_purchase_orders_has_xero_bill_id_column():
    """purchase_orders.xero_bill_id must exist — PO Bills sync depends on it."""
    schema = await _bootstrap()
    assert 'xero_bill_id' in schema['purchase_orders'], 'purchase_orders table is missing xero_bill_id column. PO Bill sync will fail at runtime.'

@pytest.mark.asyncio
async def test_purchase_orders_has_xero_sync_status_column():
    schema = await _bootstrap()
    assert 'xero_sync_status' in schema['purchase_orders']

@pytest.mark.asyncio
async def test_cycle_counts_has_required_columns():
    """cycle_counts must have all columns the service reads and writes."""
    schema = await _bootstrap()
    required = {'id', 'organization_id', 'status', 'scope', 'created_by_id', 'created_by_name', 'committed_by_id', 'committed_at', 'created_at'}
    missing = required - set(schema['cycle_counts'])
    assert not missing, f'cycle_counts missing columns: {missing}'

@pytest.mark.asyncio
async def test_cycle_count_items_has_required_columns():
    """cycle_count_items must have all columns the service reads and writes."""
    schema = await _bootstrap()
    required = {'id', 'cycle_count_id', 'sku_id', 'sku', 'product_name', 'snapshot_qty', 'counted_qty', 'variance', 'unit', 'notes', 'created_at'}
    missing = required - set(schema['cycle_count_items'])
    assert not missing, f'cycle_count_items missing columns: {missing}'
