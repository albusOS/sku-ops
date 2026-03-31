-- Finance: invoices, credit notes, payments, ledger, join tables, counters.

CREATE TABLE IF NOT EXISTS invoices (
        id UUID PRIMARY KEY,
        invoice_number TEXT UNIQUE NOT NULL,
        billing_entity TEXT NOT NULL DEFAULT '',
        billing_entity_id UUID REFERENCES billing_entities(id),
        contact_name TEXT NOT NULL DEFAULT '',
        contact_email TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft',
        subtotal NUMERIC(18,2) NOT NULL,
        tax NUMERIC(18,2) NOT NULL,
        tax_rate NUMERIC(9,4) NOT NULL DEFAULT 0.0,
        total NUMERIC(18,2) NOT NULL,
        amount_credited NUMERIC(18,2) NOT NULL DEFAULT 0,
        notes TEXT,
        invoice_date TIMESTAMPTZ,
        due_date TIMESTAMPTZ,
        payment_terms TEXT NOT NULL DEFAULT 'net_30',
        billing_address TEXT NOT NULL DEFAULT '',
        po_reference TEXT NOT NULL DEFAULT '',
        currency TEXT NOT NULL DEFAULT 'USD',
        approved_by_id UUID REFERENCES users(id),
        approved_at TIMESTAMPTZ,
        xero_invoice_id TEXT,
        xero_cogs_journal_id TEXT,
        xero_sync_status TEXT NOT NULL DEFAULT 'pending',
        organization_id UUID REFERENCES organizations(id),
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS invoice_withdrawals (
        invoice_id UUID NOT NULL REFERENCES invoices(id),
        withdrawal_id UUID NOT NULL REFERENCES withdrawals(id),
        PRIMARY KEY (invoice_id, withdrawal_id)
    );

CREATE TABLE IF NOT EXISTS invoice_line_items (
        id UUID PRIMARY KEY,
        invoice_id UUID NOT NULL REFERENCES invoices(id),
        description TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL,
        amount NUMERIC(18,2) NOT NULL,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        sku_id UUID,
        job_id UUID,
        unit TEXT NOT NULL DEFAULT 'each',
        sell_cost NUMERIC(18,4) NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS invoice_counters (
        organization_id UUID NOT NULL REFERENCES organizations(id),
        key TEXT NOT NULL,
        counter INTEGER NOT NULL DEFAULT 0
        ,
        PRIMARY KEY (organization_id, key)
    );

CREATE TABLE IF NOT EXISTS credit_notes (
        id UUID PRIMARY KEY,
        credit_note_number TEXT UNIQUE NOT NULL,
        invoice_id UUID REFERENCES invoices(id),
        return_id UUID,
        billing_entity TEXT NOT NULL DEFAULT '',
        billing_entity_id UUID REFERENCES billing_entities(id),
        status TEXT NOT NULL DEFAULT 'draft',
        subtotal NUMERIC(18,2) NOT NULL DEFAULT 0,
        tax NUMERIC(18,2) NOT NULL DEFAULT 0,
        total NUMERIC(18,2) NOT NULL DEFAULT 0,
        notes TEXT,
        xero_credit_note_id TEXT,
        xero_sync_status TEXT NOT NULL DEFAULT 'pending',
        organization_id UUID REFERENCES organizations(id),
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS credit_note_line_items (
        id UUID PRIMARY KEY,
        credit_note_id UUID NOT NULL REFERENCES credit_notes(id),
        description TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL,
        amount NUMERIC(18,2) NOT NULL,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        sku_id UUID,
        unit TEXT NOT NULL DEFAULT 'each',
        sell_cost NUMERIC(18,4) NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS payments (
        id UUID PRIMARY KEY,
        invoice_id UUID REFERENCES invoices(id),
        billing_entity_id UUID REFERENCES billing_entities(id),
        amount NUMERIC(18,2) NOT NULL,
        method TEXT NOT NULL DEFAULT 'bank_transfer',
        reference TEXT NOT NULL DEFAULT '',
        payment_date TIMESTAMPTZ NOT NULL,
        notes TEXT,
        recorded_by_id UUID NOT NULL REFERENCES users(id),
        xero_payment_id TEXT,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS payment_withdrawals (
        payment_id UUID NOT NULL REFERENCES payments(id),
        withdrawal_id UUID NOT NULL REFERENCES withdrawals(id),
        PRIMARY KEY (payment_id, withdrawal_id)
    );

CREATE TABLE IF NOT EXISTS financial_ledger (
        id UUID PRIMARY KEY,
        journal_id UUID,
        account TEXT NOT NULL,
        amount NUMERIC(18,2) NOT NULL,
        quantity NUMERIC(18,4),
        unit TEXT,
        unit_cost NUMERIC(18,4),
        department TEXT,
        job_id UUID,
        billing_entity TEXT,
        billing_entity_id UUID,
        contractor_id UUID,
        vendor_name TEXT,
        sku_id UUID,
        performed_by_user_id UUID,
        reference_type TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        organization_id UUID,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

CREATE INDEX IF NOT EXISTS idx_invoices_billing ON invoices(billing_entity);

CREATE INDEX IF NOT EXISTS idx_invoices_org ON invoices(organization_id);

CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice ON invoice_line_items(invoice_id);

CREATE INDEX IF NOT EXISTS idx_cn_invoice ON credit_notes(invoice_id);

CREATE INDEX IF NOT EXISTS idx_cn_org ON credit_notes(organization_id);

CREATE INDEX IF NOT EXISTS idx_cn_status ON credit_notes(status);

CREATE INDEX IF NOT EXISTS idx_cn_line_items_cn ON credit_note_line_items(credit_note_id);

CREATE INDEX IF NOT EXISTS idx_fl_account ON financial_ledger(account);

CREATE INDEX IF NOT EXISTS idx_fl_created ON financial_ledger(created_at);

CREATE INDEX IF NOT EXISTS idx_fl_org_account ON financial_ledger(organization_id, account, created_at);

CREATE INDEX IF NOT EXISTS idx_fl_ref ON financial_ledger(reference_type, reference_id);

CREATE INDEX IF NOT EXISTS idx_fl_dept ON financial_ledger(department, account);

CREATE INDEX IF NOT EXISTS idx_fl_job ON financial_ledger(job_id, account);

CREATE INDEX IF NOT EXISTS idx_fl_entity ON financial_ledger(billing_entity, account);

CREATE INDEX IF NOT EXISTS idx_fl_journal ON financial_ledger(journal_id);

CREATE INDEX IF NOT EXISTS idx_payments_org ON payments(organization_id);

CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);

CREATE INDEX IF NOT EXISTS idx_payments_entity ON payments(billing_entity_id);

CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);

CREATE INDEX IF NOT EXISTS idx_payment_withdrawals_wid ON payment_withdrawals(withdrawal_id);

CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);

CREATE INDEX IF NOT EXISTS idx_invoices_xero_sync ON invoices(xero_sync_status, xero_invoice_id);

CREATE INDEX IF NOT EXISTS idx_cn_xero_sync ON credit_notes(xero_sync_status, xero_credit_note_id);

CREATE INDEX IF NOT EXISTS idx_invoice_withdrawals_withdrawal ON invoice_withdrawals(withdrawal_id);
