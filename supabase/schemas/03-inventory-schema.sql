-- Inventory: stock_transactions, cycle_counts, cycle_count_items.

CREATE TABLE IF NOT EXISTS stock_transactions (
        id UUID PRIMARY KEY,
        sku_id UUID NOT NULL REFERENCES skus(id),
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
        original_quantity REAL,
        original_unit TEXT,
        user_id UUID NOT NULL REFERENCES users(id),
        user_name TEXT NOT NULL DEFAULT '',
        organization_id UUID NOT NULL REFERENCES organizations(id),
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS cycle_counts (
        id UUID PRIMARY KEY,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        status TEXT NOT NULL DEFAULT 'open',
        scope TEXT,
        created_by_id UUID NOT NULL REFERENCES users(id),
        created_by_name TEXT NOT NULL DEFAULT '',
        committed_by_id UUID REFERENCES users(id),
        committed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS cycle_count_items (
        id UUID PRIMARY KEY,
        cycle_count_id UUID NOT NULL REFERENCES cycle_counts(id),
        sku_id UUID NOT NULL REFERENCES skus(id),
        sku TEXT NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        snapshot_qty REAL NOT NULL,
        counted_qty REAL,
        variance REAL,
        unit TEXT NOT NULL DEFAULT 'each',
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_transactions(sku_id);

CREATE INDEX IF NOT EXISTS idx_stock_created ON stock_transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_stock_product_created ON stock_transactions(sku_id, created_at);

CREATE INDEX IF NOT EXISTS idx_stock_transactions_org ON stock_transactions(organization_id);

CREATE INDEX IF NOT EXISTS idx_cycle_counts_org ON cycle_counts(organization_id);

CREATE INDEX IF NOT EXISTS idx_cycle_counts_status ON cycle_counts(status);

CREATE INDEX IF NOT EXISTS idx_cycle_count_items_count ON cycle_count_items(cycle_count_id);

CREATE INDEX IF NOT EXISTS idx_cycle_count_items_product ON cycle_count_items(sku_id);

CREATE INDEX IF NOT EXISTS idx_cycle_counts_org_status_created ON cycle_counts(organization_id, status, created_at);
