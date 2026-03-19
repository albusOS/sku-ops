"""Catalog context schema — departments, vendors, products, SKUs, vendor items, SKU counters."""

# Additive migrations — applied via ALTER TABLE IF NOT EXISTS at startup.
# Safe to run repeatedly on an existing database.
_UOM_DEFS: list[tuple[str, str, str, str]] = [
    ("uom-each", "each", "Each", "discrete"),
    ("uom-case", "case", "Case", "discrete"),
    ("uom-box", "box", "Box", "discrete"),
    ("uom-pack", "pack", "Pack", "discrete"),
    ("uom-bag", "bag", "Bag", "discrete"),
    ("uom-roll", "roll", "Roll", "discrete"),
    ("uom-kit", "kit", "Kit", "discrete"),
    ("uom-set", "set", "Set", "discrete"),
    ("uom-pair", "pair", "Pair", "discrete"),
    ("uom-bottle", "bottle", "Bottle", "discrete"),
    ("uom-can", "can", "Can", "discrete"),
    ("uom-tube", "tube", "Tube", "discrete"),
    ("uom-sheet", "sheet", "Sheet", "discrete"),
    ("uom-gallon", "gallon", "Gallon", "volume"),
    ("uom-quart", "quart", "Quart", "volume"),
    ("uom-pint", "pint", "Pint", "volume"),
    ("uom-liter", "liter", "Liter", "volume"),
    ("uom-pound", "pound", "Pound", "weight"),
    ("uom-ounce", "ounce", "Ounce", "weight"),
    ("uom-foot", "foot", "Foot", "length"),
    ("uom-inch", "inch", "Inch", "length"),
    ("uom-meter", "meter", "Meter", "length"),
    ("uom-yard", "yard", "Yard", "length"),
    ("uom-sqft", "sqft", "Square Foot", "area"),
    ("uom-bundle", "bundle", "Bundle", "discrete"),
    ("uom-pallet", "pallet", "Pallet", "discrete"),
    ("uom-slab", "slab", "Slab", "discrete"),
]


def uom_seed_sql(org_id: str) -> list[str]:
    """Generate UOM seed INSERT statements scoped to a specific organization."""
    return [
        f"""INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at)
            VALUES ('{org_id}-{uom_id}', '{code}', '{name}', '{family}', '{org_id}', NOW())
            ON CONFLICT DO NOTHING"""
        for uom_id, code, name, family in _UOM_DEFS
    ]


# Kept for backwards compat — callers that don't have org context yet
_UOM_SEED = uom_seed_sql("supply-yard")

MIGRATIONS: list[str] = []

TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS departments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        sku_count INTEGER NOT NULL DEFAULT 0,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ,
        UNIQUE(organization_id, code)
    )""",
    """CREATE TABLE IF NOT EXISTS units_of_measure (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        family TEXT NOT NULL DEFAULT 'discrete',
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ,
        UNIQUE(organization_id, code)
    )""",
    """CREATE TABLE IF NOT EXISTS vendors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_name TEXT NOT NULL DEFAULT '',
        email TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        category_id TEXT NOT NULL REFERENCES departments(id),
        category_name TEXT NOT NULL DEFAULT '',
        sku_count INTEGER NOT NULL DEFAULT 0,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS skus (
        id TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        product_family_id TEXT NOT NULL REFERENCES products(id),
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        price NUMERIC(18,4) NOT NULL,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        quantity NUMERIC(18,4) NOT NULL DEFAULT 0,
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
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS vendor_items (
        id TEXT PRIMARY KEY,
        vendor_id TEXT NOT NULL REFERENCES vendors(id),
        sku_id TEXT NOT NULL REFERENCES skus(id),
        vendor_sku TEXT,
        vendor_name TEXT NOT NULL DEFAULT '',
        purchase_uom TEXT NOT NULL DEFAULT 'each',
        purchase_pack_qty INTEGER NOT NULL DEFAULT 1,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        lead_time_days INTEGER,
        moq NUMERIC(18,4),
        is_preferred BOOLEAN NOT NULL DEFAULT FALSE,
        notes TEXT,
        organization_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ,
        UNIQUE(vendor_id, sku_id)
    )""",
    """CREATE TABLE IF NOT EXISTS sku_counters (
        department_code TEXT PRIMARY KEY,
        counter INTEGER NOT NULL DEFAULT 0
    )""",
]

INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_departments_org ON departments(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_uom_org ON units_of_measure(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_vendors_org ON vendors(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_org ON products(organization_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_skus_sku ON skus(sku)",
    "CREATE INDEX IF NOT EXISTS idx_skus_product_family ON skus(product_family_id)",
    "CREATE INDEX IF NOT EXISTS idx_skus_category ON skus(category_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_skus_barcode ON skus(barcode) WHERE barcode IS NOT NULL AND TRIM(barcode) != ''",
    "CREATE INDEX IF NOT EXISTS idx_skus_vendor_barcode ON skus(vendor_barcode) WHERE vendor_barcode IS NOT NULL AND TRIM(vendor_barcode) != ''",
    "CREATE INDEX IF NOT EXISTS idx_skus_org ON skus(organization_id)",
    "CREATE INDEX IF NOT EXISTS idx_skus_family_attrs ON skus(product_family_id) WHERE deleted_at IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_vendor_items_sku ON vendor_items(sku_id)",
    "CREATE INDEX IF NOT EXISTS idx_vendor_items_vendor ON vendor_items(vendor_id)",
    "CREATE INDEX IF NOT EXISTS idx_vendor_items_vendor_sku ON vendor_items(vendor_id, vendor_sku)",
    "CREATE INDEX IF NOT EXISTS idx_vendor_items_org ON vendor_items(organization_id)",
]
