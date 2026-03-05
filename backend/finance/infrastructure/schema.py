"""Finance context schema — invoices, credit notes, and related join/counter tables."""

TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        invoice_number TEXT UNIQUE NOT NULL,
        billing_entity TEXT NOT NULL DEFAULT '',
        contact_name TEXT NOT NULL DEFAULT '',
        contact_email TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft',
        subtotal REAL NOT NULL,
        tax REAL NOT NULL,
        total REAL NOT NULL,
        notes TEXT,
        xero_invoice_id TEXT,
        organization_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS invoice_withdrawals (
        invoice_id TEXT NOT NULL REFERENCES invoices(id),
        withdrawal_id TEXT NOT NULL REFERENCES withdrawals(id),
        PRIMARY KEY (invoice_id, withdrawal_id)
    )""",

    """CREATE TABLE IF NOT EXISTS invoice_line_items (
        id TEXT PRIMARY KEY,
        invoice_id TEXT NOT NULL REFERENCES invoices(id),
        description TEXT NOT NULL DEFAULT '',
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        amount REAL NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        product_id TEXT,
        job_id TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS invoice_counters (
        key TEXT PRIMARY KEY,
        counter INTEGER NOT NULL DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS credit_notes (
        id TEXT PRIMARY KEY,
        credit_note_number TEXT UNIQUE NOT NULL,
        invoice_id TEXT,
        return_id TEXT,
        billing_entity TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft',
        subtotal REAL NOT NULL DEFAULT 0,
        tax REAL NOT NULL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        notes TEXT,
        xero_credit_note_id TEXT,
        organization_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",

    """CREATE TABLE IF NOT EXISTS credit_note_line_items (
        id TEXT PRIMARY KEY,
        credit_note_id TEXT NOT NULL REFERENCES credit_notes(id),
        description TEXT NOT NULL DEFAULT '',
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        amount REAL NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        product_id TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS financial_ledger (
        id TEXT PRIMARY KEY,
        account TEXT NOT NULL,
        amount REAL NOT NULL,
        department TEXT,
        job_id TEXT,
        billing_entity TEXT,
        contractor_id TEXT,
        vendor_name TEXT,
        product_id TEXT,
        reference_type TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        organization_id TEXT,
        created_at TEXT NOT NULL
    )""",
]

INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_billing ON invoices(billing_entity)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_org ON invoices(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice ON invoice_line_items(invoice_id)",
    "CREATE INDEX IF NOT EXISTS idx_cn_invoice ON credit_notes(invoice_id)",
    "CREATE INDEX IF NOT EXISTS idx_cn_org ON credit_notes(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_cn_status ON credit_notes(status)",
    "CREATE INDEX IF NOT EXISTS idx_cn_line_items_cn ON credit_note_line_items(credit_note_id)",
    "CREATE INDEX IF NOT EXISTS idx_fl_account ON financial_ledger(account)",
    "CREATE INDEX IF NOT EXISTS idx_fl_created ON financial_ledger(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_fl_org_account ON financial_ledger(organization_id, account, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_fl_ref ON financial_ledger(reference_type, reference_id)",
    "CREATE INDEX IF NOT EXISTS idx_fl_dept ON financial_ledger(department, account)",
    "CREATE INDEX IF NOT EXISTS idx_fl_job ON financial_ledger(job_id, account)",
    "CREATE INDEX IF NOT EXISTS idx_fl_entity ON financial_ledger(billing_entity, account)",
]
