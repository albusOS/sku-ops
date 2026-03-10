"""Catalog context schema — products, departments, vendors, SKU counters."""

TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS departments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        product_count INTEGER NOT NULL DEFAULT 0,
        organization_id TEXT,
        created_at TEXT NOT NULL,
        deleted_at TEXT,
        UNIQUE(organization_id, code)
    )""",

    """CREATE TABLE IF NOT EXISTS vendors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_name TEXT NOT NULL DEFAULT '',
        email TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        product_count INTEGER NOT NULL DEFAULT 0,
        organization_id TEXT,
        created_at TEXT NOT NULL,
        deleted_at TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        quantity REAL NOT NULL DEFAULT 0,
        min_stock INTEGER NOT NULL DEFAULT 5,
        department_id TEXT NOT NULL REFERENCES departments(id),
        department_name TEXT NOT NULL DEFAULT '',
        vendor_id TEXT,
        vendor_name TEXT NOT NULL DEFAULT '',
        original_sku TEXT,
        barcode TEXT,
        vendor_barcode TEXT,
        base_unit TEXT NOT NULL DEFAULT 'each',
        sell_uom TEXT NOT NULL DEFAULT 'each',
        pack_qty INTEGER NOT NULL DEFAULT 1,
        product_group TEXT,
        organization_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        deleted_at TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS sku_counters (
        department_code TEXT PRIMARY KEY,
        counter INTEGER NOT NULL DEFAULT 0
    )""",
]

INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_departments_org ON departments(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_vendors_org ON vendors(organization_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku ON products(sku)",
    "CREATE INDEX IF NOT EXISTS idx_products_department ON products(department_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_vendor ON products(vendor_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_vendor_original_sku ON products(vendor_id, original_sku)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode) WHERE barcode IS NOT NULL AND TRIM(barcode) != ''",
    "CREATE INDEX IF NOT EXISTS idx_products_vendor_barcode ON products(vendor_barcode) WHERE vendor_barcode IS NOT NULL AND TRIM(vendor_barcode) != ''",
    "CREATE INDEX IF NOT EXISTS idx_products_org ON products(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_group ON products(product_group) WHERE product_group IS NOT NULL",
]
