"""Inventory context schema — stock transaction ledger and cycle counts."""

MIGRATIONS: list[str] = []

TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS stock_transactions (
        id TEXT PRIMARY KEY,
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        quantity_delta NUMERIC(18,4) NOT NULL,
        quantity_before NUMERIC(18,4) NOT NULL,
        quantity_after NUMERIC(18,4) NOT NULL,
        unit TEXT NOT NULL DEFAULT 'each',
        transaction_type TEXT NOT NULL,
        reference_id TEXT,
        reference_type TEXT,
        reason TEXT,
        original_quantity NUMERIC(18,4),
        original_unit TEXT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL DEFAULT '',
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS cycle_counts (
        id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        scope TEXT,
        created_by_id TEXT NOT NULL,
        created_by_name TEXT NOT NULL DEFAULT '',
        committed_by_id TEXT,
        committed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS cycle_count_items (
        id TEXT PRIMARY KEY,
        cycle_count_id TEXT NOT NULL,
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        snapshot_qty NUMERIC(18,4) NOT NULL,
        counted_qty NUMERIC(18,4),
        variance NUMERIC(18,4),
        unit TEXT NOT NULL DEFAULT 'each',
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
]

INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_transactions(sku_id)",
    "CREATE INDEX IF NOT EXISTS idx_stock_created ON stock_transactions(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_stock_product_created ON stock_transactions(sku_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_stock_transactions_org ON stock_transactions(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_counts_org ON cycle_counts(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_counts_status ON cycle_counts(status)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_count_items_count ON cycle_count_items(cycle_count_id)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_count_items_product ON cycle_count_items(sku_id)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_counts_org_status_created ON cycle_counts(organization_id, status, created_at)",
]
