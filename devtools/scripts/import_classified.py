"""Import products from classified_products.json into the database.

Reads the LLM-classified JSON (from classify_products.py), creates
ProductFamilies first, then SKUs under them with proper variant attrs.

Usage:
    # Dry run — show what would be created
    PYTHONPATH=backend:. uv run python -m devtools.scripts.import_classified --dry-run

    # Import for real (nukes existing catalog data first)
    PYTHONPATH=backend:. uv run python -m devtools.scripts.import_classified --nuke

    # Import vendors first, then products
    PYTHONPATH=backend:. uv run python -m devtools.scripts.import_classified --nuke --vendors
"""

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "real"
CLASSIFIED_PATH = DATA_DIR / "classified_products.json"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", str(text)).strip()
    return "" if clean in ("-", "") else clean


def build_family_groups(products: list[dict]) -> dict[str, list[dict]]:
    """Group products by (department, family_name) → list of SKU entries."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in products:
        key = f"{p['department']}|{p['family_name']}"
        groups[key].append(p)
    return dict(sorted(groups.items()))


async def nuke_catalog() -> None:
    """Hard-delete all catalog data to start fresh."""
    from shared.infrastructure.db import get_connection

    db = get_connection()
    # Order matters for FK constraints
    tables = [
        "vendor_items",
        "stock_transactions",
        "skus",
        "products",
        "sku_counters",
    ]
    for table in tables:
        await db.execute(f"DELETE FROM {table}")
    # Reset department sku_count
    await db.execute("UPDATE departments SET sku_count = 0")
    await db.commit()
    print("Nuked existing catalog data (hard-deleted all rows, reset counters)")


async def import_vendors() -> dict[str, str]:
    """Import vendors from Supplier.xlsx. Returns {company_name: vendor_id}."""
    from devtools.scripts.import_hike import import_vendors as _import_vendors

    return await _import_vendors()


async def import_classified(classified_path: Path, dry_run: bool = False) -> None:
    """Import classified products, creating families then SKUs."""
    from catalog.application.product_family_lifecycle import create_product
    from catalog.application.sku_lifecycle import create_sku
    from catalog.domain.vendor_item import VendorItem
    from catalog.infrastructure.department_repo import department_repo
    from catalog.infrastructure.vendor_item_repo import vendor_item_repo
    from catalog.infrastructure.vendor_repo import vendor_repo
    from inventory.application.inventory_service import process_import_stock_changes
    from shared.infrastructure.logging_config import org_id_var

    data = json.loads(classified_path.read_text())
    products = data["products"]
    now = datetime.now(UTC).isoformat()

    # Build lookups
    all_depts = await department_repo.list_all()
    dept_by_name = {d.name: d for d in all_depts}

    all_vendors = await vendor_repo.list_all()
    vendor_map = {v.name: v.id for v in all_vendors}

    # Group into families
    family_groups = build_family_groups(products)

    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"DRY RUN — would create {len(family_groups)} families from {len(products)} products")
        print(f"{'=' * 60}\n")
        for key, members in family_groups.items():
            dept, fname = key.split("|", 1)
            print(f"  Family: {fname} [{dept}] ({len(members)} SKUs)")
            for m in members:
                vl = m.get("variant_label", "")
                bu = m.get("base_unit", "each")
                print(f"    - {m['name']}" + (f"  [variant: {vl}]" if vl else "") + f"  unit={bu}")
        return

    families_created = 0
    skus_created = 0
    vendor_items_created = 0
    errors: list[str] = []

    for key, members in family_groups.items():
        dept_name, family_name = key.split("|", 1)
        dept = dept_by_name.get(dept_name)
        if not dept:
            dept = dept_by_name.get("Miscellaneous")
        if not dept:
            errors.append(f"Unknown department: {dept_name}")
            continue

        # Create the ProductFamily
        try:
            family = await create_product(
                name=family_name,
                category_id=dept.id,
                category_name=dept.name,
                description="",
            )
            families_created += 1
        except Exception as e:
            errors.append(f"Family '{family_name}' [{dept_name}]: {e}")
            continue

        # Create each SKU under this family
        for item in members:
            barcode = item.get("barcode")
            # Skip barcodes that will fail check-digit validation
            if barcode and barcode.isdigit():
                if len(barcode) not in (12, 13):
                    barcode = None
                else:
                    # Validate check digit — skip if invalid
                    digits = [int(d) for d in barcode]
                    if len(digits) == 12:
                        check = (
                            10
                            - sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:11])) % 10
                        ) % 10
                        if check != digits[11]:
                            barcode = None
                    elif len(digits) == 13:
                        check = (
                            10
                            - sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:12])) % 10
                        ) % 10
                        if check != digits[12]:
                            barcode = None

            description = _strip_html(item.get("description"))
            qty = item.get("quantity", 0)
            item_base_unit = item.get("base_unit", "each")

            async def on_stock_import(
                sku_id: str,
                sku: str,
                product_name: str,
                quantity: float,
                user_id: str,
                user_name: str,
                _unit: str = item_base_unit,
            ):
                await process_import_stock_changes(
                    sku_id=sku_id,
                    sku=sku,
                    product_name=product_name,
                    quantity=quantity,
                    user_id=user_id,
                    user_name=user_name,
                    unit=_unit,
                )

            try:
                sku = await create_sku(
                    product_family_id=family.id,
                    category_id=dept.id,
                    category_name=dept.name,
                    name=item["name"],
                    description=description,
                    price=item.get("price", 0),
                    cost=item.get("cost", 0),
                    quantity=qty,
                    min_stock=item.get("min_stock", 0),
                    barcode=barcode,
                    base_unit=item.get("base_unit", "each"),
                    sell_uom=item.get("sell_uom", "each"),
                    pack_qty=item.get("pack_qty", 1),
                    variant_label=item.get("variant_label", ""),
                    variant_attrs=item.get("variant_attrs", {}),
                    spec=item.get("spec", ""),
                    grade=item.get("grade", ""),
                    user_id="import",
                    user_name="Hike Import",
                    on_stock_import=on_stock_import if qty > 0 else None,
                )
                skus_created += 1

                # Link vendor item
                supplier = item.get("supplier")
                vendor_sku = item.get("vendor_sku")
                vendor_id = vendor_map.get(supplier) if supplier else None

                if vendor_id and vendor_sku:
                    from shared.kernel.units import ALLOWED_BASE_UNITS

                    vi_uom = item.get("base_unit", "each")
                    if vi_uom not in ALLOWED_BASE_UNITS:
                        vi_uom = "each"

                    vi = VendorItem(
                        vendor_id=vendor_id,
                        vendor_name=supplier,
                        sku_id=sku.id,
                        vendor_sku=vendor_sku,
                        cost=item.get("cost", 0),
                        purchase_uom=vi_uom,
                        purchase_pack_qty=item.get("pack_qty", 1),
                        is_preferred=True,
                        organization_id=org_id_var.get(),
                        created_at=now,
                        updated_at=now,
                    )
                    await vendor_item_repo.insert(vi)
                    vendor_items_created += 1

            except Exception as e:
                errors.append(f"SKU '{item['name']}' row {item.get('row')}: {e}")

        if families_created % 50 == 0 and families_created > 0:
            print(f"  ... {families_created} families, {skus_created} SKUs created")

    print("\nDone:")
    print(f"  Families created:     {families_created}")
    print(f"  SKUs created:         {skus_created}")
    print(f"  Vendor items linked:  {vendor_items_created}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors[:30]:
            print(f"  {err}")
        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} more")


async def main(nuke: bool, vendors: bool, dry_run: bool, classified_path: Path) -> None:
    from devtools.scripts.company import ORG
    from shared.infrastructure.db import close_db, init_db
    from shared.infrastructure.logging_config import org_id_var, user_id_var

    if not classified_path.exists():
        print(f"Error: {classified_path} not found. Run classify_products.py first.")
        sys.exit(1)

    await init_db()
    org_id_var.set(ORG.id)
    user_id_var.set("import")

    try:
        if nuke and not dry_run:
            await nuke_catalog()

        if vendors and not dry_run:
            await import_vendors()

        await import_classified(classified_path, dry_run=dry_run)

        print("\nDone.")
    finally:
        await close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import classified products into DB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    parser.add_argument("--nuke", action="store_true", help="Soft-delete existing catalog first")
    parser.add_argument("--vendors", action="store_true", help="Import vendors from Supplier.xlsx")
    parser.add_argument(
        "--input",
        type=Path,
        default=CLASSIFIED_PATH,
        help=f"Classified JSON path (default: {CLASSIFIED_PATH})",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.nuke:
        print("Error: specify --nuke to clear existing data, or --dry-run to preview")
        sys.exit(1)

    asyncio.run(main(args.nuke, args.vendors, args.dry_run, args.input))
