"""
Seed realistic demo data: vendors, products, SKUs, vendor items, purchase history,
withdrawals, and invoices. Designed to exercise every user story end-to-end.

Run: cd backend && python -m devtools.scripts.seed_realistic
"""

import asyncio
import logging
import random as _random_mod
from datetime import UTC, datetime, timedelta
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
_rng = _random_mod.Random(42)

VENDORS = [
    {
        "name": "Johnson Lumber Co",
        "contact_name": "Mike Johnson",
        "email": "mike@johnsonlumber.com",
        "phone": "555-0101",
        "address": "100 Timber Rd",
    },
    {
        "name": "Pacific Plumbing Supply",
        "contact_name": "Sarah Chen",
        "email": "sarah@pacificplumbing.com",
        "phone": "555-0202",
        "address": "250 Pipe Ave",
    },
    {
        "name": "National Paint & Coatings",
        "contact_name": "Tom Rivera",
        "email": "tom@nationalpaint.com",
        "phone": "555-0303",
        "address": "88 Color Blvd",
    },
    {
        "name": "Allied Electrical Dist.",
        "contact_name": "Karen Park",
        "email": "karen@alliedelectric.com",
        "phone": "555-0404",
        "address": "300 Watt St",
    },
    {
        "name": "FastenAll Hardware",
        "contact_name": "Dave Wilson",
        "email": "dave@fastenall.com",
        "phone": "555-0505",
        "address": "42 Bolt Lane",
    },
    {
        "name": "Pro Tool Warehouse",
        "contact_name": "Lisa Ortega",
        "email": "lisa@protool.com",
        "phone": "555-0606",
        "address": "78 Wrench Way",
    },
]

# Products keyed by (department_code, vendor_index, product_data)
# "product" field groups SKUs under a parent Product concept
# "vendor_sku" is the vendor's part number for this item
PRODUCTS = [
    # === LUMBER (Johnson Lumber) ===
    {
        "name": "2x4x8 Stud SPF",
        "dept": "LUM",
        "vendor": 0,
        "price": 5.99,
        "cost": 3.50,
        "qty": 450,
        "min": 100,
        "unit": "each",
        "product": "Dimensional Lumber",
        "vendor_sku": "JL-2X4-8",
    },
    {
        "name": "2x6x12 Douglas Fir",
        "dept": "LUM",
        "vendor": 0,
        "price": 12.49,
        "cost": 7.80,
        "qty": 180,
        "min": 40,
        "unit": "each",
        "product": "Dimensional Lumber",
        "vendor_sku": "JL-2X6-12",
    },
    {
        "name": "4x8 1/2in CDX Plywood",
        "dept": "LUM",
        "vendor": 0,
        "price": 42.99,
        "cost": 28.00,
        "qty": 85,
        "min": 20,
        "unit": "each",
        "product": "Sheet Goods",
        "vendor_sku": "JL-PLY-12",
    },
    {
        "name": "4x8 3/4in Sanded Plywood",
        "dept": "LUM",
        "vendor": 0,
        "price": 64.99,
        "cost": 42.00,
        "qty": 45,
        "min": 15,
        "unit": "each",
        "product": "Sheet Goods",
        "vendor_sku": "JL-PLY-34",
    },
    {
        "name": "1x6x8 Cedar Fence Board",
        "dept": "LUM",
        "vendor": 0,
        "price": 4.29,
        "cost": 2.50,
        "qty": 600,
        "min": 150,
        "unit": "each",
        "vendor_sku": "JL-CED-168",
    },
    {
        "name": "2x4x10 Pressure Treated",
        "dept": "LUM",
        "vendor": 0,
        "price": 9.99,
        "cost": 6.20,
        "qty": 220,
        "min": 50,
        "unit": "each",
        "product": "Pressure Treated Lumber",
        "vendor_sku": "JL-PT-2410",
    },
    {
        "name": "4x4x8 Post Treated",
        "dept": "LUM",
        "vendor": 0,
        "price": 14.99,
        "cost": 9.00,
        "qty": 60,
        "min": 20,
        "unit": "each",
        "product": "Pressure Treated Lumber",
        "vendor_sku": "JL-PT-448",
    },
    {
        "name": "1x4x8 Furring Strip",
        "dept": "LUM",
        "vendor": 0,
        "price": 2.49,
        "cost": 1.30,
        "qty": 300,
        "min": 80,
        "unit": "each",
        "vendor_sku": "JL-FUR-148",
    },
    # === PLUMBING (Pacific Plumbing) ===
    {
        "name": "1/2in PEX Pipe 100ft",
        "dept": "PLU",
        "vendor": 1,
        "price": 89.99,
        "cost": 52.00,
        "qty": 35,
        "min": 10,
        "unit": "roll",
        "product": "PEX Tubing",
        "vendor_sku": "PP-PEX-12-100",
    },
    {
        "name": "3/4in PEX Pipe 100ft",
        "dept": "PLU",
        "vendor": 1,
        "price": 119.99,
        "cost": 72.00,
        "qty": 20,
        "min": 8,
        "unit": "roll",
        "product": "PEX Tubing",
        "vendor_sku": "PP-PEX-34-100",
    },
    {
        "name": "1/2in Copper Elbow 90deg",
        "dept": "PLU",
        "vendor": 1,
        "price": 2.49,
        "cost": 1.20,
        "qty": 250,
        "min": 50,
        "unit": "each",
        "product": "Copper Fittings",
        "vendor_sku": "PP-CU-EL90",
    },
    {
        "name": "3/4in PVC Coupling",
        "dept": "PLU",
        "vendor": 1,
        "price": 0.89,
        "cost": 0.35,
        "qty": 400,
        "min": 100,
        "unit": "each",
        "vendor_sku": "PP-PVC-CPL34",
    },
    {
        "name": "SharkBite 1/2in Push Fitting",
        "dept": "PLU",
        "vendor": 1,
        "price": 7.99,
        "cost": 4.20,
        "qty": 80,
        "min": 20,
        "unit": "each",
        "vendor_sku": "PP-SB-12",
    },
    {
        "name": "PVC Cement 16oz",
        "dept": "PLU",
        "vendor": 1,
        "price": 8.49,
        "cost": 4.50,
        "qty": 45,
        "min": 15,
        "unit": "each",
        "vendor_sku": "PP-CEM-16",
    },
    {
        "name": "Teflon Tape 1/2in x 520in",
        "dept": "PLU",
        "vendor": 1,
        "price": 1.99,
        "cost": 0.60,
        "qty": 200,
        "min": 50,
        "unit": "roll",
        "vendor_sku": "PP-TEF-12",
    },
    # === PAINT (National Paint) ===
    {
        "name": "5 Gal Interior Flat White",
        "dept": "PNT",
        "vendor": 2,
        "price": 149.99,
        "cost": 85.00,
        "qty": 18,
        "min": 8,
        "unit": "gallon",
        "product": "Interior Paint",
        "vendor_sku": "NP-INT-FW5",
        "purchase_uom": "pail",
        "purchase_pack_qty": 5,
    },
    {
        "name": "5 Gal Interior Eggshell White",
        "dept": "PNT",
        "vendor": 2,
        "price": 164.99,
        "cost": 95.00,
        "qty": 14,
        "min": 6,
        "unit": "gallon",
        "product": "Interior Paint",
        "vendor_sku": "NP-INT-EW5",
        "purchase_uom": "pail",
        "purchase_pack_qty": 5,
    },
    {
        "name": "1 Gal Exterior Semi-Gloss White",
        "dept": "PNT",
        "vendor": 2,
        "price": 44.99,
        "cost": 26.00,
        "qty": 30,
        "min": 10,
        "unit": "gallon",
        "product": "Exterior Paint",
        "vendor_sku": "NP-EXT-SGW1",
    },
    {
        "name": "Primer 5 Gal",
        "dept": "PNT",
        "vendor": 2,
        "price": 109.99,
        "cost": 62.00,
        "qty": 12,
        "min": 5,
        "unit": "gallon",
        "product": "Interior Paint",
        "vendor_sku": "NP-PRM-5",
        "purchase_uom": "pail",
        "purchase_pack_qty": 5,
    },
    {
        "name": "Wood Stain Golden Oak Qt",
        "dept": "PNT",
        "vendor": 2,
        "price": 18.99,
        "cost": 10.50,
        "qty": 25,
        "min": 8,
        "unit": "quart",
        "vendor_sku": "NP-STN-GO",
    },
    {
        "name": "2in Angle Sash Brush",
        "dept": "PNT",
        "vendor": 2,
        "price": 8.99,
        "cost": 4.00,
        "qty": 60,
        "min": 20,
        "unit": "each",
        "product": "Paint Brushes",
        "vendor_sku": "NP-BR-2AS",
    },
    {
        "name": "9in Roller Cover 3/8nap 3pk",
        "dept": "PNT",
        "vendor": 2,
        "price": 12.99,
        "cost": 6.50,
        "qty": 40,
        "min": 15,
        "unit": "pack",
        "product": "Paint Brushes",
        "vendor_sku": "NP-RC-938",
    },
    {
        "name": "Painters Tape Blue 1.88in x 60yd",
        "dept": "PNT",
        "vendor": 2,
        "price": 7.49,
        "cost": 3.80,
        "qty": 75,
        "min": 25,
        "unit": "roll",
        "vendor_sku": "NP-TPB-188",
    },
    # === ELECTRICAL (Allied Electrical) ===
    {
        "name": "12/2 NM-B Romex 250ft",
        "dept": "ELE",
        "vendor": 3,
        "price": 149.99,
        "cost": 92.00,
        "qty": 15,
        "min": 5,
        "unit": "roll",
        "product": "Romex Wire",
        "vendor_sku": "AE-ROM-122",
    },
    {
        "name": "14/2 NM-B Romex 250ft",
        "dept": "ELE",
        "vendor": 3,
        "price": 119.99,
        "cost": 72.00,
        "qty": 18,
        "min": 5,
        "unit": "roll",
        "product": "Romex Wire",
        "vendor_sku": "AE-ROM-142",
    },
    {
        "name": "Single Gang Old Work Box",
        "dept": "ELE",
        "vendor": 3,
        "price": 2.99,
        "cost": 1.40,
        "qty": 150,
        "min": 40,
        "unit": "each",
        "vendor_sku": "AE-BOX-1G",
    },
    {
        "name": "Decora Switch White",
        "dept": "ELE",
        "vendor": 3,
        "price": 3.49,
        "cost": 1.60,
        "qty": 120,
        "min": 30,
        "unit": "each",
        "product": "Switches & Outlets",
        "vendor_sku": "AE-SW-DW",
    },
    {
        "name": "Decora Outlet 15A White",
        "dept": "ELE",
        "vendor": 3,
        "price": 2.99,
        "cost": 1.30,
        "qty": 140,
        "min": 35,
        "unit": "each",
        "product": "Switches & Outlets",
        "vendor_sku": "AE-OUT-15W",
    },
    {
        "name": "GFCI Outlet 15A White",
        "dept": "ELE",
        "vendor": 3,
        "price": 16.99,
        "cost": 9.00,
        "qty": 35,
        "min": 10,
        "unit": "each",
        "product": "Switches & Outlets",
        "vendor_sku": "AE-GFCI-15W",
    },
    {
        "name": "Wire Nuts Assorted 100pk",
        "dept": "ELE",
        "vendor": 3,
        "price": 9.99,
        "cost": 4.20,
        "qty": 50,
        "min": 15,
        "unit": "pack",
        "vendor_sku": "AE-WN-100",
        "purchase_uom": "box",
        "purchase_pack_qty": 100,
    },
    {
        "name": "Electrical Tape Black 3/4in",
        "dept": "ELE",
        "vendor": 3,
        "price": 3.49,
        "cost": 1.50,
        "qty": 90,
        "min": 25,
        "unit": "roll",
        "vendor_sku": "AE-ET-BK",
    },
    # === HARDWARE (FastenAll) ===
    {
        "name": "#8 x 2-1/2in Deck Screw 5lb",
        "dept": "HDW",
        "vendor": 4,
        "price": 24.99,
        "cost": 13.00,
        "qty": 55,
        "min": 15,
        "unit": "box",
        "product": "Screws",
        "vendor_sku": "FA-DS-825",
        "purchase_uom": "box",
        "purchase_pack_qty": 1,
    },
    {
        "name": "#8 x 1-5/8in Drywall Screw 1lb",
        "dept": "HDW",
        "vendor": 4,
        "price": 6.99,
        "cost": 3.20,
        "qty": 80,
        "min": 25,
        "unit": "box",
        "product": "Screws",
        "vendor_sku": "FA-DW-816",
    },
    {
        "name": "16d Framing Nail 50lb",
        "dept": "HDW",
        "vendor": 4,
        "price": 89.99,
        "cost": 52.00,
        "qty": 12,
        "min": 5,
        "unit": "box",
        "vendor_sku": "FA-FN-16D",
    },
    {
        "name": "3in Cabinet Hinge Satin Nickel",
        "dept": "HDW",
        "vendor": 4,
        "price": 4.99,
        "cost": 2.30,
        "qty": 100,
        "min": 30,
        "unit": "each",
        "product": "Door Hardware",
        "vendor_sku": "FA-HNG-3SN",
    },
    {
        "name": "Door Knob Passage Satin Nickel",
        "dept": "HDW",
        "vendor": 4,
        "price": 19.99,
        "cost": 10.50,
        "qty": 30,
        "min": 10,
        "unit": "each",
        "product": "Door Hardware",
        "vendor_sku": "FA-DK-PSN",
    },
    {
        "name": "Deadbolt Single Cyl Satin Nickel",
        "dept": "HDW",
        "vendor": 4,
        "price": 34.99,
        "cost": 18.00,
        "qty": 20,
        "min": 8,
        "unit": "each",
        "product": "Door Hardware",
        "vendor_sku": "FA-DB-SSN",
    },
    {
        "name": "Construction Adhesive 10oz",
        "dept": "HDW",
        "vendor": 4,
        "price": 5.99,
        "cost": 2.80,
        "qty": 60,
        "min": 20,
        "unit": "each",
        "vendor_sku": "FA-CA-10",
    },
    # Multi-vendor items (FastenAll also carries paint supplies)
    {
        "name": "2in Angle Sash Brush",
        "dept": "PNT",
        "vendor": 4,
        "price": 7.99,
        "cost": 3.50,
        "qty": 40,
        "min": 15,
        "unit": "each",
        "product": "Paint Brushes",
        "vendor_sku": "FA-BR-2AS",
    },
    {
        "name": "Painters Tape Blue 1.88in x 60yd",
        "dept": "PNT",
        "vendor": 4,
        "price": 6.99,
        "cost": 3.50,
        "qty": 50,
        "min": 20,
        "unit": "roll",
        "vendor_sku": "FA-TPB-188",
    },
    {
        "name": "Electrical Tape Black 3/4in",
        "dept": "ELE",
        "vendor": 4,
        "price": 2.99,
        "cost": 1.20,
        "qty": 60,
        "min": 20,
        "unit": "roll",
        "vendor_sku": "FA-ET-BK",
    },
    # === TOOLS (Pro Tool Warehouse) ===
    {
        "name": "20V Cordless Drill Kit",
        "dept": "TOL",
        "vendor": 5,
        "price": 129.99,
        "cost": 78.00,
        "qty": 8,
        "min": 3,
        "unit": "each",
        "vendor_sku": "PT-DRL-20V",
    },
    {
        "name": "25ft Tape Measure",
        "dept": "TOL",
        "vendor": 5,
        "price": 14.99,
        "cost": 7.50,
        "qty": 25,
        "min": 10,
        "unit": "each",
        "vendor_sku": "PT-TM-25",
    },
    {
        "name": "Speed Square 7in",
        "dept": "TOL",
        "vendor": 5,
        "price": 9.99,
        "cost": 5.00,
        "qty": 20,
        "min": 8,
        "unit": "each",
        "vendor_sku": "PT-SQ-7",
    },
    {
        "name": "Utility Knife Retractable",
        "dept": "TOL",
        "vendor": 5,
        "price": 7.99,
        "cost": 3.80,
        "qty": 35,
        "min": 12,
        "unit": "each",
        "vendor_sku": "PT-UK-R",
    },
    {
        "name": "Framing Hammer 22oz",
        "dept": "TOL",
        "vendor": 5,
        "price": 24.99,
        "cost": 13.00,
        "qty": 15,
        "min": 5,
        "unit": "each",
        "vendor_sku": "PT-HM-22",
    },
    {
        "name": "Chalk Line Kit 100ft",
        "dept": "TOL",
        "vendor": 5,
        "price": 11.99,
        "cost": 6.00,
        "qty": 18,
        "min": 6,
        "unit": "each",
        "vendor_sku": "PT-CL-100",
    },
    {
        "name": "Level 48in Aluminum",
        "dept": "TOL",
        "vendor": 5,
        "price": 34.99,
        "cost": 19.00,
        "qty": 10,
        "min": 4,
        "unit": "each",
        "vendor_sku": "PT-LV-48",
    },
]

WITHDRAWAL_SCENARIOS = [
    {
        "job_id": "JOB-2026-0041",
        "service_address": "1420 Oak Valley Dr",
        "days_ago": 12,
        "items": [
            ("2x4x8 Stud SPF", 40),
            ("4x8 1/2in CDX Plywood", 8),
            ("#8 x 2-1/2in Deck Screw 5lb", 3),
            ("16d Framing Nail 50lb", 1),
        ],
    },
    {
        "job_id": "JOB-2026-0041",
        "service_address": "1420 Oak Valley Dr",
        "days_ago": 9,
        "items": [
            ("12/2 NM-B Romex 250ft", 2),
            ("Single Gang Old Work Box", 12),
            ("Decora Switch White", 8),
            ("Decora Outlet 15A White", 10),
            ("GFCI Outlet 15A White", 3),
            ("Wire Nuts Assorted 100pk", 2),
        ],
    },
    {
        "job_id": "JOB-2026-0043",
        "service_address": "890 Maple Creek Ln",
        "days_ago": 7,
        "items": [
            ("1/2in PEX Pipe 100ft", 3),
            ("SharkBite 1/2in Push Fitting", 8),
            ("1/2in Copper Elbow 90deg", 15),
            ("Teflon Tape 1/2in x 520in", 5),
            ("PVC Cement 16oz", 2),
        ],
    },
    {
        "job_id": "JOB-2026-0044",
        "service_address": "2250 Birch Hill Ct",
        "days_ago": 5,
        "items": [
            ("5 Gal Interior Flat White", 3),
            ("Primer 5 Gal", 2),
            ("2in Angle Sash Brush", 6),
            ("9in Roller Cover 3/8nap 3pk", 4),
            ("Painters Tape Blue 1.88in x 60yd", 8),
        ],
    },
    {
        "job_id": "JOB-2026-0041",
        "service_address": "1420 Oak Valley Dr",
        "days_ago": 3,
        "items": [
            ("2x4x8 Stud SPF", 20),
            ("2x6x12 Douglas Fir", 10),
            ("Construction Adhesive 10oz", 4),
        ],
    },
    {
        "job_id": "JOB-2026-0045",
        "service_address": "505 Elm Park Way",
        "days_ago": 1,
        "items": [
            ("1x6x8 Cedar Fence Board", 80),
            ("4x4x8 Post Treated", 6),
            ("#8 x 2-1/2in Deck Screw 5lb", 4),
        ],
    },
]


async def main():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from shared.infrastructure.database import get_connection, init_db

    await init_db()

    from catalog.application.queries import list_departments
    from catalog.application.sku_lifecycle import create_product_with_sku
    from catalog.application.vendor_item_lifecycle import add_vendor_item
    from catalog.infrastructure.vendor_repo import vendor_repo
    from finance.application.invoice_service import create_invoice_from_withdrawals
    from inventory.application.inventory_service import process_import_stock_changes
    from operations.domain.withdrawal import MaterialWithdrawal, WithdrawalItem
    from operations.infrastructure.withdrawal_repo import withdrawal_repo
    from shared.infrastructure.database import get_connection as _get_conn

    org_id = "default"
    conn = get_connection()

    cur = await conn.execute("SELECT COUNT(*) FROM skus WHERE organization_id = ?", (org_id,))
    count = (await cur.fetchone())[0]
    if count > 5:
        logger.info("Already have %d SKUs — skipping seed. Delete DB to re-seed.", count)
        return

    _c = _get_conn()
    _cur = await _c.execute("SELECT * FROM users WHERE email = ?", ("admin@demo.local",))
    _row = await _cur.fetchone()
    admin = dict(_row) if _row and hasattr(_row, "keys") else None
    _cur = await _c.execute("SELECT * FROM users WHERE email = ?", ("contractor@demo.local",))
    _row = await _cur.fetchone()
    contractor = dict(_row) if _row and hasattr(_row, "keys") else None
    if not admin or not contractor:
        logger.error("Demo users not found. Start the server first to run seed_mock_user().")
        return

    departments = await list_departments()
    dept_by_code = {d.code: d for d in departments}
    if not dept_by_code:
        logger.error(
            "No departments found. Start the server first to run seed_standard_departments()."
        )
        return

    # 1. Create vendors
    logger.info("--- Creating vendors ---")
    vendor_ids = []
    for v in VENDORS:
        vid = str(uuid4())
        vendor_ids.append(vid)
        await vendor_repo.insert(
            {
                "id": vid,
                **v,
                "created_at": datetime.now(UTC).isoformat(),
                "organization_id": org_id,
            }
        )
        logger.info("  Vendor: %s", v["name"])

    # 2. Create products + SKUs + vendor items
    logger.info("--- Creating products & SKUs ---")
    sku_map = {}  # name -> first SKU created (for withdrawals)

    for p in PRODUCTS:
        dept = dept_by_code.get(p["dept"])
        if not dept:
            logger.warning("  Skipping %s: dept %s not found", p["name"], p["dept"])
            continue
        vid = vendor_ids[p["vendor"]]
        vname = VENDORS[p["vendor"]]["name"]

        # If this is a multi-vendor duplicate (same name already created), just add a VendorItem
        if p["name"] in sku_map:
            existing_sku = sku_map[p["name"]]
            await add_vendor_item(
                sku_id=existing_sku.id,
                vendor_id=vid,
                vendor_sku=p.get("vendor_sku"),
                purchase_uom=p.get("purchase_uom", p["unit"]),
                purchase_pack_qty=p.get("purchase_pack_qty", 1),
                cost=p["cost"],
                is_preferred=False,
            )
            logger.info("  + VendorItem: %s → %s (%s)", p["name"], vname, p.get("vendor_sku", ""))
            continue

        try:
            sku = await create_product_with_sku(
                category_id=dept.id,
                category_name=dept.name,
                name=p["name"],
                price=p["price"],
                cost=p["cost"],
                quantity=p["qty"],
                min_stock=p["min"],
                base_unit=p["unit"],
                sell_uom=p["unit"],
                purchase_uom=p.get("purchase_uom", p["unit"]),
                purchase_pack_qty=p.get("purchase_pack_qty", 1),
                user_id=admin["id"],
                user_name=admin.get("name", "Admin"),
                on_stock_import=process_import_stock_changes,
            )
            sku_map[p["name"]] = sku

            # Create vendor item for the primary vendor
            await add_vendor_item(
                sku_id=sku.id,
                vendor_id=vid,
                vendor_sku=p.get("vendor_sku"),
                purchase_uom=p.get("purchase_uom", p["unit"]),
                purchase_pack_qty=p.get("purchase_pack_qty", 1),
                cost=p["cost"],
                is_preferred=True,
            )

            logger.info(
                "  %s | %s | qty=%d | %s (%s)",
                sku.sku,
                p["name"],
                p["qty"],
                vname,
                p.get("vendor_sku", ""),
            )
        except (ValueError, RuntimeError, OSError) as e:
            logger.warning("  Skip %s: %s", p["name"], e)

    logger.info("--- %d unique SKUs created ---", len(sku_map))

    # 3. Create withdrawals
    logger.info("--- Creating withdrawals ---")
    now = datetime.now(UTC)
    withdrawal_ids = []

    for scenario in WITHDRAWAL_SCENARIOS:
        items = []
        for prod_name, qty in scenario["items"]:
            sku = sku_map.get(prod_name)
            if not sku:
                logger.warning("  Withdrawal skip: SKU '%s' not found", prod_name)
                continue
            items.append(
                WithdrawalItem(
                    product_id=sku.id,
                    sku=sku.sku,
                    name=sku.name,
                    quantity=qty,
                    price=sku.price,
                    cost=sku.cost,
                    subtotal=round(sku.price * qty, 2),
                )
            )

        if not items:
            continue

        created_at = (now - timedelta(days=scenario["days_ago"])).isoformat()
        withdrawal = MaterialWithdrawal(
            items=items,
            job_id=scenario["job_id"],
            service_address=scenario["service_address"],
            notes="",
            subtotal=0,
            tax=0,
            total=0,
            cost_total=0,
            contractor_id=contractor["id"],
            contractor_name=contractor.get("name", ""),
            contractor_company=contractor.get("company", ""),
            billing_entity=contractor.get("billing_entity", "Demo Co"),
            payment_status="unpaid",
            processed_by_id=admin["id"],
            processed_by_name=admin.get("name", ""),
        )
        withdrawal.compute_totals()

        w_dict = withdrawal.model_dump()
        w_dict["organization_id"] = org_id
        w_dict["created_at"] = created_at
        await withdrawal_repo.insert(w_dict)
        withdrawal_ids.append(withdrawal.id)

        for item in items:
            await conn.execute(
                "UPDATE skus SET quantity = MAX(0, quantity - ?), updated_at = ? WHERE id = ?",
                (item.quantity, created_at, item.product_id),
            )
        await conn.commit()

        item_summary = ", ".join(f"{i.name} x{i.quantity}" for i in items[:3])
        if len(items) > 3:
            item_summary += f" +{len(items) - 3} more"
        logger.info(
            "  %s @ %s | $%.2f | %s",
            scenario["job_id"],
            scenario["service_address"][:25],
            withdrawal.total,
            item_summary,
        )

    # 4. Create invoices from some withdrawals
    logger.info("--- Creating invoices ---")
    if len(withdrawal_ids) >= 4:
        for wid in withdrawal_ids[:4]:
            try:
                inv = await create_invoice_from_withdrawals([wid], organization_id=org_id)
                logger.info("  Invoice %s... for withdrawal %s...", inv["id"][:8], wid[:8])
            except (ValueError, RuntimeError, OSError) as e:
                logger.warning("  Invoice skip: %s", e)

        for wid in withdrawal_ids[:2]:
            try:
                paid_at = (now - timedelta(days=5)).isoformat()
                await withdrawal_repo.mark_paid(wid, paid_at)
                logger.info("  Marked withdrawal %s... as paid", wid[:8])
            except (ValueError, RuntimeError, OSError) as e:
                logger.warning("  Mark paid skip: %s", e)

    # 5. Make a few SKUs critically low to trigger alerts
    logger.info("--- Setting low-stock alerts ---")
    low_stock_names = [
        "4x8 3/4in Sanded Plywood",
        "GFCI Outlet 15A White",
        "5 Gal Interior Eggshell White",
        "20V Cordless Drill Kit",
    ]
    for name in low_stock_names:
        sku = sku_map.get(name)
        if sku:
            low_qty = _rng.randint(1, sku.min_stock)
            await conn.execute("UPDATE skus SET quantity = ? WHERE id = ?", (low_qty, sku.id))
            logger.info("  %s | %s → qty=%d (min=%d)", sku.sku, name, low_qty, sku.min_stock)
    await conn.commit()

    # Summary
    cur = await conn.execute("SELECT COUNT(*) FROM skus WHERE organization_id = ?", (org_id,))
    total_skus = (await cur.fetchone())[0]
    cur = await conn.execute("SELECT COUNT(*) FROM products WHERE organization_id = ?", (org_id,))
    total_products = (await cur.fetchone())[0]
    cur = await conn.execute(
        "SELECT COUNT(*) FROM vendor_items WHERE organization_id = ?", (org_id,)
    )
    total_vendor_items = (await cur.fetchone())[0]
    cur = await conn.execute("SELECT COUNT(*) FROM vendors WHERE organization_id = ?", (org_id,))
    total_vendors = (await cur.fetchone())[0]
    cur = await conn.execute(
        "SELECT COUNT(*) FROM withdrawals WHERE organization_id = ?", (org_id,)
    )
    total_withdrawals = (await cur.fetchone())[0]
    cur = await conn.execute("SELECT COUNT(*) FROM invoices WHERE organization_id = ?", (org_id,))
    total_invoices = (await cur.fetchone())[0]

    logger.info("\n=== SEED COMPLETE ===")
    logger.info("  %d vendors", total_vendors)
    logger.info(
        "  %d products (parent), %d SKUs, %d vendor items",
        total_products,
        total_skus,
        total_vendor_items,
    )
    logger.info("  %d withdrawals", total_withdrawals)
    logger.info("  %d invoices", total_invoices)
    logger.info("  Login: admin@demo.local / demo123")
    logger.info("  Login: contractor@demo.local / demo123")


if __name__ == "__main__":
    asyncio.run(main())
