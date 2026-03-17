"""LLM-augmented product family classification for Hike POS data.

Reads Products 2.xlsx, sends products to Claude in department batches,
and outputs a classified_products.json for human review before import.

Usage:
    # Classify all products (calls Claude API)
    uv run --with openpyxl python -m devtools.scripts.classify_products

    # Classify only specific departments (for testing)
    uv run --with openpyxl python -m devtools.scripts.classify_products --dept "Drywall Mud" --dept "Light Bulbs"

    # Show stats from an existing classification file
    uv run --with openpyxl python -m devtools.scripts.classify_products --stats

Requires ANTHROPIC_API_KEY in environment.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic
import openpyxl

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "real"
OUTPUT_PATH = DATA_DIR / "classified_products.json"

# ── Department code lookup ───────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))
from devtools.scripts.company import DEPT_CODE_BY_NAME  # noqa: E402

# ── XLSX extraction ──────────────────────────────────────────────────────────


def load_products(xlsx_path: Path) -> list[dict]:
    """Load all products from the Hike export with fields relevant to classification."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = rows[0]
    products = []

    for i, row in enumerate(rows[1:], start=2):
        data = dict(zip(headers, row, strict=False))
        name = (data.get("Name") or "").strip()
        if not name:
            continue

        product_type = (data.get("Product type") or "").strip()
        cost = float(data.get("Pittsburgh Store_Cost price") or 0)
        price_ex = float(data.get("Pittsburgh Store_Price Excluding Tax") or 0)
        price = price_ex if price_ex > 0 else float(data.get("Pittsburgh Store_Retail price") or 0)
        qty = float(
            data.get("Pittsburgh Store_Stock on hand") or data.get("Pittsburgh Store_Stock") or 0
        )
        min_stock = int(float(data.get("Pittsburgh Store_Reorder level") or 0))

        barcode_raw = str(data.get("Barcode") or "").strip()
        barcode = barcode_raw or None

        vendor_sku = str(data.get("SKU") or "").strip() or None
        supplier = (data.get("Supplier name") or "").strip() or None
        description = (data.get("Description") or "").strip() or None

        products.append(
            {
                "row": i,
                "name": name,
                "department": product_type,
                "price": price,
                "cost": cost,
                "quantity": qty,
                "min_stock": min_stock,
                "barcode": barcode,
                "vendor_sku": vendor_sku,
                "supplier": supplier,
                "description": description,
            }
        )

    wb.close()
    return products


def group_by_department(products: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for p in products:
        dept = p["department"] or "(uncategorized)"
        groups.setdefault(dept, []).append(p)
    return dict(sorted(groups.items()))


# ── LLM classification ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a hardware store materials expert and data engineer. Your job is to \
classify products from a hardware store's POS export into logical Product Families.

A Product Family groups items that are essentially the same product in different \
sizes, quantities, pack counts, or variants. Customers would think of them as \
"the same thing, different option."

GROUPING RULES:
1. Same base product, different sizes → ONE family
   e.g. "1/2\" Pex Elbows 65pk" and "3/4\" Pex Elbows 40pk" → family "Pex Elbows"
2. Same base product, different pack quantities → ONE family
   e.g. "Drywall Screws #6x1-5/8\" 1lb" and "Drywall Screws #6x2\" 1lb" → family "Drywall Screws Coarse #6"
3. Same product line, different set times/formulas → ONE family
   e.g. "Easy Sand 5", "Easy Sand 20", "Easy Sand 45" → family "Easy Sand"
4. Same brand product, different sizes/capacities → ONE family
   e.g. "Joint Compound All Purpose 1.75pt Sheetrock" and "Joint Compound All Purpose 3.5qt Sheetrock" → family "Sheetrock All Purpose Joint Compound"
5. Different product types even if same brand → SEPARATE families
   e.g. "Gorilla Wood Glue" and "Gorilla Duct Tape" → separate families
6. Different fittings/shapes even if same material+size → SEPARATE families
   e.g. "1/2\" Pex Elbows" vs "1/2\" Pex Tees" vs "1/2\" Pex Couplings" → separate families
7. Products that are truly unique with no variants → family of ONE (that's fine)

FOR EACH PRODUCT, extract:
- family_name: A clean, canonical name for the product family (the name you'd see on a store shelf label)
- brand: The brand/manufacturer if identifiable from the name (e.g. "Sheetrock", "Milwaukee", "3M", "Gorilla"). Empty string if unclear.
- variant_label: What makes THIS SKU different from siblings (e.g. "45", "1/2\" 65pk", "XL", "32oz"). Empty string if it's the only one in the family.
- variant_attrs: Structured key-value pairs for the variant dimensions. Use consistent keys like: size, pack, length, width, color, wattage, weight, volume, grit, gauge, setting_time, capacity, material. Only include attrs that vary between siblings.
- base_unit: The fundamental unit of inventory ("each", "box", "roll", "bag", "can", "bottle", "tube", "gallon", "quart", "pair", "set", "foot", "sheet")
- sell_uom: What it's sold as (usually same as base_unit, but "pack" if sold as multi-pack)
- pack_qty: If sell_uom differs from base_unit, how many base units per sell unit (default 1)

RESPOND WITH ONLY valid JSON — an array of objects, one per input product, in the \
same order as the input. Each object has the fields above plus the original "name" field for alignment."""


def build_department_prompt(dept_name: str, products: list[dict]) -> str:
    """Build the user prompt for one department batch."""
    lines = [f"Department: {dept_name}", f"Products ({len(products)}):", ""]
    for i, p in enumerate(products, 1):
        lines.append(f"{i}. {p['name']}")
    return "\n".join(lines)


CHUNK_SIZE = 50  # Max products per API call to avoid output truncation


def classify_batch(
    client: anthropic.Anthropic,
    dept_name: str,
    products: list[dict],
) -> list[dict]:
    """Send one batch to Claude and parse the classification."""
    user_prompt = build_department_prompt(dept_name, products)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16384,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

    try:
        classifications = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  !! JSON parse error for {dept_name}: {e}")
        print(f"  !! Raw response (first 500 chars): {text[:500]}")
        return [{"error": "parse_failed"} for _ in products]

    if len(classifications) != len(products):
        print(
            f"  !! Count mismatch for {dept_name}: "
            f"got {len(classifications)}, expected {len(products)}"
        )

    return classifications


def classify_department(
    client: anthropic.Anthropic,
    dept_name: str,
    products: list[dict],
) -> list[dict]:
    """Classify a department, chunking large ones to avoid output truncation."""
    if len(products) <= CHUNK_SIZE:
        return classify_batch(client, dept_name, products)

    # Chunk large departments
    all_results: list[dict] = []
    chunks = [products[i : i + CHUNK_SIZE] for i in range(0, len(products), CHUNK_SIZE)]
    for ci, chunk in enumerate(chunks, 1):
        print(f"chunk {ci}/{len(chunks)} ({len(chunk)})...", end=" ", flush=True)
        results = classify_batch(client, dept_name, chunk)
        all_results.extend(results)
        if ci < len(chunks):
            time.sleep(0.5)  # Brief pause between chunks
    return all_results


# ── Merge classifications back into product data ─────────────────────────────


def merge_classification(product: dict, classification: dict) -> dict:
    """Combine the original product data with LLM classification."""
    return {
        # Original data (preserved for import)
        "row": product["row"],
        "name": product["name"],
        "department": product["department"],
        "department_code": DEPT_CODE_BY_NAME.get(product["department"], "MSC"),
        "price": product["price"],
        "cost": product["cost"],
        "quantity": product["quantity"],
        "min_stock": product["min_stock"],
        "barcode": product["barcode"],
        "vendor_sku": product["vendor_sku"],
        "supplier": product["supplier"],
        "description": product["description"],
        # LLM classification
        "family_name": classification.get("family_name", product["name"]),
        "brand": classification.get("brand", ""),
        "variant_label": classification.get("variant_label", ""),
        "variant_attrs": classification.get("variant_attrs", {}),
        "base_unit": classification.get("base_unit", "each"),
        "sell_uom": classification.get("sell_uom", "each"),
        "pack_qty": classification.get("pack_qty", 1),
    }


# ── Stats ────────────────────────────────────────────────────────────────────


def print_stats(data: dict) -> None:
    """Print summary statistics from a classification file."""
    products = data["products"]
    families: dict[str, list] = {}
    for p in products:
        key = f"{p['department']}|{p['family_name']}"
        families.setdefault(key, []).append(p)

    total_products = len(products)
    total_families = len(families)
    solo_families = sum(1 for members in families.values() if len(members) == 1)
    multi_families = total_families - solo_families
    largest = max(families.items(), key=lambda x: len(x[1]))

    print(f"\n{'=' * 60}")
    print("Classification Summary")
    print(f"{'=' * 60}")
    print(f"Total products:        {total_products}")
    print(f"Total families:        {total_families}")
    print(f"Multi-SKU families:    {multi_families}")
    print(f"Single-SKU families:   {solo_families}")
    print(f"Avg SKUs per family:   {total_products / total_families:.1f}")
    print(f"Largest family:        {largest[0].split('|')[1]} ({len(largest[1])} SKUs)")

    # Per-department breakdown
    dept_stats: dict[str, dict] = {}
    for key, members in families.items():
        dept = key.split("|")[0]
        ds = dept_stats.setdefault(dept, {"products": 0, "families": 0, "multi": 0})
        ds["products"] += len(members)
        ds["families"] += 1
        if len(members) > 1:
            ds["multi"] += 1

    print(f"\n{'Department':<30} {'Products':>8} {'Families':>8} {'Multi':>6} {'Ratio':>6}")
    print("-" * 60)
    for dept in sorted(dept_stats, key=lambda d: dept_stats[d]["products"], reverse=True):
        ds = dept_stats[dept]
        ratio = ds["products"] / ds["families"]
        print(f"{dept:<30} {ds['products']:>8} {ds['families']:>8} {ds['multi']:>6} {ratio:>6.1f}")

    # Show multi-SKU families
    print(f"\n{'=' * 60}")
    print("Multi-SKU Families (showing up to 30)")
    print(f"{'=' * 60}")
    multi = sorted(
        [(k, v) for k, v in families.items() if len(v) > 1],
        key=lambda x: len(x[1]),
        reverse=True,
    )
    for key, members in multi[:30]:
        dept, fname = key.split("|", 1)
        print(f"\n  {fname} [{dept}] ({len(members)} SKUs)")
        for m in members:
            vl = m.get("variant_label", "")
            print(f"    - {m['name']}" + (f"  →  variant: {vl}" if vl else ""))


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="LLM-augmented product family classification")
    parser.add_argument(
        "--dept",
        action="append",
        help="Only classify specific department(s). Can be repeated.",
    )
    parser.add_argument("--stats", action="store_true", help="Show stats from existing output file")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-classify only products that failed in a previous run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output JSON path (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    # Stats mode — just read existing file
    if args.stats:
        if not args.output.exists():
            print(f"No classification file at {args.output}")
            return
        data = json.loads(args.output.read_text())
        print_stats(data)
        return

    # Classification mode
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Retry-failed mode: re-classify only failed products from previous run
    if args.retry_failed:
        if not args.output.exists():
            print(f"No existing file at {args.output} to retry from")
            sys.exit(1)

        existing = json.loads(args.output.read_text())
        failed_rows: set[int] = set()
        ok_products: list[dict] = []
        failed_products: list[dict] = []

        for p in existing["products"]:
            if p.get("_review") in ("parse_failed", "api_error"):
                failed_rows.add(p["row"])
                # Reconstruct source product from the classified entry
                failed_products.append(p)
            else:
                ok_products.append(p)

        print(f"Found {len(failed_products)} failed products to retry, {len(ok_products)} OK\n")

        if not failed_products:
            print("Nothing to retry!")
            return

        by_dept = group_by_department(failed_products)
        client = anthropic.Anthropic(api_key=api_key)
        reclassified: list[dict] = []
        errors: list[str] = []

        for dept_name, dept_products in by_dept.items():
            n = len(dept_products)
            print(f"  {dept_name} ({n} products)...", end=" ", flush=True)
            t0 = time.time()

            try:
                classifications = classify_department(client, dept_name, dept_products)
                for product, cls in zip(dept_products, classifications, strict=False):
                    if cls.get("error"):
                        merged = merge_classification(product, {})
                        merged["_review"] = "parse_failed"
                        reclassified.append(merged)
                        errors.append(f"Row {product['row']}: {product['name']} — still failed")
                    else:
                        reclassified.append(merge_classification(product, cls))

                elapsed = time.time() - t0
                print(f"done ({elapsed:.1f}s)")
            except Exception as e:
                print(f"ERROR: {e}")
                for product in dept_products:
                    merged = merge_classification(product, {})
                    merged["_review"] = "api_error"
                    reclassified.append(merged)
                errors.append(f"{dept_name}: API error — {e}")

        # Merge back: ok_products + reclassified, sorted by row
        all_products = ok_products + reclassified
        all_products.sort(key=lambda p: p["row"])

        output = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_products": len(all_products),
            "departments": existing["departments"],
            "products": all_products,
        }
        args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"\nWrote {args.output}")

        if errors:
            print(f"\nErrors ({len(errors)}):")
            for err in errors:
                print(f"  {err}")

        print_stats(output)
        return

    # Full classification mode
    xlsx_path = DATA_DIR / "Products 2.xlsx"
    if not xlsx_path.exists():
        print(f"Error: {xlsx_path} not found")
        sys.exit(1)

    print(f"Loading products from {xlsx_path}...")
    products = load_products(xlsx_path)
    print(f"Loaded {len(products)} products")

    by_dept = group_by_department(products)
    if args.dept:
        by_dept = {d: ps for d, ps in by_dept.items() if d in args.dept}
        if not by_dept:
            print(f"No products found in departments: {args.dept}")
            sys.exit(1)

    print(
        f"Classifying {sum(len(ps) for ps in by_dept.values())} products across {len(by_dept)} departments\n"
    )

    client = anthropic.Anthropic(api_key=api_key)
    all_classified: list[dict] = []
    errors: list[str] = []

    for dept_name, dept_products in by_dept.items():
        n = len(dept_products)
        print(f"  {dept_name} ({n} products)...", end=" ", flush=True)
        t0 = time.time()

        try:
            classifications = classify_department(client, dept_name, dept_products)

            for product, cls in zip(dept_products, classifications, strict=False):
                if cls.get("error"):
                    merged = merge_classification(product, {})
                    merged["_review"] = "parse_failed"
                    all_classified.append(merged)
                    errors.append(f"Row {product['row']}: {product['name']} — parse failed")
                else:
                    all_classified.append(merge_classification(product, cls))

            elapsed = time.time() - t0
            print(f"done ({elapsed:.1f}s)")

        except Exception as e:
            print(f"ERROR: {e}")
            for product in dept_products:
                merged = merge_classification(product, {})
                merged["_review"] = "api_error"
                all_classified.append(merged)
            errors.append(f"{dept_name}: API error — {e}")

    # Build output
    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_products": len(all_classified),
        "departments": len(by_dept),
        "products": all_classified,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nWrote {args.output}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  {err}")

    print_stats(output)


if __name__ == "__main__":
    main()
