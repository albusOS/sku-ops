"""
Enhance the Supply Yard CSV with AI-assisted department classification
and sensible reorder points. Outputs a clean CSV ready for seeding.

Usage: cd backend && python -m devtools.scripts.enhance_csv
"""

import csv
import io
import os
import re

INPUT = os.path.join(os.path.dirname(__file__), "..", "data", "SY Inventory - Sheet1 (1).csv")
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "SY Inventory - Enhanced.csv")

# ── Department classification rules ──────────────────────────────────────────
# Each rule: (pattern, department_code)
# Order matters — first match wins.

DEPT_RULES = [
    # Plumbing
    (
        r"(?i)\b(pex|cpvc|pvc|copper|pipe|plumb|faucet|toilet|sink|drain|valve|coupling|elbow|tee|adapter|fitting|ball.?valve|shut.?off|supply.?line|tailpiece|trap|wax.?ring|closet.?bolt|flange|solder|flux|teflon|thread.?seal|hose.?bibb|spigot|water.?heater|sump|sewer|crimp|press\b|propress|sharkbite|fernco|test.?plug|ptfe)",
        "PLU",
    ),
    # Electrical
    (
        r"(?i)\b(wire\b|wire\s|wiring|romex|nmwg|thhn|electrical|outlet|switch|breaker|gfci|afci|circuit|conduit|emt|junction.?box|gang.?box|round.?box|receptacle|dimmer|timer|switch.?plate|cover.?plate|wall.?plate|wire.?nut|marrette|cable.?connector|clamp.?conn|knockout|staple|strap.*emt|bushing|ground.?clamp|volt|amp|lug|terminal|pigtail|fish.?tape|pull.?box|weatherproof|photocell|motion.?sensor|flood.?light|light.?bulb|led.?bulb|cfl|fluorescent|ballast|lamp|lantern|flush.?mount|pendant|ceiling.?fan|smoke.?detector|co.?detector|doorbell|thermostat|time.?switch|ext.*cord|power.?strip|surge|battery|UF.?cable)",
        "ELE",
    ),
    # Lumber
    (
        r"(?i)\b(lumber|2x4|2x6|2x8|2x10|2x12|1x[246]|4x4|4x8|plywood|osb|sheathing|stud|furring|board|trim.?board|moulding|molding|baseboard|casing|crown|lattice|deck.?board|cedar|pine|oak|poplar|treated|pressure.?treat|pt\b|lvl|joist|rafter|beam|post|fence.?board|picket|rail|baluster|whitewood|hardboard|mdf|particleboard)",
        "LUM",
    ),
    # Paint
    (
        r"(?i)\b(paint|primer|stain|polyurethane|varnish|lacquer|shellac|sealant|caulk|silicone|adhesive|glue|epoxy|wood.?filler|spackle|putty|dap\b|bondo|roller|brush|tray|drop.?cloth|tape.*paint|painter|masking|sand.?paper|sanding|grit|scraper|sprayer|spray.?paint|rust.?oleum|kilz|zinsser|behr|eggshell|satin|semi.?gloss|flat|matte|gallon|quart|pint)",
        "PNT",
    ),
    # Tools
    (
        r"(?i)\b(drill|driver|saw\b|hammer|wrench|plier|screwdriver|socket|ratchet|level\b|tape.?measure|utility.?knife|snips|cutter|chisel|file\b|rasp|vise|workbench|sawhorse|tool.?box|tool.?bag|tool.?belt|bit\b|bits\b|blade|jigsaw|recipro|circular.?saw|miter|table.?saw|grinder|sander|heat.?gun|soldering|multimeter|voltage.?tester|fish.?tape|crimper|stripper|punch|awl|pry.?bar|crowbar|wrecking|sledge|mallet|axe|hatchet|shovel|rake|hoe\b|pick\b|mattock|post.?hole|wheelbarrow|dolly|ladder|scaffold|dewalt|milwaukee|makita|ryobi|bosch|husky|stanley|klein|knipex|channellock|irwin|craftsman|kobalt|ridgid|cordless.?drill|cordless.?saw|20v|combo.?kit|impact.?driver|oscillat|rotary|dremel)",
        "TOL",
    ),
    # Hardware / Fasteners
    (
        r"(?i)\b(screw|nail|bolt|nut\b|washer|anchor|rivet|staple|brad|pin\b|hook|eye|hinge|hasp|latch|lock|deadbolt|knob|handle|pull\b|bracket|brace|angle|corner|plate|strap(?!.*emt)|chain|cable(?!.*connector)|rope|twine|bungee|zip.?tie|cleat|d.?ring|snap|buckle|grommet|eyelet|magnet|velcro|command|3m\b|fastener|drywall|deck.?screw|lag|carriage|machine.?screw|hex|torx|phillips|flat.?head|pan.?head|round.?head|truss|self.?tap|sheet.?metal|concrete|masonry|tapcon|ramset|hilti|simpson|joist.?hanger|hurricane|rafter.?tie|post.?base|strapping(?!.*14))",
        "HDW",
    ),
    # Garden / Outdoor
    (
        r"(?i)\b(garden|plant|soil|mulch|fertilizer|seed\b|grass|lawn|mower|trimmer|edger|blower|chainsaw|pruner|shear|lopper|sprinkler|hose(?!.*bibb)|nozzle|pot\b|planter|landscape|weed|pesticide|herbicide|insect|ant\b|rodent|bird|fence(?!.*board)|gate|post(?!.*base)|concrete.?mix|mortar|paver|stepping.?stone|gravel|sand\b|landscape.?fabric|tarp|wheelbarrow|rain|gutter|downspout|ice.?melt|salt|snow|de.?icer|windshield)",
        "GDN",
    ),
    # Appliances / Home
    (
        r"(?i)\b(appliance|washer(?!.*flat)|dryer|refrigerator|dishwasher|microwave|range|oven|stove|hood|furnace|filter|hvac|a.?c\b|air.?condition|heater|fan\b|vent|duct|register|thermostat|water.?softener|blind|curtain|shade|door(?!.*bell)|window|screen|weather.?strip|threshold|sweep|insulation|foam|fiberglass|r.?value|vapor.?barrier|house.?wrap|tyvek|flashing|roofing|shingle|tar|felt|ice.?shield|ridge|soffit|fascia|siding|vinyl(?!.*mini)|aluminum|composite|pvc.?trim|glove|safety|mask|respirator|goggles|ear.?plug|knee.?pad|first.?aid|fire.?ext|lighter|flashlight|headlamp|work.?light|shop.?vac|bucket|trash|garbage|broom|mop|sponge|cleaning|bleach|cleaner)",
        "APP",
    ),
]

# Fallback: if nothing matches
DEFAULT_DEPT = "HDW"


def classify_department(product_name: str) -> str:
    for pattern, dept_code in DEPT_RULES:
        if re.search(pattern, product_name):
            return dept_code
    return DEFAULT_DEPT


def compute_reorder_point(product_name: str, on_hand: int, cost: float) -> int:
    """Heuristic reorder point based on product type and cost."""
    name_lower = product_name.lower()

    # High-velocity consumables — reorder sooner
    if any(
        kw in name_lower
        for kw in [
            "screw",
            "nail",
            "wire nut",
            "nut ",
            "washer",
            "strap",
            "connector",
            "clamp",
            "staple",
            "tape",
            "caulk",
            "silicone",
            "teflon",
            "sand",
            "grit",
        ]
    ):
        return max(10, on_hand // 3)

    # Bulk/by-the-foot items
    if "by the foot" in name_lower or "per foot" in name_lower:
        return max(50, on_hand // 4)

    # Pack items (already have quantity buffer)
    if re.search(r"\d+pk\b", name_lower):
        return max(3, on_hand // 4)

    # Expensive items (>$50 cost) — keep less on hand
    if cost > 50:
        return max(2, min(5, on_hand // 5))

    # Mid-range items
    if cost > 15:
        return max(3, on_hand // 4)

    # Cheap items — keep more
    return max(5, on_hand // 3)


def compute_reorder_qty(reorder_point: int, cost: float) -> int:
    """How many to order when hitting reorder point."""
    if cost > 100:
        return max(2, reorder_point)
    if cost > 30:
        return max(5, reorder_point)
    if cost > 10:
        return max(10, reorder_point * 2)
    return max(15, reorder_point * 2)


def parse_dollar(val: str) -> float:
    """Parse '$1,234.56' to float."""
    if not val:
        return 0.0
    return float(val.replace("$", "").replace(",", "").strip())


def main():
    with open(INPUT, encoding="utf-8-sig") as f:
        raw = f.read()

    # Skip header rows (first 4 lines are report metadata)
    lines = raw.strip().split("\n")
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Product,SKU"):
            header_idx = i
            break
    if header_idx is None:
        print("Could not find header row")
        return

    csv_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(csv_text))

    enhanced = []
    dept_counts = {}
    skipped = 0

    for row in reader:
        name = row.get("Product", "").strip()
        if not name:
            continue

        # Parse fields
        on_hand = int(row.get("On hand", "0").strip() or "0")
        cost = parse_dollar(row.get("Unit cost", "0"))
        retail = parse_dollar(row.get("Retail price", "0"))
        total_cost = parse_dollar(row.get("Total cost", "0"))
        retail_ex_tax = parse_dollar(row.get("Retail (Ex. Tax)", "0"))
        retail_inc_tax = parse_dollar(row.get("Retail (Inc. Tax)", "0"))
        sku = row.get("SKU", "").strip()
        barcode = row.get("Barcode", "").strip()

        # Skip items with 0 cost AND 0 retail (likely bad data)
        if cost == 0 and retail == 0:
            skipped += 1
            continue

        # Classify
        dept = classify_department(name)
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

        # Compute reorder
        reorder_point = compute_reorder_point(name, on_hand, cost)
        reorder_qty = compute_reorder_qty(reorder_point, cost)

        enhanced.append(
            {
                "Product": name,
                "SKU": sku,
                "Barcode": barcode,
                "On hand": on_hand,
                "Reorder qty": reorder_qty,
                "Reorder point": reorder_point,
                "Unit cost": f"${cost:.2f}",
                "Total cost": f"${total_cost:.2f}",
                "Retail price": f"${retail:.2f}",
                "Retail (Ex. Tax)": f"${retail_ex_tax:.2f}",
                "Retail (Inc. Tax)": f"${retail_inc_tax:.2f}",
                "Department": dept,
            }
        )

    # Write enhanced CSV
    fieldnames = [
        "Product",
        "SKU",
        "Barcode",
        "On hand",
        "Reorder qty",
        "Reorder point",
        "Unit cost",
        "Total cost",
        "Retail price",
        "Retail (Ex. Tax)",
        "Retail (Inc. Tax)",
        "Department",
    ]
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enhanced)

    # Summary
    dept_names = {
        "PLU": "Plumbing",
        "ELE": "Electrical",
        "LUM": "Lumber",
        "PNT": "Paint",
        "TOL": "Tools",
        "HDW": "Hardware",
        "GDN": "Garden",
        "APP": "Appliances/Home",
    }
    print(f"\nEnhanced {len(enhanced)} products ({skipped} skipped)")
    print(f"Output: {OUTPUT}\n")
    print("Department breakdown:")
    for code, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
        print(f"  {dept_names.get(code, code):20s} {count:4d}")
    print()

    # Show a few examples per department
    for code in sorted(dept_counts.keys()):
        examples = [e["Product"] for e in enhanced if e["Department"] == code][:3]
        print(f"  {code}: {', '.join(examples)}")


if __name__ == "__main__":
    main()
