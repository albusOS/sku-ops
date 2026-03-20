"""Seed both local and Supabase databases with clean, holistic demo data.

Covers every bounded context with realistic hardware-store data:
  - 58 departments, 5 vendors, 3 billing entities, 5 jobs
  - 30 product families, ~60 SKUs across 12 departments
  - 4 purchase orders (various states)
  - 8 withdrawals (unpaid → paid lifecycle)
  - 2 material requests (pending + processed)
  - 1 return with credit note
  - 5 invoices (draft, approved, paid, overdue)
  - 2 payments
  - Financial ledger entries
  - Stock transactions
  - 1 cycle count (committed)

Usage:
    # Wipe + seed local dev DB
    PYTHONPATH=backend:. uv run python -m devtools.scripts.seed_demo --target local

    # Wipe + seed Supabase prod DB
    PYTHONPATH=backend:. uv run python -m devtools.scripts.seed_demo --target supabase

    # Seed both
    PYTHONPATH=backend:. uv run python -m devtools.scripts.seed_demo --target both
"""

import argparse
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

NOW = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)

# ── Helpers ──────────────────────────────────────────────────────────────────


def uid() -> str:
    return str(uuid.uuid4())


def ts(dt: datetime) -> str:
    return dt.isoformat()


def ago(**kw) -> str:
    return ts(NOW - timedelta(**kw))


def future(**kw) -> str:
    return ts(NOW + timedelta(**kw))


# ── IDs (stable so FKs work) ────────────────────────────────────────────────

ORG = "supply-yard"

# Users
ADMIN_ID = uid()
CONTRACTOR_MIKE_ID = uid()
CONTRACTOR_SARAH_ID = uid()

# Vendors
V_EMERY = uid()
V_SHERWIN = uid()
V_HOMEDEPOT = uid()
V_AMAZON = uid()
V_DECKEXP = uid()

# Billing entities
BE_RIVRIDGE = uid()
BE_SUMMIT = uid()
BE_COASTAL = uid()

# Jobs
J_KITCHEN_1 = uid()
J_BATH_2 = uid()
J_DECK_3 = uid()
J_ELECTRIC_4 = uid()
J_PAINT_5 = uid()

# Departments (we need IDs for FK refs — these match the provision script's pattern)
DEPT_IDS = {}  # code → id, populated at insert time


def build_statements() -> list[str]:
    """Return ordered SQL statements for the full demo dataset."""
    stmts: list[str] = []

    def q(s: str) -> str:
        """Escape single quotes for SQL."""
        return s.replace("'", "''")

    # ── 1. Organization ──────────────────────────────────────────────────
    stmts.append(
        f"INSERT INTO organizations (id, name, slug, created_at) "
        f"VALUES ('{ORG}', 'Supply Yard', 'supply-yard', '{ago(days=365)}') "
        f"ON CONFLICT (id) DO NOTHING"
    )

    # ── 2. Org Settings ──────────────────────────────────────────────────
    stmts.append(
        f"INSERT INTO org_settings (organization_id, auto_invoice, default_tax_rate) "
        f"VALUES ('{ORG}', FALSE, 0.10) "
        f"ON CONFLICT (organization_id) DO NOTHING"
    )

    # ── 3. Departments ───────────────────────────────────────────────────
    from devtools.scripts.company import DEPARTMENTS

    for dept in DEPARTMENTS:
        did = uid()
        DEPT_IDS[dept.code] = did
        stmts.append(
            f"INSERT INTO departments (id, name, code, description, sku_count, organization_id, created_at) "
            f"VALUES ('{did}', '{q(dept.name)}', '{dept.code}', '{q(dept.description)}', 0, '{ORG}', '{ago(days=365)}') "
            f"ON CONFLICT (organization_id, code) DO NOTHING"
        )

    # ── 4. Users ─────────────────────────────────────────────────────────
    # bcrypt hash of "demo123"
    demo_hash = "$2b$12$LJ3m4ys3Lg8U0cOqXn6xAOQzf3LYwnBR6FmPXjBZ5VQ9IJ6Lqt3jC"

    users = [
        (ADMIN_ID, "admin@supplyyard.com", demo_hash, "Marcus Chen", "admin", "", "", ""),
        (
            CONTRACTOR_MIKE_ID,
            "mike@rivridge.com",
            demo_hash,
            "Mike Torres",
            "contractor",
            "Riva Ridge Property Mgmt",
            "Riva Ridge Property Mgmt",
            "",
        ),
        (
            CONTRACTOR_SARAH_ID,
            "sarah@summitpm.com",
            demo_hash,
            "Sarah Okafor",
            "contractor",
            "Summit Property Group",
            "Summit Property Group",
            "",
        ),
    ]
    for u in users:
        stmts.append(
            f"INSERT INTO users (id, email, password, name, role, company, billing_entity, phone, is_active, organization_id, created_at) "
            f"VALUES ('{u[0]}', '{u[1]}', '{u[2]}', '{q(u[3])}', '{u[4]}', '{q(u[5])}', '{q(u[6])}', '{u[7]}', TRUE, '{ORG}', '{ago(days=90)}') "
            f"ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role"
        )

    # ── 5. Vendors ───────────────────────────────────────────────────────
    vendors = [
        (
            V_EMERY,
            "Emery Jensen Distribution",
            "Pat Emery",
            "orders@emeryjensen.com",
            "555-0101",
            "2400 Industrial Pkwy, Elkhart IN",
        ),
        (
            V_SHERWIN,
            "Sherwin-Williams",
            "Alex Rivera",
            "pro@sherwin.com",
            "555-0102",
            "101 W Prospect Ave, Cleveland OH",
        ),
        (
            V_HOMEDEPOT,
            "The Home Depot Pro",
            "Jordan Lee",
            "pro-desk@homedepot.com",
            "555-0103",
            "2455 Paces Ferry Rd, Atlanta GA",
        ),
        (V_AMAZON, "Amazon Business", "", "business@amazon.com", "", ""),
        (
            V_DECKEXP,
            "Deck Expressions",
            "Tom Nguyen",
            "tom@deckexpressions.com",
            "555-0105",
            "834 Lumber Ln, Portland OR",
        ),
    ]
    for v in vendors:
        stmts.append(
            f"INSERT INTO vendors (id, name, contact_name, email, phone, address, organization_id, created_at) "
            f"VALUES ('{v[0]}', '{q(v[1])}', '{q(v[2])}', '{v[3]}', '{v[4]}', '{q(v[5])}', '{ORG}', '{ago(days=180)}') "
            f"ON CONFLICT DO NOTHING"
        )

    # ── 6. Billing Entities ──────────────────────────────────────────────
    billing_entities = [
        (
            BE_RIVRIDGE,
            "Riva Ridge Property Mgmt",
            "Mike Torres",
            "mike@rivridge.com",
            "1200 Mountain View Dr, Ste 400, Vail CO 81657",
            "net_30",
        ),
        (
            BE_SUMMIT,
            "Summit Property Group",
            "Sarah Okafor",
            "sarah@summitpm.com",
            "890 Summit Blvd, Ste 12, Aspen CO 81611",
            "net_30",
        ),
        (
            BE_COASTAL,
            "Coastal Living Rentals",
            "Jenna Park",
            "jenna@coastalrentals.com",
            "45 Ocean Ave, Ste 3, Monterey CA 93940",
            "net_15",
        ),
    ]
    for be in billing_entities:
        stmts.append(
            f"INSERT INTO billing_entities (id, name, contact_name, contact_email, billing_address, payment_terms, is_active, organization_id, created_at, updated_at) "
            f"VALUES ('{be[0]}', '{q(be[1])}', '{q(be[2])}', '{be[3]}', '{q(be[4])}', '{be[5]}', TRUE, '{ORG}', '{ago(days=120)}', '{ago(days=120)}') "
            f"ON CONFLICT (organization_id, name) DO NOTHING"
        )

    # ── 7. Jobs ──────────────────────────────────────────────────────────
    jobs = [
        (
            J_KITCHEN_1,
            "RR-2026-001",
            "Riva Ridge Unit 4A Kitchen Remodel",
            BE_RIVRIDGE,
            "active",
            "1200 Mountain View Dr, Unit 4A, Vail CO",
        ),
        (
            J_BATH_2,
            "RR-2026-002",
            "Riva Ridge Unit 7B Bathroom Renovation",
            BE_RIVRIDGE,
            "active",
            "1200 Mountain View Dr, Unit 7B, Vail CO",
        ),
        (
            J_DECK_3,
            "SP-2026-001",
            "Summit Pines Deck Replacement",
            BE_SUMMIT,
            "active",
            "345 Pine Ridge Rd, Aspen CO",
        ),
        (
            J_ELECTRIC_4,
            "SP-2026-002",
            "Summit Pines Electrical Upgrade",
            BE_SUMMIT,
            "active",
            "345 Pine Ridge Rd, Aspen CO",
        ),
        (
            J_PAINT_5,
            "CL-2026-001",
            "Coastal Exterior Repaint",
            BE_COASTAL,
            "active",
            "45 Ocean Ave, Monterey CA",
        ),
    ]
    for j in jobs:
        stmts.append(
            f"INSERT INTO jobs (id, code, name, billing_entity_id, status, service_address, organization_id, created_at, updated_at) "
            f"VALUES ('{j[0]}', '{j[1]}', '{q(j[2])}', '{j[3]}', '{j[4]}', '{q(j[5])}', '{ORG}', '{ago(days=30)}', '{ago(days=30)}') "
            f"ON CONFLICT (organization_id, code) DO NOTHING"
        )

    # ── 8. Addresses ─────────────────────────────────────────────────────
    addresses = [
        (
            uid(),
            "Riva Ridge Office",
            "1200 Mountain View Dr",
            "Ste 400",
            "Vail",
            "CO",
            "81657",
            BE_RIVRIDGE,
            None,
        ),
        (
            uid(),
            "Summit Property Office",
            "890 Summit Blvd",
            "Ste 12",
            "Aspen",
            "CO",
            "81611",
            BE_SUMMIT,
            None,
        ),
        (
            uid(),
            "Coastal Rentals",
            "45 Ocean Ave",
            "Ste 3",
            "Monterey",
            "CA",
            "93940",
            BE_COASTAL,
            None,
        ),
        (
            uid(),
            "Kitchen Remodel Site",
            "1200 Mountain View Dr",
            "Unit 4A",
            "Vail",
            "CO",
            "81657",
            None,
            J_KITCHEN_1,
        ),
        (
            uid(),
            "Deck Replacement Site",
            "345 Pine Ridge Rd",
            "",
            "Aspen",
            "CO",
            "81611",
            None,
            J_DECK_3,
        ),
    ]
    for a in addresses:
        be_val = f"'{a[7]}'" if a[7] else "NULL"
        job_val = f"'{a[8]}'" if a[8] else "NULL"
        stmts.append(
            f"INSERT INTO addresses (id, label, line1, line2, city, state, postal_code, country, billing_entity_id, job_id, organization_id, created_at) "
            f"VALUES ('{a[0]}', '{q(a[1])}', '{q(a[2])}', '{q(a[3])}', '{a[4]}', '{a[5]}', '{a[6]}', 'US', {be_val}, {job_val}, '{ORG}', '{ago(days=120)}') "
            f"ON CONFLICT DO NOTHING"
        )

    # ── 9. Product Families & SKUs ───────────────────────────────────────
    # Each tuple: (family_id, family_name, dept_code, skus_list)
    # skus_list: [(sku_id, sku_code, name, price, cost, qty, base_unit, sell_uom, variant_attrs, barcode)]

    catalog = _build_catalog()
    for fam in catalog:
        fam_id, fam_name, dept_code, skus = fam
        dept_id = DEPT_IDS[dept_code]
        stmts.append(
            f"INSERT INTO products (id, name, description, category_id, category_name, sku_count, organization_id, created_at, updated_at) "
            f"VALUES ('{fam_id}', '{q(fam_name)}', '', '{dept_id}', '{dept_code}', {len(skus)}, '{ORG}', '{ago(days=180)}', '{ago(days=180)}') "
            f"ON CONFLICT DO NOTHING"
        )
        for s in skus:
            (
                s_id,
                s_sku,
                s_name,
                s_price,
                s_cost,
                s_qty,
                s_base_unit,
                s_sell_uom,
                s_variant_attrs,
                s_barcode,
            ) = s
            bc = f"'{s_barcode}'" if s_barcode else "NULL"
            stmts.append(
                f"INSERT INTO skus (id, sku, product_family_id, name, description, price, cost, quantity, min_stock, "
                f"category_id, category_name, barcode, base_unit, sell_uom, pack_qty, purchase_uom, purchase_pack_qty, "
                f"variant_label, spec, grade, variant_attrs, organization_id, created_at, updated_at) "
                f"VALUES ('{s_id}', '{s_sku}', '{fam_id}', '{q(s_name)}', '', {s_price}, {s_cost}, {s_qty}, 5, "
                f"'{dept_id}', '{dept_code}', {bc}, '{s_base_unit}', '{s_sell_uom}', 1, 'each', 1, "
                f"'', '', '', '{s_variant_attrs}', '{ORG}', '{ago(days=180)}', '{ago(days=1)}') "
                f"ON CONFLICT DO NOTHING"
            )

    # ── 10. Vendor Items ─────────────────────────────────────────────────
    vendor_links = _build_vendor_items(catalog)
    for vl in vendor_links:
        stmts.append(
            f"INSERT INTO vendor_items (id, vendor_id, sku_id, vendor_sku, vendor_name, purchase_uom, purchase_pack_qty, "
            f"cost, lead_time_days, moq, is_preferred, organization_id, created_at, updated_at) "
            f"VALUES ('{vl[0]}', '{vl[1]}', '{vl[2]}', '{vl[3]}', '{q(vl[4])}', 'each', 1, "
            f"{vl[5]}, {vl[6]}, 1, {'TRUE' if vl[7] else 'FALSE'}, '{ORG}', '{ago(days=90)}', '{ago(days=90)}') "
            f"ON CONFLICT (vendor_id, sku_id) DO NOTHING"
        )

    # ── 11. SKU Counters ─────────────────────────────────────────────────
    counter_map: dict[str, int] = {}
    for fam in catalog:
        dept_code = fam[2]
        counter_map[dept_code] = counter_map.get(dept_code, 0) + len(fam[3])
    for code, count in counter_map.items():
        stmts.append(
            f"INSERT INTO sku_counters (department_code, counter) "
            f"VALUES ('{code}', {count}) "
            f"ON CONFLICT (department_code) DO UPDATE SET counter = EXCLUDED.counter"
        )

    # ── 12. Purchase Orders ──────────────────────────────────────────────
    po_data = _build_purchase_orders(catalog)
    stmts.extend(po_data["orders"])
    stmts.extend(po_data["items"])

    # ── 13. Withdrawals ──────────────────────────────────────────────────
    wd_data = _build_withdrawals(catalog)
    stmts.extend(wd_data["withdrawals"])
    stmts.extend(wd_data["items"])

    # ── 14. Material Requests ────────────────────────────────────────────
    mr_data = _build_material_requests(catalog, wd_data)
    stmts.extend(mr_data["requests"])
    stmts.extend(mr_data["items"])

    # ── 15. Invoices ─────────────────────────────────────────────────────
    inv_data = _build_invoices(wd_data)
    stmts.extend(inv_data["stmts"])

    # ── 16. Payments ─────────────────────────────────────────────────────
    pay_data = _build_payments(inv_data)
    stmts.extend(pay_data)

    # ── 17. Returns + Credit Notes ───────────────────────────────────────
    ret_data = _build_returns(wd_data, inv_data)
    stmts.extend(ret_data["returns"])
    stmts.extend(ret_data["items"])

    # ── 18. Stock Transactions ───────────────────────────────────────────
    stx_data = _build_stock_transactions(catalog, wd_data, po_data)
    stmts.extend(stx_data)

    # ── 19. Financial Ledger ─────────────────────────────────────────────
    ledger_data = _build_financial_ledger(wd_data, po_data, inv_data)
    stmts.extend(ledger_data)

    # ── 20. Cycle Count ──────────────────────────────────────────────────
    cc_data = _build_cycle_count(catalog)
    stmts.extend(cc_data)

    # ── 21. Fiscal Period ────────────────────────────────────────────────
    fp_id = uid()
    stmts.append(
        f"INSERT INTO fiscal_periods (id, name, start_date, end_date, status, organization_id, created_at) "
        f"VALUES ('{fp_id}', 'Q1 2026', '2026-01-01', '2026-03-31', 'open', '{ORG}', '{ago(days=76)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # ── 22. Invoice Counter ──────────────────────────────────────────────
    stmts.append(
        "INSERT INTO invoice_counters (key, counter) VALUES ('invoice_number', 5) "
        "ON CONFLICT (key) DO UPDATE SET counter = EXCLUDED.counter"
    )

    return stmts


# ── Catalog Data ─────────────────────────────────────────────────────────────


def _build_catalog():
    """Return list of (family_id, family_name, dept_code, [(sku_id, sku, name, price, cost, qty, base_unit, sell_uom, variant_attrs, barcode)])."""
    catalog = []

    def fam(name, dept, skus):
        fid = uid()
        catalog.append((fid, name, dept, skus))

    def sku(
        dept, slug, seq, name, price, cost, qty, unit="each", uom="each", attrs="{}", barcode=None
    ):
        return (
            uid(),
            f"{dept}-{slug}-{seq:02d}",
            name,
            price,
            cost,
            qty,
            unit,
            uom,
            attrs,
            barcode,
        )

    # ── Plumbing ─────────────────────────────────────────────────────────
    fam(
        "PEX Tubing",
        "PLP",
        [
            sku(
                "PLP",
                "PEXTUBE",
                1,
                'PEX-A Tubing 1/2" x 100ft Red',
                42.99,
                24.50,
                15,
                "foot",
                "100ft_coil",
                '{"diameter": "1/2\\"", "color": "red", "length": "100ft"}',
                "0012345000011",
            ),
            sku(
                "PLP",
                "PEXTUBE",
                2,
                'PEX-A Tubing 1/2" x 100ft Blue',
                42.99,
                24.50,
                12,
                "foot",
                "100ft_coil",
                '{"diameter": "1/2\\"", "color": "blue", "length": "100ft"}',
                "0012345000012",
            ),
            sku(
                "PLP",
                "PEXTUBE",
                3,
                'PEX-A Tubing 3/4" x 100ft Red',
                64.99,
                38.00,
                8,
                "foot",
                "100ft_coil",
                '{"diameter": "3/4\\"", "color": "red", "length": "100ft"}',
                "0012345000013",
            ),
        ],
    )
    fam(
        "SharkBite Push Fittings",
        "PLF",
        [
            sku(
                "PLF",
                "SHRKBT90",
                1,
                'SharkBite 1/2" 90-Degree Elbow',
                8.49,
                4.80,
                45,
                "each",
                "each",
                '{"size": "1/2\\"", "type": "90-elbow"}',
                "0012345000021",
            ),
            sku(
                "PLF",
                "SHRKBTT",
                1,
                'SharkBite 1/2" Tee',
                9.99,
                5.60,
                38,
                "each",
                "each",
                '{"size": "1/2\\"", "type": "tee"}',
                "0012345000022",
            ),
            sku(
                "PLF",
                "SHRKBTCP",
                1,
                'SharkBite 1/2" Coupling',
                5.99,
                3.40,
                60,
                "each",
                "each",
                '{"size": "1/2\\"", "type": "coupling"}',
                "0012345000023",
            ),
        ],
    )

    # ── Electrical ───────────────────────────────────────────────────────
    fam(
        "Romex NM-B Wire",
        "ELW",
        [
            sku(
                "ELW",
                "ROMEX14",
                1,
                "Romex 14/2 NM-B 250ft",
                89.99,
                52.00,
                6,
                "foot",
                "250ft_spool",
                '{"gauge": "14/2", "length": "250ft"}',
                "0012345000031",
            ),
            sku(
                "ELW",
                "ROMEX12",
                1,
                "Romex 12/2 NM-B 250ft",
                119.99,
                72.00,
                4,
                "foot",
                "250ft_spool",
                '{"gauge": "12/2", "length": "250ft"}',
                "0012345000032",
            ),
        ],
    )
    fam(
        "Leviton Decora Switch",
        "ELE",
        [
            sku(
                "ELE",
                "DECORASW",
                1,
                "Leviton Decora 15A Switch White",
                3.29,
                1.60,
                80,
                "each",
                "each",
                '{"amperage": "15A", "color": "white"}',
                "0012345000041",
            ),
            sku(
                "ELE",
                "DECORASW",
                2,
                "Leviton Decora 15A Switch Ivory",
                3.29,
                1.60,
                40,
                "each",
                "each",
                '{"amperage": "15A", "color": "ivory"}',
                "0012345000042",
            ),
        ],
    )
    fam(
        "Leviton GFCI Outlet",
        "ELE",
        [
            sku(
                "ELE",
                "GFCI15",
                1,
                "Leviton GFCI 15A Outlet White",
                18.99,
                10.50,
                25,
                "each",
                "each",
                '{"amperage": "15A", "color": "white"}',
                "0012345000051",
            ),
        ],
    )

    # ── Paint ────────────────────────────────────────────────────────────
    fam(
        "Sherwin-Williams SuperPaint",
        "PNT",
        [
            sku(
                "PNT",
                "SWSUPER",
                1,
                "SW SuperPaint Interior Flat - Gallon",
                52.99,
                32.00,
                20,
                "gallon",
                "gallon",
                '{"finish": "flat", "type": "interior"}',
                "0012345000061",
            ),
            sku(
                "PNT",
                "SWSUPER",
                2,
                "SW SuperPaint Interior Satin - Gallon",
                56.99,
                34.00,
                18,
                "gallon",
                "gallon",
                '{"finish": "satin", "type": "interior"}',
                "0012345000062",
            ),
            sku(
                "PNT",
                "SWSUPER",
                3,
                "SW SuperPaint Exterior Flat - Gallon",
                58.99,
                36.00,
                12,
                "gallon",
                "gallon",
                '{"finish": "flat", "type": "exterior"}',
                "0012345000063",
            ),
        ],
    )
    fam(
        "Paint Rollers",
        "PNS",
        [
            sku(
                "PNS",
                "ROLLER9",
                1,
                'Purdy White Dove 9" Roller Cover 3/8" Nap',
                8.99,
                4.20,
                30,
                "each",
                "each",
                '{"size": "9\\"", "nap": "3/8\\""}',
                "0012345000071",
            ),
            sku(
                "PNS",
                "ROLLER9",
                2,
                'Purdy White Dove 9" Roller Cover 1/2" Nap',
                9.49,
                4.50,
                25,
                "each",
                "each",
                '{"size": "9\\"", "nap": "1/2\\""}',
                "0012345000072",
            ),
        ],
    )

    # ── Building Materials ───────────────────────────────────────────────
    fam(
        "Drywall Sheet",
        "BLD",
        [
            sku(
                "BLD",
                "DRYWALL",
                1,
                '1/2" x 4x8 Drywall Sheet',
                14.99,
                8.20,
                40,
                "sheet",
                "sheet",
                '{"thickness": "1/2\\"", "size": "4x8"}',
                "0012345000081",
            ),
            sku(
                "BLD",
                "DRYWALL",
                2,
                '5/8" x 4x8 Drywall Sheet',
                17.49,
                9.80,
                25,
                "sheet",
                "sheet",
                '{"thickness": "5/8\\"", "size": "4x8"}',
                "0012345000082",
            ),
        ],
    )
    fam(
        "Concrete Mix",
        "CON",
        [
            sku(
                "CON",
                "QUIKSET",
                1,
                "Quikrete Fast-Setting Concrete 50lb",
                7.49,
                4.10,
                35,
                "bag",
                "bag",
                '{"weight": "50lb"}',
                "0012345000091",
            ),
            sku(
                "CON",
                "QUIKSET",
                2,
                "Quikrete Fast-Setting Concrete 80lb",
                9.99,
                5.60,
                20,
                "bag",
                "bag",
                '{"weight": "80lb"}',
                "0012345000092",
            ),
        ],
    )

    # ── Lumber ───────────────────────────────────────────────────────────
    fam(
        "Dimensional Lumber",
        "LUM",
        [
            sku(
                "LUM",
                "STUDS2X4",
                1,
                "2x4x8 SPF Stud",
                4.29,
                2.40,
                120,
                "each",
                "each",
                '{"size": "2x4", "length": "8ft"}',
                "0012345000101",
            ),
            sku(
                "LUM",
                "STUDS2X4",
                2,
                "2x4x10 SPF Stud",
                5.99,
                3.40,
                60,
                "each",
                "each",
                '{"size": "2x4", "length": "10ft"}',
                "0012345000102",
            ),
            sku(
                "LUM",
                "STUDS2X6",
                1,
                "2x6x8 SPF",
                6.99,
                4.00,
                50,
                "each",
                "each",
                '{"size": "2x6", "length": "8ft"}',
                "0012345000103",
            ),
        ],
    )
    fam(
        "Pressure Treated Deck Boards",
        "LUM",
        [
            sku(
                "LUM",
                "PTDECK",
                1,
                "5/4x6x12 PT Deck Board",
                14.99,
                8.80,
                80,
                "each",
                "each",
                '{"size": "5/4x6", "length": "12ft"}',
                "0012345000111",
            ),
            sku(
                "LUM",
                "PTDECK",
                2,
                "5/4x6x16 PT Deck Board",
                19.99,
                11.60,
                40,
                "each",
                "each",
                '{"size": "5/4x6", "length": "16ft"}',
                "0012345000112",
            ),
        ],
    )

    # ── Fasteners ────────────────────────────────────────────────────────
    fam(
        "Deck Screws",
        "FAS",
        [
            sku(
                "FAS",
                "DECKSCR",
                1,
                'GRK #8 x 2-1/2" Deck Screw 100pk',
                14.99,
                7.80,
                50,
                "box",
                "box",
                '{"size": "#8 x 2-1/2\\"", "count": "100"}',
                "0012345000121",
            ),
            sku(
                "FAS",
                "DECKSCR",
                2,
                'GRK #8 x 3" Deck Screw 100pk',
                16.49,
                8.60,
                35,
                "box",
                "box",
                '{"size": "#8 x 3\\"", "count": "100"}',
                "0012345000122",
            ),
        ],
    )
    fam(
        "Drywall Screws",
        "FAS",
        [
            sku(
                "FAS",
                "DRYSCR",
                1,
                '#6 x 1-5/8" Drywall Screw 1lb',
                5.99,
                2.80,
                40,
                "box",
                "box",
                '{"size": "#6 x 1-5/8\\"", "weight": "1lb"}',
                "0012345000131",
            ),
        ],
    )

    # ── HVAC ─────────────────────────────────────────────────────────────
    fam(
        "Furnace Filters",
        "HVF",
        [
            sku(
                "HVF",
                "FILTER16",
                1,
                "16x20x1 MERV 8 Pleated Filter",
                4.99,
                2.20,
                60,
                "each",
                "each",
                '{"size": "16x20x1", "merv": "8"}',
                "0012345000141",
            ),
            sku(
                "HVF",
                "FILTER20",
                1,
                "20x25x1 MERV 11 Pleated Filter",
                7.99,
                3.80,
                40,
                "each",
                "each",
                '{"size": "20x25x1", "merv": "11"}',
                "0012345000142",
            ),
        ],
    )

    # ── Adhesives ────────────────────────────────────────────────────────
    fam(
        "Construction Adhesive",
        "ADH",
        [
            sku(
                "ADH",
                "LIQNAIL",
                1,
                "Liquid Nails Heavy Duty 10oz",
                5.49,
                2.80,
                35,
                "tube",
                "tube",
                '{"volume": "10oz"}',
                "0012345000151",
            ),
            sku(
                "ADH",
                "GORILL",
                1,
                "Gorilla Construction Adhesive 9oz",
                6.99,
                3.60,
                20,
                "tube",
                "tube",
                '{"volume": "9oz"}',
                "0012345000152",
            ),
        ],
    )

    # ── Drywall ──────────────────────────────────────────────────────────
    fam(
        "Joint Compound",
        "DRM",
        [
            sku(
                "DRM",
                "JNTCMPD",
                1,
                "USG Plus 3 Joint Compound 4.5gal",
                18.99,
                10.40,
                15,
                "bucket",
                "bucket",
                '{"weight": "4.5gal"}',
                "0012345000161",
            ),
        ],
    )
    fam(
        "Drywall Tape",
        "DRS",
        [
            sku(
                "DRS",
                "DRYTAPE",
                1,
                "FibaTape Mesh Drywall Tape 300ft",
                6.99,
                3.20,
                25,
                "roll",
                "roll",
                '{"length": "300ft"}',
                "0012345000171",
            ),
        ],
    )

    # ── Safety ───────────────────────────────────────────────────────────
    fam(
        "Smoke Detectors",
        "SAF",
        [
            sku(
                "SAF",
                "KIDDESM",
                1,
                "Kidde Hardwired Smoke + CO Detector",
                42.99,
                28.00,
                18,
                "each",
                "each",
                "{}",
                "0012345000181",
            ),
        ],
    )

    # ── Roofing ──────────────────────────────────────────────────────────
    fam(
        "Roofing Shingles",
        "ROF",
        [
            sku(
                "ROF",
                "ARCHTAB",
                1,
                "GAF Timberline Architectural Shingle Bundle",
                34.99,
                22.00,
                25,
                "bundle",
                "bundle",
                '{"style": "architectural"}',
                "0012345000191",
            ),
        ],
    )

    # ── Hand Tools ───────────────────────────────────────────────────────
    fam(
        "Hammers",
        "HTL",
        [
            sku(
                "HTL",
                "FRAMHAM",
                1,
                "Estwing 22oz Framing Hammer",
                34.99,
                19.00,
                10,
                "each",
                "each",
                '{"weight": "22oz"}',
                "0012345000201",
            ),
        ],
    )

    # ── Cleaning ─────────────────────────────────────────────────────────
    fam(
        "Cleanup Supplies",
        "CLN",
        [
            sku(
                "CLN",
                "PREPWIPE",
                1,
                "Sherwin-Williams Prep & Cleanup Wipes",
                9.99,
                5.20,
                30,
                "pack",
                "pack",
                "{}",
                "0012345000211",
            ),
        ],
    )

    # ── Locks ────────────────────────────────────────────────────────────
    fam(
        "Deadbolts",
        "LOK",
        [
            sku(
                "LOK",
                "KWIKDBL",
                1,
                "Kwikset Deadbolt Satin Nickel",
                29.99,
                16.00,
                12,
                "each",
                "each",
                '{"finish": "satin nickel"}',
                "0012345000221",
            ),
            sku(
                "LOK",
                "KWIKDBL",
                2,
                "Kwikset Deadbolt Oil-Rubbed Bronze",
                32.99,
                18.00,
                8,
                "each",
                "each",
                '{"finish": "oil-rubbed bronze"}',
                "0012345000222",
            ),
        ],
    )

    # ── Insulation ───────────────────────────────────────────────────────
    fam(
        "Fiberglass Insulation",
        "INS",
        [
            sku(
                "INS",
                "OWENR15",
                1,
                'Owens Corning R-15 3.5" x 15" x 93" 8-pack',
                49.99,
                28.00,
                20,
                "pack",
                "pack",
                '{"r_value": "R-15"}',
                "0012345000231",
            ),
        ],
    )

    # ── Flooring ─────────────────────────────────────────────────────────
    fam(
        "LVP Flooring",
        "FLO",
        [
            sku(
                "FLO",
                "LVPOAK",
                1,
                "LifeProof Sterling Oak LVP 20.06sqft",
                42.99,
                24.00,
                30,
                "box",
                "box",
                '{"style": "sterling oak", "sqft": "20.06"}',
                "0012345000241",
            ),
        ],
    )

    return catalog


def _build_vendor_items(catalog):
    """Build vendor → SKU links. Returns list of tuples."""
    links = []
    # Map dept codes to preferred vendors
    vendor_map = {
        "PLP": V_HOMEDEPOT,
        "PLF": V_HOMEDEPOT,
        "ELW": V_HOMEDEPOT,
        "ELE": V_HOMEDEPOT,
        "PNT": V_SHERWIN,
        "PNS": V_SHERWIN,
        "CLN": V_SHERWIN,
        "BLD": V_EMERY,
        "CON": V_EMERY,
        "LUM": V_EMERY,
        "FAS": V_EMERY,
        "HVF": V_AMAZON,
        "ADH": V_AMAZON,
        "DRM": V_EMERY,
        "DRS": V_EMERY,
        "SAF": V_HOMEDEPOT,
        "ROF": V_EMERY,
        "HTL": V_EMERY,
        "LOK": V_HOMEDEPOT,
        "INS": V_HOMEDEPOT,
        "FLO": V_HOMEDEPOT,
    }
    vendor_names = {
        V_EMERY: "Emery Jensen Distribution",
        V_SHERWIN: "Sherwin-Williams",
        V_HOMEDEPOT: "The Home Depot Pro",
        V_AMAZON: "Amazon Business",
        V_DECKEXP: "Deck Expressions",
    }

    for _fam_id, _fam_name, dept_code, skus in catalog:
        vid = vendor_map.get(dept_code, V_EMERY)
        for s in skus:
            s_id, s_sku = s[0], s[1]
            links.append((uid(), vid, s_id, s_sku, vendor_names[vid], s[4], 5, 1))

    # Deck boards also supplied by Deck Expressions (secondary vendor)
    for _fam_id, fam_name, _dept_code, skus in catalog:
        if "Deck Board" in fam_name:
            for s in skus:
                links.append((uid(), V_DECKEXP, s[0], s[1], "Deck Expressions", s[4] * 0.95, 7, 0))

    return links


# ── Purchase Orders ──────────────────────────────────────────────────────────


def _build_purchase_orders(catalog):
    """Build 4 POs in various states."""
    orders = []
    items = []

    # Lookup SKUs by code prefix for convenience
    sku_lookup = {}
    for _fam_id, _fam_name, _dept_code, skus in catalog:
        for s in skus:
            sku_lookup[s[1]] = s  # keyed by sku code

    # PO-1: Sherwin-Williams paint order — RECEIVED (14 days ago)
    po1_id = uid()
    po1_items_data = [
        ("PNT-SWSUPER-01", 10, 32.00),
        ("PNT-SWSUPER-02", 8, 34.00),
        ("PNT-SWSUPER-03", 6, 36.00),
        ("PNS-ROLLER9-01", 20, 4.20),
        ("CLN-PREPWIPE-01", 10, 5.20),
    ]
    po1_total = sum(q * c for _, q, c in po1_items_data)
    orders.append(
        f"INSERT INTO purchase_orders (id, vendor_id, vendor_name, document_date, total, status, "
        f"created_by_id, created_by_name, received_at, received_by_id, received_by_name, "
        f"xero_bill_id, xero_sync_status, created_at, updated_at, organization_id) "
        f"VALUES ('{po1_id}', '{V_SHERWIN}', 'Sherwin-Williams', '{ago(days=16)}', {po1_total}, 'received', "
        f"'{ADMIN_ID}', 'Marcus Chen', '{ago(days=14)}', '{ADMIN_ID}', 'Marcus Chen', "
        f"'XERO-STUB-BILL-{po1_id[:8]}', 'synced', '{ago(days=16)}', '{ago(days=14)}', '{ORG}') "
        f"ON CONFLICT DO NOTHING"
    )
    for sku_code, qty, cost in po1_items_data:
        s = sku_lookup[sku_code]
        items.append(
            f"INSERT INTO purchase_order_items (id, po_id, name, original_sku, ordered_qty, delivered_qty, "
            f"unit_price, cost, base_unit, sell_uom, suggested_department, status, sku_id, organization_id) "
            f"VALUES ('{uid()}', '{po1_id}', '{s[2].replace(chr(39), chr(39) + chr(39))}', '{sku_code}', {qty}, {qty}, "
            f"0, {cost}, '{s[6]}', '{s[7]}', '{sku_code[:3]}', 'arrived', '{s[0]}', '{ORG}') "
            f"ON CONFLICT DO NOTHING"
        )

    # PO-2: Home Depot electrical + plumbing — RECEIVED (10 days ago)
    po2_id = uid()
    po2_items_data = [
        ("ELW-ROMEX14-01", 4, 52.00),
        ("ELW-ROMEX12-01", 2, 72.00),
        ("ELE-GFCI15-01", 12, 10.50),
        ("PLF-SHRKBT90-01", 20, 4.80),
        ("PLF-SHRKBTT-01", 15, 5.60),
    ]
    po2_total = sum(q * c for _, q, c in po2_items_data)
    orders.append(
        f"INSERT INTO purchase_orders (id, vendor_id, vendor_name, document_date, total, status, "
        f"created_by_id, created_by_name, received_at, received_by_id, received_by_name, "
        f"xero_sync_status, created_at, updated_at, organization_id) "
        f"VALUES ('{po2_id}', '{V_HOMEDEPOT}', 'The Home Depot Pro', '{ago(days=12)}', {po2_total}, 'received', "
        f"'{ADMIN_ID}', 'Marcus Chen', '{ago(days=10)}', '{ADMIN_ID}', 'Marcus Chen', "
        f"'pending', '{ago(days=12)}', '{ago(days=10)}', '{ORG}') "
        f"ON CONFLICT DO NOTHING"
    )
    for sku_code, qty, cost in po2_items_data:
        s = sku_lookup[sku_code]
        items.append(
            f"INSERT INTO purchase_order_items (id, po_id, name, original_sku, ordered_qty, delivered_qty, "
            f"unit_price, cost, base_unit, sell_uom, suggested_department, status, sku_id, organization_id) "
            f"VALUES ('{uid()}', '{po2_id}', '{s[2].replace(chr(39), chr(39) + chr(39))}', '{sku_code}', {qty}, {qty}, "
            f"0, {cost}, '{s[6]}', '{s[7]}', '{sku_code[:3]}', 'arrived', '{s[0]}', '{ORG}') "
            f"ON CONFLICT DO NOTHING"
        )

    # PO-3: Emery Jensen building materials — ORDERED (3 days ago, not yet received)
    po3_id = uid()
    po3_items_data = [
        ("LUM-STUDS2X4-01", 50, 2.40),
        ("LUM-STUDS2X6-01", 20, 4.00),
        ("BLD-DRYWALL-01", 30, 8.20),
        ("FAS-DRYSCR-01", 20, 2.80),
        ("DRM-JNTCMPD-01", 8, 10.40),
    ]
    po3_total = sum(q * c for _, q, c in po3_items_data)
    orders.append(
        f"INSERT INTO purchase_orders (id, vendor_id, vendor_name, document_date, total, status, "
        f"created_by_id, created_by_name, "
        f"xero_sync_status, created_at, updated_at, organization_id) "
        f"VALUES ('{po3_id}', '{V_EMERY}', 'Emery Jensen Distribution', '{ago(days=3)}', {po3_total}, 'ordered', "
        f"'{ADMIN_ID}', 'Marcus Chen', "
        f"'pending', '{ago(days=3)}', '{ago(days=3)}', '{ORG}') "
        f"ON CONFLICT DO NOTHING"
    )
    for sku_code, qty, cost in po3_items_data:
        s = sku_lookup[sku_code]
        items.append(
            f"INSERT INTO purchase_order_items (id, po_id, name, original_sku, ordered_qty, delivered_qty, "
            f"unit_price, cost, base_unit, sell_uom, suggested_department, status, sku_id, organization_id) "
            f"VALUES ('{uid()}', '{po3_id}', '{s[2].replace(chr(39), chr(39) + chr(39))}', '{sku_code}', {qty}, 0, "
            f"0, {cost}, '{s[6]}', '{s[7]}', '{sku_code[:3]}', 'ordered', '{s[0]}', '{ORG}') "
            f"ON CONFLICT DO NOTHING"
        )

    # PO-4: Deck Expressions deck boards — ORDERED (1 day ago)
    po4_id = uid()
    po4_items_data = [
        ("LUM-PTDECK-01", 60, 8.80),
        ("LUM-PTDECK-02", 24, 11.60),
        ("FAS-DECKSCR-01", 15, 7.80),
        ("FAS-DECKSCR-02", 10, 8.60),
    ]
    po4_total = sum(q * c for _, q, c in po4_items_data)
    orders.append(
        f"INSERT INTO purchase_orders (id, vendor_id, vendor_name, document_date, total, status, "
        f"created_by_id, created_by_name, "
        f"xero_sync_status, created_at, updated_at, organization_id) "
        f"VALUES ('{po4_id}', '{V_DECKEXP}', 'Deck Expressions', '{ago(days=1)}', {po4_total}, 'ordered', "
        f"'{ADMIN_ID}', 'Marcus Chen', "
        f"'pending', '{ago(days=1)}', '{ago(days=1)}', '{ORG}') "
        f"ON CONFLICT DO NOTHING"
    )
    for sku_code, qty, cost in po4_items_data:
        s = sku_lookup[sku_code]
        items.append(
            f"INSERT INTO purchase_order_items (id, po_id, name, original_sku, ordered_qty, delivered_qty, "
            f"unit_price, cost, base_unit, sell_uom, suggested_department, status, sku_id, organization_id) "
            f"VALUES ('{uid()}', '{po4_id}', '{s[2].replace(chr(39), chr(39) + chr(39))}', '{sku_code}', {qty}, 0, "
            f"0, {cost}, '{s[6]}', '{s[7]}', '{sku_code[:3]}', 'ordered', '{s[0]}', '{ORG}') "
            f"ON CONFLICT DO NOTHING"
        )

    return {
        "orders": orders,
        "items": items,
        "po_ids": [po1_id, po2_id, po3_id, po4_id],
        "po1_id": po1_id,
        "po2_id": po2_id,
        "po3_id": po3_id,
        "po4_id": po4_id,
        "po1_items": po1_items_data,
        "po2_items": po2_items_data,
    }


# ── Withdrawals ──────────────────────────────────────────────────────────────

# Store withdrawal metadata for cross-referencing
_WD_META = []  # populated by _build_withdrawals


def _build_withdrawals(catalog):
    """Build 8 withdrawals across different jobs, contractors, and payment states."""
    stmts_w = []
    stmts_wi = []

    sku_lookup = {}
    for _fam_id, _fam_name, _dept_code, skus in catalog:
        for s in skus:
            sku_lookup[s[1]] = s

    def make_wd(
        wd_id,
        job_id,
        job_code,
        addr,
        contractor_id,
        contractor_name,
        be_name,
        be_id,
        items_data,
        payment_status,
        invoice_id,
        paid_at,
        days_ago,
    ):
        """items_data: [(sku_code, qty, unit_price, cost)]"""
        import json

        subtotal = sum(q * p for _, q, p, _ in items_data)
        cost_total = sum(q * c for _, q, _, c in items_data)
        tax = round(subtotal * 0.10, 2)
        total = round(subtotal + tax, 2)

        items_json = json.dumps(
            [
                {
                    "sku_id": sku_lookup[sc][0],
                    "sku": sc,
                    "name": sku_lookup[sc][2],
                    "quantity": q,
                    "unit_price": p,
                    "cost": c,
                    "unit": sku_lookup[sc][6],
                    "sell_uom": sku_lookup[sc][7],
                    "sell_cost": c,
                    "subtotal": round(q * p, 2),
                    "cost_total": round(q * c, 2),
                }
                for sc, q, p, c in items_data
            ]
        )

        inv_val = f"'{invoice_id}'" if invoice_id else "NULL"
        paid_val = f"'{paid_at}'" if paid_at else "NULL"

        stmts_w.append(
            f"INSERT INTO withdrawals (id, items, job_id, service_address, subtotal, tax, tax_rate, total, cost_total, "
            f"contractor_id, contractor_name, contractor_company, billing_entity, billing_entity_id, "
            f"payment_status, invoice_id, paid_at, processed_by_id, processed_by_name, organization_id, created_at) "
            f"VALUES ('{wd_id}', '{items_json.replace(chr(39), chr(39) + chr(39))}', '{job_code}', '{addr.replace(chr(39), chr(39) + chr(39))}', "
            f"{subtotal}, {tax}, 0.10, {total}, {cost_total}, "
            f"'{contractor_id}', '{contractor_name.replace(chr(39), chr(39) + chr(39))}', '', '{be_name.replace(chr(39), chr(39) + chr(39))}', '{be_id}', "
            f"'{payment_status}', {inv_val}, {paid_val}, '{ADMIN_ID}', 'Marcus Chen', '{ORG}', '{ago(days=days_ago)}') "
            f"ON CONFLICT DO NOTHING"
        )

        for sc, q, p, c in items_data:
            s = sku_lookup[sc]
            stmts_wi.append(
                f"INSERT INTO withdrawal_items (id, withdrawal_id, sku_id, sku, name, quantity, unit_price, cost, "
                f"unit, amount, cost_total, sell_uom, sell_cost) "
                f"VALUES ('{uid()}', '{wd_id}', '{s[0]}', '{sc}', '{s[2].replace(chr(39), chr(39) + chr(39))}', {q}, {p}, {c}, "
                f"'{s[6]}', {round(q * p, 2)}, {round(q * c, 2)}, '{s[7]}', {c}) "
                f"ON CONFLICT DO NOTHING"
            )

        _WD_META.append(
            {
                "id": wd_id,
                "job_code": job_code,
                "job_id": job_id,
                "be_name": be_name,
                "be_id": be_id,
                "contractor_id": contractor_id,
                "contractor_name": contractor_name,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "cost_total": cost_total,
                "payment_status": payment_status,
                "invoice_id": invoice_id,
                "items": items_data,
                "days_ago": days_ago,
            }
        )

    # WD-1: Kitchen remodel — plumbing (paid)
    wd1 = uid()
    inv1 = uid()
    make_wd(
        wd1,
        J_KITCHEN_1,
        "RR-2026-001",
        "1200 Mountain View Dr, Unit 4A, Vail CO",
        CONTRACTOR_MIKE_ID,
        "Mike Torres",
        "Riva Ridge Property Mgmt",
        BE_RIVRIDGE,
        [
            ("PLP-PEXTUBE-01", 2, 42.99, 24.50),
            ("PLF-SHRKBT90-01", 10, 8.49, 4.80),
            ("PLF-SHRKBTT-01", 6, 9.99, 5.60),
        ],
        "paid",
        inv1,
        ago(days=5),
        12,
    )

    # WD-2: Kitchen remodel — electrical (invoiced)
    wd2 = uid()
    inv2 = uid()
    make_wd(
        wd2,
        J_KITCHEN_1,
        "RR-2026-001",
        "1200 Mountain View Dr, Unit 4A, Vail CO",
        CONTRACTOR_MIKE_ID,
        "Mike Torres",
        "Riva Ridge Property Mgmt",
        BE_RIVRIDGE,
        [
            ("ELE-DECORASW-01", 8, 3.29, 1.60),
            ("ELE-GFCI15-01", 4, 18.99, 10.50),
            ("ELW-ROMEX14-01", 1, 89.99, 52.00),
        ],
        "invoiced",
        inv2,
        None,
        10,
    )

    # WD-3: Bathroom renovation — drywall (invoiced)
    wd3 = uid()
    make_wd(
        wd3,
        J_BATH_2,
        "RR-2026-002",
        "1200 Mountain View Dr, Unit 7B, Vail CO",
        CONTRACTOR_MIKE_ID,
        "Mike Torres",
        "Riva Ridge Property Mgmt",
        BE_RIVRIDGE,
        [
            ("BLD-DRYWALL-01", 12, 14.99, 8.20),
            ("FAS-DRYSCR-01", 4, 5.99, 2.80),
            ("DRM-JNTCMPD-01", 2, 18.99, 10.40),
            ("DRS-DRYTAPE-01", 3, 6.99, 3.20),
        ],
        "invoiced",
        inv2,
        None,
        8,
    )

    # WD-4: Deck replacement — lumber (unpaid)
    wd4 = uid()
    make_wd(
        wd4,
        J_DECK_3,
        "SP-2026-001",
        "345 Pine Ridge Rd, Aspen CO",
        CONTRACTOR_SARAH_ID,
        "Sarah Okafor",
        "Summit Property Group",
        BE_SUMMIT,
        [
            ("LUM-PTDECK-01", 20, 14.99, 8.80),
            ("LUM-PTDECK-02", 8, 19.99, 11.60),
            ("FAS-DECKSCR-01", 6, 14.99, 7.80),
        ],
        "unpaid",
        None,
        None,
        6,
    )

    # WD-5: Deck — more materials (unpaid)
    wd5 = uid()
    make_wd(
        wd5,
        J_DECK_3,
        "SP-2026-001",
        "345 Pine Ridge Rd, Aspen CO",
        CONTRACTOR_SARAH_ID,
        "Sarah Okafor",
        "Summit Property Group",
        BE_SUMMIT,
        [
            ("LUM-STUDS2X4-01", 12, 4.29, 2.40),
            ("LUM-STUDS2X6-01", 8, 6.99, 4.00),
            ("CON-QUIKSET-01", 6, 7.49, 4.10),
        ],
        "unpaid",
        None,
        None,
        4,
    )

    # WD-6: Electrical upgrade (unpaid)
    wd6 = uid()
    make_wd(
        wd6,
        J_ELECTRIC_4,
        "SP-2026-002",
        "345 Pine Ridge Rd, Aspen CO",
        CONTRACTOR_SARAH_ID,
        "Sarah Okafor",
        "Summit Property Group",
        BE_SUMMIT,
        [
            ("ELW-ROMEX12-01", 1, 119.99, 72.00),
            ("ELE-GFCI15-01", 6, 18.99, 10.50),
            ("ELE-DECORASW-02", 10, 3.29, 1.60),
        ],
        "unpaid",
        None,
        None,
        3,
    )

    # WD-7: Coastal paint job (paid)
    wd7 = uid()
    inv3 = uid()
    make_wd(
        wd7,
        J_PAINT_5,
        "CL-2026-001",
        "45 Ocean Ave, Monterey CA",
        CONTRACTOR_MIKE_ID,
        "Mike Torres",
        "Coastal Living Rentals",
        BE_COASTAL,
        [
            ("PNT-SWSUPER-03", 4, 58.99, 36.00),
            ("PNS-ROLLER9-01", 6, 8.99, 4.20),
            ("PNS-ROLLER9-02", 4, 9.49, 4.50),
            ("CLN-PREPWIPE-01", 3, 9.99, 5.20),
        ],
        "paid",
        inv3,
        ago(days=1),
        7,
    )

    # WD-8: Kitchen — safety + misc (unpaid, recent)
    wd8 = uid()
    make_wd(
        wd8,
        J_KITCHEN_1,
        "RR-2026-001",
        "1200 Mountain View Dr, Unit 4A, Vail CO",
        CONTRACTOR_MIKE_ID,
        "Mike Torres",
        "Riva Ridge Property Mgmt",
        BE_RIVRIDGE,
        [
            ("SAF-KIDDESM-01", 3, 42.99, 28.00),
            ("LOK-KWIKDBL-01", 2, 29.99, 16.00),
            ("ADH-LIQNAIL-01", 4, 5.49, 2.80),
        ],
        "unpaid",
        None,
        None,
        1,
    )

    return {
        "withdrawals": stmts_w,
        "items": stmts_wi,
        "wd_ids": [wd1, wd2, wd3, wd4, wd5, wd6, wd7, wd8],
        "inv1": inv1,
        "inv2": inv2,
        "inv3": inv3,
        "wd1": wd1,
        "wd2": wd2,
        "wd3": wd3,
        "wd4": wd4,
        "wd5": wd5,
        "wd6": wd6,
        "wd7": wd7,
        "wd8": wd8,
    }


# ── Material Requests ────────────────────────────────────────────────────────


def _build_material_requests(catalog, _wd_data):
    import json

    stmts_mr = []
    stmts_mri = []
    sku_lookup = {}
    for _fam_id, _fam_name, _dept_code, skus in catalog:
        for s in skus:
            sku_lookup[s[1]] = s

    def q(s: str) -> str:
        return s.replace("'", "''")

    # MR-1: Pending — Sarah needs insulation for deck job
    mr1_id = uid()
    mr1_items_data = [
        ("INS-OWENR15-01", 4, 49.99, 0),
    ]
    mr1_items = json.dumps(
        [
            {
                "sku_id": sku_lookup[sc][0],
                "sku": sc,
                "name": sku_lookup[sc][2],
                "quantity": qty,
                "unit_price": price,
                "cost": cost,
                "unit": sku_lookup[sc][6],
                "sell_uom": sku_lookup[sc][7],
                "sell_cost": cost,
                "subtotal": round(qty * price, 2),
                "cost_total": round(qty * cost, 2),
            }
            for sc, qty, price, cost in mr1_items_data
        ]
    )
    stmts_mr.append(
        f"INSERT INTO material_requests (id, contractor_id, contractor_name, items, status, job_id, "
        f"service_address, created_at, organization_id) "
        f"VALUES ('{mr1_id}', '{CONTRACTOR_SARAH_ID}', 'Sarah Okafor', "
        f"'{mr1_items.replace(chr(39), chr(39) + chr(39))}', 'pending', 'SP-2026-001', "
        f"'345 Pine Ridge Rd, Aspen CO', '{ago(hours=6)}', '{ORG}') "
        f"ON CONFLICT DO NOTHING"
    )
    for sc, qty, price, cost in mr1_items_data:
        s = sku_lookup[sc]
        stmts_mri.append(
            f"INSERT INTO material_request_items (id, material_request_id, sku_id, sku, name, quantity, unit_price, cost, unit) "
            f"VALUES ('{uid()}', '{mr1_id}', '{s[0]}', '{sc}', '{q(s[2])}', {qty}, {price}, {cost}, '{s[6]}') "
            f"ON CONFLICT DO NOTHING"
        )

    # MR-2: Processed — Mike's earlier flooring request (became WD-8 essentially)
    mr2_id = uid()
    mr2_items_data = [
        ("FLO-LVPOAK-01", 6, 42.99, 0),
    ]
    mr2_items = json.dumps(
        [
            {
                "sku_id": sku_lookup[sc][0],
                "sku": sc,
                "name": sku_lookup[sc][2],
                "quantity": qty,
                "unit_price": price,
                "cost": cost,
                "unit": sku_lookup[sc][6],
                "sell_uom": sku_lookup[sc][7],
                "sell_cost": cost,
                "subtotal": round(qty * price, 2),
                "cost_total": round(qty * cost, 2),
            }
            for sc, qty, price, cost in mr2_items_data
        ]
    )
    stmts_mr.append(
        f"INSERT INTO material_requests (id, contractor_id, contractor_name, items, status, "
        f"job_id, service_address, created_at, processed_at, processed_by_id, organization_id) "
        f"VALUES ('{mr2_id}', '{CONTRACTOR_MIKE_ID}', 'Mike Torres', "
        f"'{mr2_items.replace(chr(39), chr(39) + chr(39))}', 'processed', "
        f"'RR-2026-001', '1200 Mountain View Dr, Unit 4A, Vail CO', '{ago(days=2)}', '{ago(days=1)}', '{ADMIN_ID}', '{ORG}') "
        f"ON CONFLICT DO NOTHING"
    )
    for sc, qty, price, cost in mr2_items_data:
        s = sku_lookup[sc]
        stmts_mri.append(
            f"INSERT INTO material_request_items (id, material_request_id, sku_id, sku, name, quantity, unit_price, cost, unit) "
            f"VALUES ('{uid()}', '{mr2_id}', '{s[0]}', '{sc}', '{q(s[2])}', {qty}, {price}, {cost}, '{s[6]}') "
            f"ON CONFLICT DO NOTHING"
        )

    return {"requests": stmts_mr, "items": stmts_mri}


# ── Invoices ─────────────────────────────────────────────────────────────────


def _build_invoices(wd_data):
    stmts = []
    inv1 = wd_data["inv1"]  # WD-1 kitchen plumbing — PAID
    inv2 = wd_data["inv2"]  # WD-2 + WD-3 combined — APPROVED (overdue)
    inv3 = wd_data["inv3"]  # WD-7 coastal paint — PAID

    wd_meta_by_id = {w["id"]: w for w in _WD_META}
    w1 = wd_meta_by_id[wd_data["wd1"]]
    w2 = wd_meta_by_id[wd_data["wd2"]]
    w3 = wd_meta_by_id[wd_data["wd3"]]
    w7 = wd_meta_by_id[wd_data["wd7"]]

    # INV-00001: Kitchen plumbing — PAID
    stmts.append(
        f"INSERT INTO invoices (id, invoice_number, billing_entity, billing_entity_id, contact_name, contact_email, "
        f"status, subtotal, tax, tax_rate, total, amount_credited, invoice_date, due_date, payment_terms, "
        f"billing_address, currency, xero_sync_status, organization_id, created_at, updated_at) "
        f"VALUES ('{inv1}', 'INV-00001', 'Riva Ridge Property Mgmt', '{BE_RIVRIDGE}', 'Mike Torres', 'mike@rivridge.com', "
        f"'paid', {w1['subtotal']}, {w1['tax']}, 0.10, {w1['total']}, 0, "
        f"'{ago(days=12)}', '{ago(days=-18)}', 'net_30', "
        f"'1200 Mountain View Dr, Ste 400, Vail CO 81657', 'USD', 'synced', '{ORG}', '{ago(days=12)}', '{ago(days=5)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # INV-00002: Kitchen electrical + Bathroom drywall — APPROVED (due in 20 days)
    inv2_sub = round(w2["subtotal"] + w3["subtotal"], 2)
    inv2_tax = round(w2["tax"] + w3["tax"], 2)
    inv2_total = round(w2["total"] + w3["total"], 2)
    stmts.append(
        f"INSERT INTO invoices (id, invoice_number, billing_entity, billing_entity_id, contact_name, contact_email, "
        f"status, subtotal, tax, tax_rate, total, amount_credited, invoice_date, due_date, payment_terms, "
        f"billing_address, currency, approved_by_id, approved_at, xero_sync_status, organization_id, created_at, updated_at) "
        f"VALUES ('{inv2}', 'INV-00002', 'Riva Ridge Property Mgmt', '{BE_RIVRIDGE}', 'Mike Torres', 'mike@rivridge.com', "
        f"'approved', {inv2_sub}, {inv2_tax}, 0.10, {inv2_total}, 0, "
        f"'{ago(days=8)}', '{future(days=22)}', 'net_30', "
        f"'1200 Mountain View Dr, Ste 400, Vail CO 81657', 'USD', '{ADMIN_ID}', '{ago(days=7)}', 'synced', '{ORG}', '{ago(days=8)}', '{ago(days=7)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # INV-00003: Coastal paint — PAID
    stmts.append(
        f"INSERT INTO invoices (id, invoice_number, billing_entity, billing_entity_id, contact_name, contact_email, "
        f"status, subtotal, tax, tax_rate, total, amount_credited, invoice_date, due_date, payment_terms, "
        f"billing_address, currency, xero_sync_status, organization_id, created_at, updated_at) "
        f"VALUES ('{inv3}', 'INV-00003', 'Coastal Living Rentals', '{BE_COASTAL}', 'Jenna Park', 'jenna@coastalrentals.com', "
        f"'paid', {w7['subtotal']}, {w7['tax']}, 0.10, {w7['total']}, 0, "
        f"'{ago(days=7)}', '{future(days=8)}', 'net_15', "
        f"'45 Ocean Ave, Ste 3, Monterey CA 93940', 'USD', 'synced', '{ORG}', '{ago(days=7)}', '{ago(days=1)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # INV-00004: Draft invoice for deck work (WD-4 + WD-5) — not yet sent
    inv4 = uid()
    w4 = wd_meta_by_id[wd_data["wd4"]]
    w5 = wd_meta_by_id[wd_data["wd5"]]
    inv4_sub = round(w4["subtotal"] + w5["subtotal"], 2)
    inv4_tax = round(w4["tax"] + w5["tax"], 2)
    inv4_total = round(w4["total"] + w5["total"], 2)
    stmts.append(
        f"INSERT INTO invoices (id, invoice_number, billing_entity, billing_entity_id, contact_name, contact_email, "
        f"status, subtotal, tax, tax_rate, total, amount_credited, invoice_date, due_date, payment_terms, "
        f"billing_address, currency, xero_sync_status, organization_id, created_at, updated_at) "
        f"VALUES ('{inv4}', 'INV-00004', 'Summit Property Group', '{BE_SUMMIT}', 'Sarah Okafor', 'sarah@summitpm.com', "
        f"'draft', {inv4_sub}, {inv4_tax}, 0.10, {inv4_total}, 0, "
        f"'{ago(days=2)}', '{future(days=28)}', 'net_30', "
        f"'890 Summit Blvd, Ste 12, Aspen CO 81611', 'USD', 'pending', '{ORG}', '{ago(days=2)}', '{ago(days=2)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # Invoice-withdrawal joins
    stmts.append(
        f"INSERT INTO invoice_withdrawals (invoice_id, withdrawal_id) VALUES ('{inv1}', '{wd_data['wd1']}') ON CONFLICT DO NOTHING"
    )
    stmts.append(
        f"INSERT INTO invoice_withdrawals (invoice_id, withdrawal_id) VALUES ('{inv2}', '{wd_data['wd2']}') ON CONFLICT DO NOTHING"
    )
    stmts.append(
        f"INSERT INTO invoice_withdrawals (invoice_id, withdrawal_id) VALUES ('{inv2}', '{wd_data['wd3']}') ON CONFLICT DO NOTHING"
    )
    stmts.append(
        f"INSERT INTO invoice_withdrawals (invoice_id, withdrawal_id) VALUES ('{inv3}', '{wd_data['wd7']}') ON CONFLICT DO NOTHING"
    )
    stmts.append(
        f"INSERT INTO invoice_withdrawals (invoice_id, withdrawal_id) VALUES ('{inv4}', '{wd_data['wd4']}') ON CONFLICT DO NOTHING"
    )
    stmts.append(
        f"INSERT INTO invoice_withdrawals (invoice_id, withdrawal_id) VALUES ('{inv4}', '{wd_data['wd5']}') ON CONFLICT DO NOTHING"
    )

    # Invoice line items — from withdrawal items
    sku_lookup = {}
    for _fam_id, _fam_name, _dept_code, skus in _build_catalog():
        for s in skus:
            sku_lookup[s[1]] = s

    for inv_id, wd_ids in [
        (inv1, [wd_data["wd1"]]),
        (inv2, [wd_data["wd2"], wd_data["wd3"]]),
        (inv3, [wd_data["wd7"]]),
        (inv4, [wd_data["wd4"], wd_data["wd5"]]),
    ]:
        for wid in wd_ids:
            w = wd_meta_by_id[wid]
            for sc, q, p, c in w["items"]:
                s = sku_lookup.get(sc)
                job_val = f"'{w['job_code']}'" if w.get("job_code") else "NULL"
                stmts.append(
                    f"INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, amount, cost, "
                    f"sku_id, job_id, unit, sell_cost) "
                    f"VALUES ('{uid()}', '{inv_id}', '{s[2].replace(chr(39), chr(39) + chr(39))}', {q}, {p}, {round(q * p, 2)}, {c}, "
                    f"'{s[0]}', {job_val}, '{s[6]}', {c}) "
                    f"ON CONFLICT DO NOTHING"
                )

    return {
        "stmts": stmts,
        "inv1": inv1,
        "inv2": inv2,
        "inv3": inv3,
        "inv4": inv4,
        "inv1_total": w1["total"],
        "inv3_total": w7["total"],
    }


# ── Payments ─────────────────────────────────────────────────────────────────


def _build_payments(inv_data):
    stmts = []
    # Payment for INV-00001
    p1 = uid()
    stmts.append(
        f"INSERT INTO payments (id, invoice_id, billing_entity_id, amount, method, reference, payment_date, "
        f"recorded_by_id, organization_id, created_at, updated_at) "
        f"VALUES ('{p1}', '{inv_data['inv1']}', '{BE_RIVRIDGE}', {inv_data['inv1_total']}, 'check', 'CHK-4521', "
        f"'{ago(days=5)}', '{ADMIN_ID}', '{ORG}', '{ago(days=5)}', '{ago(days=5)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # Payment for INV-00003
    p2 = uid()
    stmts.append(
        f"INSERT INTO payments (id, invoice_id, billing_entity_id, amount, method, reference, payment_date, "
        f"recorded_by_id, organization_id, created_at, updated_at) "
        f"VALUES ('{p2}', '{inv_data['inv3']}', '{BE_COASTAL}', {inv_data['inv3_total']}, 'bank_transfer', 'ACH-8873', "
        f"'{ago(days=1)}', '{ADMIN_ID}', '{ORG}', '{ago(days=1)}', '{ago(days=1)}') "
        f"ON CONFLICT DO NOTHING"
    )

    return stmts


# ── Returns + Credit Notes ───────────────────────────────────────────────────


def _build_returns(wd_data, inv_data):
    import json

    stmts = []
    stmts_ri = []
    # Return 2 GFCI outlets from WD-2 (damaged)
    wd_meta = {w["id"]: w for w in _WD_META}
    wd_meta[wd_data["wd2"]]

    ret_id = uid()
    cn_id = uid()

    # Find the GFCI SKU
    catalog = _build_catalog()
    gfci_sku = None
    for _fam_id, _fam_name, _dept_code, skus in catalog:
        for s in skus:
            if "GFCI15" in s[1]:
                gfci_sku = s
                break

    ret_items_data = [
        (
            "ELE-GFCI15-01",
            gfci_sku[0],
            "Leviton GFCI 15A Outlet White",
            2,
            18.99,
            10.50,
            "each",
            "each",
        ),
    ]

    ret_subtotal = sum(round(qty * price, 2) for _, _, _, qty, price, _, _, _ in ret_items_data)
    ret_cost_total = sum(round(qty * cost, 2) for _, _, _, qty, _, cost, _, _ in ret_items_data)
    ret_tax = round(ret_subtotal * 0.10, 2)
    ret_total = round(ret_subtotal + ret_tax, 2)

    ret_items = json.dumps(
        [
            {
                "sku_id": sku_id,
                "sku": sc,
                "name": name,
                "quantity": qty,
                "unit_price": price,
                "cost": cost,
                "unit": unit,
                "reason": "damaged",
                "notes": "Cracked faceplates on arrival",
            }
            for sc, sku_id, name, qty, price, cost, unit, _sell_uom in ret_items_data
        ]
    )

    stmts.append(
        f"INSERT INTO returns (id, withdrawal_id, contractor_id, contractor_name, billing_entity, billing_entity_id, "
        f"job_id, items, subtotal, tax, total, cost_total, reason, notes, credit_note_id, "
        f"processed_by_id, processed_by_name, organization_id, created_at, updated_at) "
        f"VALUES ('{ret_id}', '{wd_data['wd2']}', '{CONTRACTOR_MIKE_ID}', 'Mike Torres', "
        f"'Riva Ridge Property Mgmt', '{BE_RIVRIDGE}', 'RR-2026-001', "
        f"'{ret_items.replace(chr(39), chr(39) + chr(39))}', {ret_subtotal}, {ret_tax}, {ret_total}, {ret_cost_total}, "
        f"'damaged', 'Cracked faceplates on arrival', '{cn_id}', "
        f"'{ADMIN_ID}', 'Marcus Chen', '{ORG}', '{ago(days=9)}', '{ago(days=9)}') "
        f"ON CONFLICT DO NOTHING"
    )

    for sc, sku_id, name, qty, price, cost, unit, sell_uom in ret_items_data:
        stmts_ri.append(
            f"INSERT INTO return_items (id, return_id, sku_id, sku, name, quantity, unit_price, cost, "
            f"unit, amount, cost_total, sell_uom, sell_cost) "
            f"VALUES ('{uid()}', '{ret_id}', '{sku_id}', '{sc}', '{name.replace(chr(39), chr(39) + chr(39))}', {qty}, {price}, {cost}, "
            f"'{unit}', {round(qty * price, 2)}, {round(qty * cost, 2)}, '{sell_uom}', {cost}) "
            f"ON CONFLICT DO NOTHING"
        )

    # Credit note
    stmts.append(
        f"INSERT INTO credit_notes (id, credit_note_number, invoice_id, return_id, billing_entity, billing_entity_id, "
        f"status, subtotal, tax, total, xero_sync_status, organization_id, created_at, updated_at) "
        f"VALUES ('{cn_id}', 'CN-00001', '{inv_data['inv2']}', '{ret_id}', "
        f"'Riva Ridge Property Mgmt', '{BE_RIVRIDGE}', 'applied', "
        f"{ret_subtotal}, {ret_tax}, {ret_total}, 'synced', '{ORG}', '{ago(days=9)}', '{ago(days=9)}') "
        f"ON CONFLICT DO NOTHING"
    )

    return {"returns": stmts, "items": stmts_ri}


# ── Stock Transactions ───────────────────────────────────────────────────────


def _build_stock_transactions(catalog, wd_data, po_data):
    stmts = []
    sku_lookup = {}
    for _fam_id, _fam_name, _dept_code, skus in catalog:
        for s in skus:
            sku_lookup[s[1]] = s

    wd_meta = {w["id"]: w for w in _WD_META}

    # Stock transactions from withdrawals
    for wd_id in wd_data["wd_ids"]:
        w = wd_meta[wd_id]
        for sc, q, _p, _c in w["items"]:
            s = sku_lookup[sc]
            qty_before = s[5]  # original quantity
            qty_after = qty_before - q
            stmts.append(
                f"INSERT INTO stock_transactions (id, sku_id, sku, product_name, quantity_delta, quantity_before, quantity_after, "
                f"unit, transaction_type, reference_id, reference_type, user_id, user_name, organization_id, created_at, "
                f"original_quantity, original_unit) "
                f"VALUES ('{uid()}', '{s[0]}', '{sc}', '{s[2].replace(chr(39), chr(39) + chr(39))}', {-q}, {qty_before}, {qty_after}, "
                f"'{s[6]}', 'withdrawal', '{wd_id}', 'withdrawal', '{ADMIN_ID}', 'Marcus Chen', '{ORG}', '{ago(days=w['days_ago'])}', "
                f"{q}, '{s[6]}') "
                f"ON CONFLICT DO NOTHING"
            )

    # Stock transactions from PO receipts (PO-1 and PO-2 received)
    for po_items, po_id, days in [
        (po_data["po1_items"], po_data["po1_id"], 14),
        (po_data["po2_items"], po_data["po2_id"], 10),
    ]:
        for sc, q, _c in po_items:
            s = sku_lookup[sc]
            qty_before = s[5]
            qty_after = qty_before + q
            stmts.append(
                f"INSERT INTO stock_transactions (id, sku_id, sku, product_name, quantity_delta, quantity_before, quantity_after, "
                f"unit, transaction_type, reference_id, reference_type, user_id, user_name, organization_id, created_at, "
                f"original_quantity, original_unit) "
                f"VALUES ('{uid()}', '{s[0]}', '{sc}', '{s[2].replace(chr(39), chr(39) + chr(39))}', {q}, {qty_before}, {qty_after}, "
                f"'{s[6]}', 'po_receipt', '{po_id}', 'purchase_order', '{ADMIN_ID}', 'Marcus Chen', '{ORG}', '{ago(days=days)}', "
                f"{q}, '{s[6]}') "
                f"ON CONFLICT DO NOTHING"
            )

    return stmts


# ── Financial Ledger ─────────────────────────────────────────────────────────


def _build_financial_ledger(wd_data, po_data, _inv_data):
    stmts = []
    catalog = _build_catalog()
    sku_lookup = {}
    dept_name_lookup = {}
    for _fam_id, _fam_name, _dept_code, skus in catalog:
        for s in skus:
            sku_lookup[s[1]] = s
    from devtools.scripts.company import DEPARTMENTS

    for d in DEPARTMENTS:
        dept_name_lookup[d.code] = d.name

    wd_meta = {w["id"]: w for w in _WD_META}

    # Withdrawal journal entries (revenue, cogs, inventory, tax, AR)
    for wd_id in wd_data["wd_ids"]:
        w = wd_meta[wd_id]
        jid = uid()
        for sc, q, p, c in w["items"]:
            s = sku_lookup[sc]
            dept_name = dept_name_lookup.get(sc[:3], sc[:3])
            # Revenue
            stmts.append(
                f"INSERT INTO financial_ledger (id, journal_id, account, amount, quantity, unit, unit_cost, "
                f"department, job_id, billing_entity, billing_entity_id, contractor_id, sku_id, "
                f"performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
                f"VALUES ('{uid()}', '{jid}', 'revenue', {round(q * p, 2)}, {q}, '{s[6]}', {p}, "
                f"'{dept_name}', '{w['job_code']}', '{w['be_name'].replace(chr(39), chr(39) + chr(39))}', '{w['be_id']}', '{w['contractor_id']}', '{s[0]}', "
                f"'{ADMIN_ID}', 'withdrawal', '{wd_id}', '{ORG}', '{ago(days=w['days_ago'])}') "
                f"ON CONFLICT DO NOTHING"
            )
            # COGS
            stmts.append(
                f"INSERT INTO financial_ledger (id, journal_id, account, amount, quantity, unit, unit_cost, "
                f"department, job_id, billing_entity, billing_entity_id, contractor_id, sku_id, "
                f"performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
                f"VALUES ('{uid()}', '{jid}', 'cogs', {round(q * c, 2)}, {q}, '{s[6]}', {c}, "
                f"'{dept_name}', '{w['job_code']}', '{w['be_name'].replace(chr(39), chr(39) + chr(39))}', '{w['be_id']}', '{w['contractor_id']}', '{s[0]}', "
                f"'{ADMIN_ID}', 'withdrawal', '{wd_id}', '{ORG}', '{ago(days=w['days_ago'])}') "
                f"ON CONFLICT DO NOTHING"
            )
            # Inventory (negative)
            stmts.append(
                f"INSERT INTO financial_ledger (id, journal_id, account, amount, quantity, unit, unit_cost, "
                f"department, job_id, billing_entity, billing_entity_id, contractor_id, sku_id, "
                f"performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
                f"VALUES ('{uid()}', '{jid}', 'inventory', {-round(q * c, 2)}, {q}, '{s[6]}', {c}, "
                f"'{dept_name}', '{w['job_code']}', '{w['be_name'].replace(chr(39), chr(39) + chr(39))}', '{w['be_id']}', '{w['contractor_id']}', '{s[0]}', "
                f"'{ADMIN_ID}', 'withdrawal', '{wd_id}', '{ORG}', '{ago(days=w['days_ago'])}') "
                f"ON CONFLICT DO NOTHING"
            )
        # Tax
        stmts.append(
            f"INSERT INTO financial_ledger (id, journal_id, account, amount, "
            f"job_id, billing_entity, billing_entity_id, contractor_id, "
            f"performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
            f"VALUES ('{uid()}', '{jid}', 'tax_collected', {w['tax']}, "
            f"'{w['job_code']}', '{w['be_name'].replace(chr(39), chr(39) + chr(39))}', '{w['be_id']}', '{w['contractor_id']}', "
            f"'{ADMIN_ID}', 'withdrawal', '{wd_id}', '{ORG}', '{ago(days=w['days_ago'])}') "
            f"ON CONFLICT DO NOTHING"
        )
        # AR
        stmts.append(
            f"INSERT INTO financial_ledger (id, journal_id, account, amount, "
            f"job_id, billing_entity, billing_entity_id, contractor_id, "
            f"performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
            f"VALUES ('{uid()}', '{jid}', 'accounts_receivable', {w['total']}, "
            f"'{w['job_code']}', '{w['be_name'].replace(chr(39), chr(39) + chr(39))}', '{w['be_id']}', '{w['contractor_id']}', "
            f"'{ADMIN_ID}', 'withdrawal', '{wd_id}', '{ORG}', '{ago(days=w['days_ago'])}') "
            f"ON CONFLICT DO NOTHING"
        )

    # PO receipt journal entries (inventory + AP)
    for po_items, po_id, _vid, vname, days in [
        (po_data["po1_items"], po_data["po1_id"], V_SHERWIN, "Sherwin-Williams", 14),
        (po_data["po2_items"], po_data["po2_id"], V_HOMEDEPOT, "The Home Depot Pro", 10),
    ]:
        jid = uid()
        for sc, q, c in po_items:
            s = sku_lookup[sc]
            dept_name = dept_name_lookup.get(sc[:3], sc[:3])
            stmts.append(
                f"INSERT INTO financial_ledger (id, journal_id, account, amount, quantity, unit, unit_cost, "
                f"department, vendor_name, sku_id, performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
                f"VALUES ('{uid()}', '{jid}', 'inventory', {round(q * c, 2)}, {q}, '{s[6]}', {c}, "
                f"'{dept_name}', '{vname}', '{s[0]}', '{ADMIN_ID}', 'po_receipt', '{po_id}', '{ORG}', '{ago(days=days)}') "
                f"ON CONFLICT DO NOTHING"
            )
            stmts.append(
                f"INSERT INTO financial_ledger (id, journal_id, account, amount, quantity, unit, unit_cost, "
                f"department, vendor_name, sku_id, performed_by_user_id, reference_type, reference_id, organization_id, created_at) "
                f"VALUES ('{uid()}', '{jid}', 'accounts_payable', {round(q * c, 2)}, {q}, '{s[6]}', {c}, "
                f"'{dept_name}', '{vname}', '{s[0]}', '{ADMIN_ID}', 'po_receipt', '{po_id}', '{ORG}', '{ago(days=days)}') "
                f"ON CONFLICT DO NOTHING"
            )

    return stmts


# ── Cycle Count ──────────────────────────────────────────────────────────────


def _build_cycle_count(catalog):
    stmts = []
    cc_id = uid()
    stmts.append(
        f"INSERT INTO cycle_counts (id, organization_id, status, scope, created_by_id, created_by_name, "
        f"committed_by_id, committed_at, created_at) "
        f"VALUES ('{cc_id}', '{ORG}', 'committed', 'Plumbing spot check', '{ADMIN_ID}', 'Marcus Chen', "
        f"'{ADMIN_ID}', '{ago(days=2)}', '{ago(days=3)}') "
        f"ON CONFLICT DO NOTHING"
    )

    # Count some plumbing SKUs
    for _fam_id, _fam_name, dept_code, skus in catalog:
        if dept_code in ("PLP", "PLF"):
            for s in skus:
                variance = -1 if "Elbow" in s[2] else 0  # one item short
                stmts.append(
                    f"INSERT INTO cycle_count_items (id, cycle_count_id, sku_id, sku, product_name, "
                    f"snapshot_qty, counted_qty, variance, unit, created_at) "
                    f"VALUES ('{uid()}', '{cc_id}', '{s[0]}', '{s[1]}', '{s[2].replace(chr(39), chr(39) + chr(39))}', "
                    f"{s[5]}, {s[5] + variance}, {variance}, '{s[6]}', '{ago(days=3)}') "
                    f"ON CONFLICT DO NOTHING"
                )

    return stmts


# ── Truncate ─────────────────────────────────────────────────────────────────

TRUNCATE_ORDER = [
    # Leaf tables first (no incoming FKs), then work up
    "embeddings",
    "agent_runs",
    "memory_artifacts",
    "documents",
    "cycle_count_items",
    "cycle_counts",
    "financial_ledger",
    "payment_withdrawals",
    "payments",
    "credit_note_line_items",
    "credit_notes",
    "invoice_line_items",
    "invoice_withdrawals",
    "invoice_counters",
    "invoices",
    "return_items",
    "returns",
    "material_request_items",
    "material_requests",
    "withdrawal_items",
    "withdrawals",
    "purchase_order_items",
    "purchase_orders",
    "stock_transactions",
    "vendor_items",
    "sku_counters",
    "skus",
    "products",
    "vendors",
    "departments",
    "addresses",
    "fiscal_periods",
    "billing_entities",
    "jobs",
    "audit_log",
    "processed_events",
    "refresh_tokens",
    "oauth_states",
    "users",
    "org_settings",
    "organizations",
]


def truncate_statements() -> list[str]:
    return [f"DELETE FROM {t}" for t in TRUNCATE_ORDER]


# ── Runner ───────────────────────────────────────────────────────────────────


async def run_local():
    from shared.infrastructure.db import close_db, get_connection, init_db

    await init_db()
    try:
        conn = get_connection()
        print("Clearing local DB...")
        for stmt in truncate_statements():
            await conn.execute(stmt)
        await conn.commit()
        print("Seeding local DB...")
        stmts = build_statements()
        for i, stmt in enumerate(stmts):
            try:
                await conn.execute(stmt)
            except Exception as e:
                print(f"  WARN stmt {i}: {e}")
            if i % 50 == 0:
                await conn.commit()
        await conn.commit()
        print(f"Done — {len(stmts)} statements executed on local DB.")
    finally:
        await close_db()


async def run_supabase():
    """Run via Supabase MCP — outputs SQL to paste or pipe."""
    stmts = truncate_statements() + build_statements()
    # Write to a file for execution
    sql = ";\n".join(stmts) + ";"
    out_path = "/Users/nooz/products/sku-ops/devtools/data/seed_demo.sql"
    with open(out_path, "w") as f:
        f.write(sql)
    print(f"Wrote {len(stmts)} statements to {out_path}")
    print(
        "Execute in Supabase SQL editor or via: psql $DATABASE_URL -f devtools/data/seed_demo.sql"
    )


async def main():
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--target", choices=["local", "supabase", "both"], default="both")
    args = parser.parse_args()

    if args.target in ("local", "both"):
        await run_local()
    if args.target in ("supabase", "both"):
        await run_supabase()


if __name__ == "__main__":
    asyncio.run(main())
