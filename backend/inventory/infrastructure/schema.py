"""Inventory context schema — stock transaction ledger."""

TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS stock_transactions (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        quantity_delta REAL NOT NULL,
        quantity_before REAL NOT NULL,
        quantity_after REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'each',
        transaction_type TEXT NOT NULL,
        reference_id TEXT,
        reference_type TEXT,
        reason TEXT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL DEFAULT '',
        organization_id TEXT,
        created_at TEXT NOT NULL
    )""",
]

INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_transactions(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_stock_created ON stock_transactions(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_stock_product_created ON stock_transactions(product_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_stock_transactions_org ON stock_transactions(organization_id)",
]
