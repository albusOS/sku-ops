-- Operations: withdrawals, material_requests, material_request_items, returns,
-- withdrawal_items, return_items.

CREATE TABLE IF NOT EXISTS withdrawals (
        id TEXT PRIMARY KEY,
        items TEXT,
        job_id TEXT NOT NULL,
        service_address TEXT NOT NULL,
        notes TEXT,
        subtotal NUMERIC(18,2) NOT NULL,
        tax NUMERIC(18,2) NOT NULL,
        tax_rate NUMERIC(9,4) NOT NULL DEFAULT 0.0,
        total NUMERIC(18,2) NOT NULL,
        cost_total NUMERIC(18,2) NOT NULL,
        contractor_id TEXT NOT NULL,
        contractor_name TEXT NOT NULL DEFAULT '',
        contractor_company TEXT NOT NULL DEFAULT '',
        billing_entity TEXT NOT NULL DEFAULT '',
        billing_entity_id TEXT,
        payment_status TEXT NOT NULL DEFAULT 'unpaid',
        invoice_id TEXT,
        paid_at TIMESTAMPTZ,
        processed_by_id TEXT NOT NULL,
        processed_by_name TEXT NOT NULL DEFAULT '',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS material_requests (
        id TEXT PRIMARY KEY,
        contractor_id TEXT NOT NULL,
        contractor_name TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'pending',
        withdrawal_id TEXT,
        job_id TEXT,
        service_address TEXT,
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        processed_at TIMESTAMPTZ,
        processed_by_id TEXT,
        organization_id TEXT NOT NULL
    );

CREATE TABLE IF NOT EXISTS material_request_items (
        id TEXT PRIMARY KEY,
        material_request_id TEXT NOT NULL REFERENCES material_requests(id),
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'each'
    );

CREATE TABLE IF NOT EXISTS returns (
        id TEXT PRIMARY KEY,
        withdrawal_id TEXT NOT NULL,
        contractor_id TEXT NOT NULL,
        contractor_name TEXT NOT NULL DEFAULT '',
        billing_entity TEXT NOT NULL DEFAULT '',
        billing_entity_id TEXT,
        job_id TEXT NOT NULL DEFAULT '',
        subtotal NUMERIC(18,2) NOT NULL DEFAULT 0,
        tax NUMERIC(18,2) NOT NULL DEFAULT 0,
        total NUMERIC(18,2) NOT NULL DEFAULT 0,
        cost_total NUMERIC(18,2) NOT NULL DEFAULT 0,
        reason TEXT NOT NULL DEFAULT 'other',
        notes TEXT,
        credit_note_id TEXT,
        processed_by_id TEXT NOT NULL DEFAULT '',
        processed_by_name TEXT NOT NULL DEFAULT '',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS withdrawal_items (
        id TEXT PRIMARY KEY,
        withdrawal_id TEXT NOT NULL REFERENCES withdrawals(id),
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'each',
        amount NUMERIC(18,2) NOT NULL DEFAULT 0,
        cost_total NUMERIC(18,2) NOT NULL DEFAULT 0,
        sell_uom TEXT NOT NULL DEFAULT 'each',
        sell_cost NUMERIC(18,4) NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS return_items (
        id TEXT PRIMARY KEY,
        return_id TEXT NOT NULL REFERENCES returns(id),
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'each',
        amount NUMERIC(18,2) NOT NULL DEFAULT 0,
        cost_total NUMERIC(18,2) NOT NULL DEFAULT 0,
        sell_uom TEXT NOT NULL DEFAULT 'each',
        sell_cost NUMERIC(18,4) NOT NULL DEFAULT 0
    );

CREATE INDEX IF NOT EXISTS idx_withdrawals_contractor ON withdrawals(contractor_id);

CREATE INDEX IF NOT EXISTS idx_withdrawals_created ON withdrawals(created_at);

CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(payment_status);

CREATE INDEX IF NOT EXISTS idx_withdrawals_billing ON withdrawals(billing_entity);

CREATE INDEX IF NOT EXISTS idx_withdrawals_org ON withdrawals(organization_id);

CREATE INDEX IF NOT EXISTS idx_material_requests_contractor ON material_requests(contractor_id);

CREATE INDEX IF NOT EXISTS idx_material_requests_status ON material_requests(status);

CREATE INDEX IF NOT EXISTS idx_material_requests_org ON material_requests(organization_id);

CREATE INDEX IF NOT EXISTS idx_material_request_items_mrid ON material_request_items(material_request_id);

CREATE INDEX IF NOT EXISTS idx_material_request_items_sku ON material_request_items(sku_id);

CREATE INDEX IF NOT EXISTS idx_returns_withdrawal ON returns(withdrawal_id);

CREATE INDEX IF NOT EXISTS idx_returns_contractor ON returns(contractor_id);

CREATE INDEX IF NOT EXISTS idx_returns_org ON returns(organization_id);

CREATE INDEX IF NOT EXISTS idx_returns_created ON returns(created_at);

CREATE INDEX IF NOT EXISTS idx_withdrawal_items_wid ON withdrawal_items(withdrawal_id);

CREATE INDEX IF NOT EXISTS idx_withdrawal_items_sku ON withdrawal_items(sku_id);

CREATE INDEX IF NOT EXISTS idx_return_items_rid ON return_items(return_id);

CREATE INDEX IF NOT EXISTS idx_return_items_sku ON return_items(sku_id);

CREATE INDEX IF NOT EXISTS idx_withdrawals_invoice ON withdrawals(invoice_id);

CREATE INDEX IF NOT EXISTS idx_withdrawals_job ON withdrawals(organization_id, job_id);

CREATE INDEX IF NOT EXISTS idx_returns_credit_note ON returns(organization_id, credit_note_id);
