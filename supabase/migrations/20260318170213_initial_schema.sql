-- Generated from legacy Python schema modules during the Supabase cutover.
-- This file is the baseline migration for fresh databases. Follow-up changes
-- must land as normal Supabase SQL migrations rather than backend schema.py edits.

create extension if not exists vector with schema extensions;

CREATE TABLE IF NOT EXISTS organizations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        company TEXT,
        billing_entity TEXT,
        billing_entity_id TEXT,
        phone TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS org_settings (
        organization_id TEXT PRIMARY KEY,
        auto_invoice BOOLEAN NOT NULL DEFAULT FALSE,
        default_tax_rate REAL NOT NULL DEFAULT 0.10,
        xero_tenant_id TEXT,
        xero_access_token TEXT,
        xero_refresh_token TEXT,
        xero_token_expiry TEXT,
        xero_sales_account_code TEXT NOT NULL DEFAULT '200',
        xero_cogs_account_code TEXT NOT NULL DEFAULT '500',
        xero_inventory_account_code TEXT NOT NULL DEFAULT '630',
        xero_ap_account_code TEXT NOT NULL DEFAULT '800',
        xero_tracking_category_id TEXT,
        xero_tax_type TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS refresh_tokens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMPTZ NOT NULL,
        revoked BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS oauth_states (
        state TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        action TEXT NOT NULL,
        resource_type TEXT,
        resource_id TEXT,
        details TEXT,
        ip_address TEXT,
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS billing_entities (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_name TEXT NOT NULL DEFAULT '',
        contact_email TEXT NOT NULL DEFAULT '',
        billing_address TEXT NOT NULL DEFAULT '',
        payment_terms TEXT NOT NULL DEFAULT 'net_30',
        xero_contact_id TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(organization_id, name)
    );

CREATE TABLE IF NOT EXISTS addresses (
        id TEXT PRIMARY KEY,
        label TEXT NOT NULL DEFAULT '',
        line1 TEXT NOT NULL DEFAULT '',
        line2 TEXT NOT NULL DEFAULT '',
        city TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL DEFAULT '',
        postal_code TEXT NOT NULL DEFAULT '',
        country TEXT NOT NULL DEFAULT 'US',
        billing_entity_id TEXT,
        job_id TEXT,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS fiscal_periods (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        closed_by_id TEXT,
        closed_at TIMESTAMPTZ,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS processed_events (
        event_id TEXT NOT NULL,
        handler_name TEXT NOT NULL,
        event_type TEXT NOT NULL,
        processed_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (event_id, handler_name)
    );

CREATE TABLE IF NOT EXISTS departments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        sku_count INTEGER NOT NULL DEFAULT 0,
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ,
        UNIQUE(organization_id, code)
    );

CREATE TABLE IF NOT EXISTS units_of_measure (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        family TEXT NOT NULL DEFAULT 'discrete',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ,
        UNIQUE(organization_id, code)
    );

CREATE TABLE IF NOT EXISTS vendors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_name TEXT NOT NULL DEFAULT '',
        email TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        category_id TEXT NOT NULL REFERENCES departments(id),
        category_name TEXT NOT NULL DEFAULT '',
        sku_count INTEGER NOT NULL DEFAULT 0,
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS skus (
        id TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        product_family_id TEXT NOT NULL REFERENCES products(id),
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        quantity REAL NOT NULL DEFAULT 0,
        min_stock INTEGER NOT NULL DEFAULT 5,
        category_id TEXT NOT NULL REFERENCES departments(id),
        category_name TEXT NOT NULL DEFAULT '',
        barcode TEXT,
        vendor_barcode TEXT,
        base_unit TEXT NOT NULL DEFAULT 'each',
        sell_uom TEXT NOT NULL DEFAULT 'each',
        pack_qty INTEGER NOT NULL DEFAULT 1,
        purchase_uom TEXT NOT NULL DEFAULT 'each',
        purchase_pack_qty INTEGER NOT NULL DEFAULT 1,
        variant_label TEXT NOT NULL DEFAULT '',
        spec TEXT NOT NULL DEFAULT '',
        grade TEXT NOT NULL DEFAULT '',
        variant_attrs TEXT NOT NULL DEFAULT '{}',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS vendor_items (
        id TEXT PRIMARY KEY,
        vendor_id TEXT NOT NULL REFERENCES vendors(id),
        sku_id TEXT NOT NULL REFERENCES skus(id),
        vendor_sku TEXT,
        vendor_name TEXT NOT NULL DEFAULT '',
        purchase_uom TEXT NOT NULL DEFAULT 'each',
        purchase_pack_qty INTEGER NOT NULL DEFAULT 1,
        cost REAL NOT NULL DEFAULT 0,
        lead_time_days INTEGER,
        moq REAL,
        is_preferred BOOLEAN NOT NULL DEFAULT FALSE,
        notes TEXT,
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ,
        UNIQUE(vendor_id, sku_id)
    );

CREATE TABLE IF NOT EXISTS sku_counters (
        department_code TEXT PRIMARY KEY,
        counter INTEGER NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS stock_transactions (
        id TEXT PRIMARY KEY,
        sku_id TEXT NOT NULL,
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
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL DEFAULT '',
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS cycle_counts (
        id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        scope TEXT,
        created_by_id TEXT NOT NULL,
        created_by_name TEXT NOT NULL DEFAULT '',
        committed_by_id TEXT,
        committed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS cycle_count_items (
        id TEXT PRIMARY KEY,
        cycle_count_id TEXT NOT NULL,
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        snapshot_qty REAL NOT NULL,
        counted_qty REAL,
        variance REAL,
        unit TEXT NOT NULL DEFAULT 'each',
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS withdrawals (
        id TEXT PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        invoice_number TEXT UNIQUE NOT NULL,
        billing_entity TEXT NOT NULL DEFAULT '',
        billing_entity_id TEXT,
        contact_name TEXT NOT NULL DEFAULT '',
        contact_email TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft',
        subtotal NUMERIC(18,2) NOT NULL,
        tax NUMERIC(18,2) NOT NULL,
        tax_rate NUMERIC(9,4) NOT NULL DEFAULT 0.0,
        total NUMERIC(18,2) NOT NULL,
        amount_credited NUMERIC(18,2) NOT NULL DEFAULT 0,
        notes TEXT,
        invoice_date TEXT,
        due_date TEXT,
        payment_terms TEXT NOT NULL DEFAULT 'net_30',
        billing_address TEXT NOT NULL DEFAULT '',
        po_reference TEXT NOT NULL DEFAULT '',
        currency TEXT NOT NULL DEFAULT 'USD',
        approved_by_id TEXT,
        approved_at TIMESTAMPTZ,
        xero_invoice_id TEXT,
        xero_cogs_journal_id TEXT,
        xero_sync_status TEXT NOT NULL DEFAULT 'pending',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        deleted_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS invoice_withdrawals (
        invoice_id TEXT NOT NULL REFERENCES invoices(id),
        withdrawal_id TEXT NOT NULL REFERENCES withdrawals(id),
        PRIMARY KEY (invoice_id, withdrawal_id)
    );

CREATE TABLE IF NOT EXISTS invoice_line_items (
        id TEXT PRIMARY KEY,
        invoice_id TEXT NOT NULL REFERENCES invoices(id),
        description TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL,
        amount NUMERIC(18,2) NOT NULL,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        sku_id TEXT,
        job_id TEXT,
        unit TEXT NOT NULL DEFAULT 'each',
        sell_cost NUMERIC(18,4) NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS invoice_counters (
        key TEXT PRIMARY KEY,
        counter INTEGER NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS credit_notes (
        id TEXT PRIMARY KEY,
        credit_note_number TEXT UNIQUE NOT NULL,
        invoice_id TEXT,
        return_id TEXT,
        billing_entity TEXT NOT NULL DEFAULT '',
        billing_entity_id TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        subtotal NUMERIC(18,2) NOT NULL DEFAULT 0,
        tax NUMERIC(18,2) NOT NULL DEFAULT 0,
        total NUMERIC(18,2) NOT NULL DEFAULT 0,
        notes TEXT,
        xero_credit_note_id TEXT,
        xero_sync_status TEXT NOT NULL DEFAULT 'pending',
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS credit_note_line_items (
        id TEXT PRIMARY KEY,
        credit_note_id TEXT NOT NULL REFERENCES credit_notes(id),
        description TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL,
        amount NUMERIC(18,2) NOT NULL,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        sku_id TEXT,
        unit TEXT NOT NULL DEFAULT 'each',
        sell_cost NUMERIC(18,4) NOT NULL DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        invoice_id TEXT,
        billing_entity_id TEXT,
        amount NUMERIC(18,2) NOT NULL,
        method TEXT NOT NULL DEFAULT 'bank_transfer',
        reference TEXT NOT NULL DEFAULT '',
        payment_date TEXT NOT NULL,
        notes TEXT,
        recorded_by_id TEXT NOT NULL,
        xero_payment_id TEXT,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS payment_withdrawals (
        payment_id TEXT NOT NULL REFERENCES payments(id),
        withdrawal_id TEXT NOT NULL REFERENCES withdrawals(id),
        PRIMARY KEY (payment_id, withdrawal_id)
    );

CREATE TABLE IF NOT EXISTS financial_ledger (
        id TEXT PRIMARY KEY,
        journal_id TEXT,
        account TEXT NOT NULL,
        amount NUMERIC(18,2) NOT NULL,
        quantity NUMERIC(18,4),
        unit TEXT,
        unit_cost NUMERIC(18,4),
        department TEXT,
        job_id TEXT,
        billing_entity TEXT,
        billing_entity_id TEXT,
        contractor_id TEXT,
        vendor_name TEXT,
        sku_id TEXT,
        performed_by_user_id TEXT,
        reference_type TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        organization_id TEXT,
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS purchase_orders (
        id TEXT PRIMARY KEY,
        vendor_id TEXT,
        vendor_name TEXT NOT NULL DEFAULT '',
        document_date TEXT,
        total REAL,
        status TEXT NOT NULL DEFAULT 'ordered',
        notes TEXT,
        created_by_id TEXT NOT NULL DEFAULT '',
        created_by_name TEXT NOT NULL DEFAULT '',
        received_at TIMESTAMPTZ,
        received_by_id TEXT,
        received_by_name TEXT,
        document_id TEXT,
        xero_bill_id TEXT,
        xero_sync_status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ,
        organization_id TEXT
    );

CREATE TABLE IF NOT EXISTS purchase_order_items (
        id TEXT PRIMARY KEY,
        po_id TEXT NOT NULL REFERENCES purchase_orders(id),
        name TEXT NOT NULL,
        original_sku TEXT,
        ordered_qty REAL NOT NULL DEFAULT 1,
        delivered_qty REAL,
        unit_price REAL NOT NULL DEFAULT 0,
        cost REAL NOT NULL DEFAULT 0,
        base_unit TEXT NOT NULL DEFAULT 'each',
        sell_uom TEXT NOT NULL DEFAULT 'each',
        pack_qty INTEGER NOT NULL DEFAULT 1,
        purchase_uom TEXT NOT NULL DEFAULT 'each',
        purchase_pack_qty INTEGER NOT NULL DEFAULT 1,
        suggested_department TEXT NOT NULL DEFAULT 'HDW',
        status TEXT NOT NULL DEFAULT 'ordered',
        sku_id TEXT,
        organization_id TEXT
    );

CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        document_type TEXT NOT NULL DEFAULT 'other',
        vendor_name TEXT,
        file_hash TEXT NOT NULL DEFAULT '',
        file_size INTEGER NOT NULL DEFAULT 0,
        mime_type TEXT NOT NULL DEFAULT '',
        parsed_data TEXT,
        po_id TEXT,
        status TEXT NOT NULL DEFAULT 'parsed',
        uploaded_by_id TEXT NOT NULL,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL DEFAULT '',
        billing_entity_id TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        service_address TEXT NOT NULL DEFAULT '',
        notes TEXT,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(organization_id, code)
    );

CREATE TABLE IF NOT EXISTS memory_artifacts (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'entity_fact',
        subject TEXT NOT NULL DEFAULT 'general',
        content TEXT NOT NULL DEFAULT '',
        tags TEXT NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ NOT NULL,
        expires_at TIMESTAMPTZ
    );

CREATE TABLE IF NOT EXISTS agent_runs (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        org_id TEXT NOT NULL,
        user_id TEXT,
        agent_name TEXT NOT NULL,
        model TEXT NOT NULL,
        mode TEXT,
        user_message TEXT,
        response_text TEXT,
        tool_calls TEXT NOT NULL DEFAULT '[]',
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        cost_usd REAL NOT NULL DEFAULT 0,
        duration_ms INTEGER NOT NULL DEFAULT 0,
        attempts INTEGER NOT NULL DEFAULT 1,
        error TEXT,
        error_kind TEXT,
        parent_run_id TEXT,
        handoff_from TEXT,
        validation_passed BOOLEAN,
        validation_failures TEXT NOT NULL DEFAULT '[]',
        validation_scores TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL
    );

CREATE TABLE IF NOT EXISTS embeddings (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        content TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        embedding vector(1536) NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);

CREATE INDEX IF NOT EXISTS idx_users_org_role ON users(organization_id, role);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_log_org ON audit_log(organization_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action, created_at);

CREATE INDEX IF NOT EXISTS idx_billing_entities_org ON billing_entities(organization_id, is_active);

CREATE INDEX IF NOT EXISTS idx_billing_entities_name ON billing_entities(organization_id, name);

CREATE INDEX IF NOT EXISTS idx_addresses_org ON addresses(organization_id);

CREATE INDEX IF NOT EXISTS idx_addresses_entity ON addresses(billing_entity_id);

CREATE INDEX IF NOT EXISTS idx_addresses_job ON addresses(job_id);

CREATE INDEX IF NOT EXISTS idx_fiscal_periods_org ON fiscal_periods(organization_id, status);

CREATE INDEX IF NOT EXISTS idx_departments_org ON departments(organization_id);

CREATE INDEX IF NOT EXISTS idx_uom_org ON units_of_measure(organization_id);

CREATE INDEX IF NOT EXISTS idx_vendors_org ON vendors(organization_id);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);

CREATE INDEX IF NOT EXISTS idx_products_org ON products(organization_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_skus_sku ON skus(sku);

CREATE INDEX IF NOT EXISTS idx_skus_product_family ON skus(product_family_id);

CREATE INDEX IF NOT EXISTS idx_skus_category ON skus(category_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_skus_barcode ON skus(barcode) WHERE barcode IS NOT NULL AND TRIM(barcode) != '';

CREATE INDEX IF NOT EXISTS idx_skus_vendor_barcode ON skus(vendor_barcode) WHERE vendor_barcode IS NOT NULL AND TRIM(vendor_barcode) != '';

CREATE INDEX IF NOT EXISTS idx_skus_org ON skus(organization_id);

CREATE INDEX IF NOT EXISTS idx_vendor_items_sku ON vendor_items(sku_id);

CREATE INDEX IF NOT EXISTS idx_vendor_items_vendor ON vendor_items(vendor_id);

CREATE INDEX IF NOT EXISTS idx_vendor_items_vendor_sku ON vendor_items(vendor_id, vendor_sku);

CREATE INDEX IF NOT EXISTS idx_vendor_items_org ON vendor_items(organization_id);

CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_transactions(sku_id);

CREATE INDEX IF NOT EXISTS idx_stock_created ON stock_transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_stock_product_created ON stock_transactions(sku_id, created_at);

CREATE INDEX IF NOT EXISTS idx_stock_transactions_org ON stock_transactions(organization_id);

CREATE INDEX IF NOT EXISTS idx_cycle_counts_org ON cycle_counts(organization_id);

CREATE INDEX IF NOT EXISTS idx_cycle_counts_status ON cycle_counts(status);

CREATE INDEX IF NOT EXISTS idx_cycle_count_items_count ON cycle_count_items(cycle_count_id);

CREATE INDEX IF NOT EXISTS idx_cycle_count_items_product ON cycle_count_items(sku_id);

CREATE INDEX IF NOT EXISTS idx_cycle_counts_org_status_created ON cycle_counts(organization_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_withdrawals_contractor ON withdrawals(contractor_id);

CREATE INDEX IF NOT EXISTS idx_withdrawals_created ON withdrawals(created_at);

CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(payment_status);

CREATE INDEX IF NOT EXISTS idx_withdrawals_billing ON withdrawals(billing_entity);

CREATE INDEX IF NOT EXISTS idx_withdrawals_org ON withdrawals(organization_id);

CREATE INDEX IF NOT EXISTS idx_material_requests_contractor ON material_requests(contractor_id);

CREATE INDEX IF NOT EXISTS idx_material_requests_status ON material_requests(status);

CREATE INDEX IF NOT EXISTS idx_material_requests_org ON material_requests(organization_id);

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

CREATE INDEX IF NOT EXISTS idx_po_org_status ON purchase_orders(organization_id, status);

CREATE INDEX IF NOT EXISTS idx_po_created ON purchase_orders(created_at);

CREATE INDEX IF NOT EXISTS idx_po_items_po ON purchase_order_items(po_id);

CREATE INDEX IF NOT EXISTS idx_po_items_status ON purchase_order_items(status);

CREATE INDEX IF NOT EXISTS idx_po_xero_sync ON purchase_orders(xero_sync_status, xero_bill_id);

CREATE INDEX IF NOT EXISTS idx_documents_org ON documents(organization_id);

CREATE INDEX IF NOT EXISTS idx_documents_po ON documents(po_id);

CREATE INDEX IF NOT EXISTS idx_documents_vendor ON documents(vendor_name);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

CREATE INDEX IF NOT EXISTS idx_jobs_org_code ON jobs(organization_id, code);

CREATE INDEX IF NOT EXISTS idx_jobs_org_status ON jobs(organization_id, status);

CREATE INDEX IF NOT EXISTS idx_memory_user ON memory_artifacts(org_id, user_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_artifacts(session_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_session ON agent_runs(session_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_org ON agent_runs(org_id, created_at);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON agent_runs(agent_name, created_at);

CREATE INDEX IF NOT EXISTS idx_agent_runs_created ON agent_runs(created_at);

CREATE INDEX IF NOT EXISTS idx_embeddings_org_type ON embeddings(org_id, entity_type);

CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(org_id, entity_type, entity_id);

CREATE OR REPLACE VIEW entity_edges AS
    -- sku → vendor (via vendor_items)
    SELECT vi.sku_id       AS source_id,
           'sku'           AS source_type,
           vi.vendor_id    AS target_id,
           'vendor'        AS target_type,
           'supplied_by'   AS relation,
           vi.organization_id AS org_id
    FROM vendor_items vi
    UNION ALL
    -- vendor → sku (reverse)
    SELECT vi.vendor_id    AS source_id,
           'vendor'        AS source_type,
           vi.sku_id       AS target_id,
           'sku'           AS target_type,
           'supplies'      AS relation,
           vi.organization_id AS org_id
    FROM vendor_items vi
    UNION ALL
    -- sku → department
    SELECT s.id            AS source_id,
           'sku'           AS source_type,
           s.category_id   AS target_id,
           'department'    AS target_type,
           'in_department' AS relation,
           s.organization_id AS org_id
    FROM skus s WHERE s.category_id IS NOT NULL
    UNION ALL
    -- po → vendor
    SELECT po.id           AS source_id,
           'po'            AS source_type,
           po.vendor_id    AS target_id,
           'vendor'        AS target_type,
           'from_vendor'   AS relation,
           po.organization_id AS org_id
    FROM purchase_orders po WHERE po.vendor_id IS NOT NULL
    UNION ALL
    -- po_item → sku
    SELECT poi.po_id       AS source_id,
           'po'            AS source_type,
           poi.sku_id  AS target_id,
           'sku'           AS target_type,
           'contains_sku'  AS relation,
           poi.organization_id AS org_id
    FROM purchase_order_items poi WHERE poi.sku_id IS NOT NULL
    UNION ALL
    -- withdrawal → job
    SELECT w.id            AS source_id,
           'withdrawal'    AS source_type,
           w.job_id        AS target_id,
           'job'           AS target_type,
           'for_job'       AS relation,
           w.organization_id AS org_id
    FROM withdrawals w WHERE w.job_id IS NOT NULL
    UNION ALL
    -- job → withdrawal (reverse)
    SELECT w.job_id        AS source_id,
           'job'           AS source_type,
           w.id            AS target_id,
           'withdrawal'    AS target_type,
           'has_withdrawal' AS relation,
           w.organization_id AS org_id
    FROM withdrawals w WHERE w.job_id IS NOT NULL
    UNION ALL
    -- withdrawal → invoice (via join table)
    SELECT iw.withdrawal_id AS source_id,
           'withdrawal'     AS source_type,
           iw.invoice_id    AS target_id,
           'invoice'        AS target_type,
           'invoiced_in'    AS relation,
           i.organization_id AS org_id
    FROM invoice_withdrawals iw
    JOIN invoices i ON i.id = iw.invoice_id
    UNION ALL
    -- invoice → withdrawal (reverse)
    SELECT iw.invoice_id    AS source_id,
           'invoice'        AS source_type,
           iw.withdrawal_id AS target_id,
           'withdrawal'     AS target_type,
           'from_withdrawal' AS relation,
           i.organization_id AS org_id
    FROM invoice_withdrawals iw
    JOIN invoices i ON i.id = iw.invoice_id
    UNION ALL
    -- invoice → billing_entity
    SELECT i.id             AS source_id,
           'invoice'        AS source_type,
           i.billing_entity_id AS target_id,
           'billing_entity' AS target_type,
           'billed_to'      AS relation,
           i.organization_id AS org_id
    FROM invoices i WHERE i.billing_entity_id IS NOT NULL
    UNION ALL
    -- invoice → payment
    SELECT p.invoice_id    AS source_id,
           'invoice'       AS source_type,
           p.id            AS target_id,
           'payment'       AS target_type,
           'has_payment'   AS relation,
           p.organization_id AS org_id
    FROM payments p WHERE p.invoice_id IS NOT NULL
    UNION ALL
    -- invoice → credit_note
    SELECT cn.invoice_id   AS source_id,
           'invoice'       AS source_type,
           cn.id           AS target_id,
           'credit_note'   AS target_type,
           'has_credit_note' AS relation,
           cn.organization_id AS org_id
    FROM credit_notes cn WHERE cn.invoice_id IS NOT NULL
    UNION ALL
    -- withdrawal_item → sku
    SELECT wi.withdrawal_id AS source_id,
           'withdrawal'     AS source_type,
           wi.sku_id        AS target_id,
           'sku'            AS target_type,
           'contains_sku'   AS relation,
           w.organization_id AS org_id
    FROM withdrawal_items wi
    JOIN withdrawals w ON w.id = wi.withdrawal_id
    WHERE wi.sku_id IS NOT NULL
    UNION ALL
    -- job → billing_entity
    SELECT j.id            AS source_id,
           'job'           AS source_type,
           j.billing_entity_id AS target_id,
           'billing_entity' AS target_type,
           'billed_to'     AS relation,
           j.organization_id AS org_id
    FROM jobs j WHERE j.billing_entity_id IS NOT NULL
    UNION ALL
    -- job → invoice (via line items)
    SELECT DISTINCT ili.job_id AS source_id,
           'job'           AS source_type,
           ili.invoice_id  AS target_id,
           'invoice'       AS target_type,
           'has_invoice'   AS relation,
           i.organization_id AS org_id
    FROM invoice_line_items ili
    JOIN invoices i ON i.id = ili.invoice_id
    WHERE ili.job_id IS NOT NULL;
