"""Product classification helpers: UOM inference, department suggestion, UOM resolution.

Pure functions that classify hardware store products by analyzing product names.
Used by the product intelligence pipeline and document import flows.
"""

import contextlib
import re

from shared.kernel.units import ALLOWED_BASE_UNITS

# ── Department keyword hints ─────────────────────────────────────────────────

_DEPT_KEYWORDS = {
    "PLU": [
        "pex",
        "pvc",
        "cpvc",
        "pipe",
        "valve",
        "elbow",
        "coupling",
        "adapter",
        "sweat",
        "press",
        "crimp",
        "tailpiece",
        "drain",
        "faucet",
        "toilet",
        "sink",
    ],
    "ELE": [
        "wire",
        "cable",
        "connector",
        "emt",
        "conduit",
        "outlet",
        "switch",
        "breaker",
        "led",
        "light",
        "lamp",
        "box",
        "strap",
        "clamp",
        "knockout",
    ],
    "PNT": [
        "paint",
        "brush",
        "roller",
        "stain",
        "primer",
        "caulk",
        "spray",
        "sanding",
        "sandpaper",
    ],
    "LUM": [
        "lumber",
        "board",
        "stud",
        "plywood",
        "2x4",
        "2x6",
        "trim",
        "furring",
        "door",
        "slab",
        "moulding",
    ],
    "TOL": [
        "tool",
        "drill",
        "saw",
        "sander",
        "bit",
        "blade",
        "hammer",
        "screwdriver",
        "wrench",
        "level",
    ],
    "HDW": ["screw", "nail", "bolt", "anchor", "hinge", "lock", "bracket", "fastener"],
    "GDN": ["garden", "plant", "soil", "fertilizer", "hose", "sprinkler"],
    "APP": ["appliance", "furnace", "range", "hood", "filter", "hvac"],
}


def suggest_department(name: str, departments_by_code: dict) -> str | None:
    """Suggest department code from product name using keyword matching."""
    if not name:
        return None
    name_lower = name.lower()
    for code, keywords in _DEPT_KEYWORDS.items():
        if code in departments_by_code and any(kw in name_lower for kw in keywords):
            return code
    return None


# ── UOM inference ────────────────────────────────────────────────────────────


def resolve_uom(item: dict) -> tuple[str, str, int]:
    """Resolve base_unit, sell_uom, pack_qty from item dict, validating against allowed units."""
    bu = (item.get("base_unit") or "each").lower().strip()
    su = (item.get("sell_uom") or item.get("base_unit") or "each").lower().strip()
    pq = item.get("pack_qty")
    try:
        pq = max(1, int(pq)) if pq is not None else 1
    except (ValueError, TypeError):
        pq = 1
    bu = bu if bu in ALLOWED_BASE_UNITS else "each"
    su = su if su in ALLOWED_BASE_UNITS else "each"
    return bu, su, pq


def infer_uom(name: str) -> tuple[str, str, int]:
    """Infer base_unit, sell_uom, pack_qty from product name.

    Order: explicit patterns first (e.g. 5 gal), then keyword-based rules.
    """
    n = name.lower()

    for pattern, unit in [
        (r"(\d+)\s*gal", "gallon"),
        (r"(\d+)\s*gal\.?", "gallon"),
        (r"gal(?:lon)?\b", "gallon"),
        (r"(\d+)\s*qt\.?", "quart"),
        (r"quart\b", "quart"),
        (r"(\d+)\s*pt\.?", "pint"),
        (r"(\d+)\s*pk\b", "pack"),
        (r"(\d+)pk\b", "pack"),
        (r"(\d+)\s*pack", "pack"),
        (r"(\d+)\s*box", "box"),
        (r"(\d+)\s*roll", "roll"),
        (r"(\d+)\s*case", "case"),
        (r"(\d+)\s*lb", "pound"),
        (r"(\d+)\s*oz", "ounce"),
        (r"(\d+)\s*ft\b", "foot"),
        (r"(\d+)\s*'\s*", "foot"),
        (r"(\d+)'\s*", "foot"),
        (r"x(\d+)'", "foot"),
        (r"(\d+)\s*lf\b", "foot"),
        (r"(\d+)\s*ln\s*ft", "foot"),
        (r'(\d+)\s*(?:in\b|in\.|")', "inch"),
        (r"(\d+)\s*inch", "inch"),
        (r"sq\s*ft", "sqft"),
        (r"(\d+)\s*sq\s*ft", "sqft"),
        (r"(\d+)\s*bag", "bag"),
        (r"(\d+)\s*kit", "kit"),
    ]:
        m = re.search(pattern, n, re.IGNORECASE)
        if m and unit in ALLOWED_BASE_UNITS:
            pq = 1
            if m.groups() and m.group(1):
                with contextlib.suppress(ValueError, TypeError):
                    pq = max(1, int(m.group(1)))
            return unit, unit, pq

    roll_keywords = ["tape", "screen", "mesh", "landscape fabric", "vapor barrier", "house wrap"]
    if any(kw in n for kw in roll_keywords):
        return "roll", "roll", 1

    linear_keywords = [
        "pipe",
        "pvc",
        "cpvc",
        "pex",
        "conduit",
        "emt",
        "wire",
        "cable",
        "romex",
        "rope",
        "hose",
        "chain",
        "cord",
        "extension cord",
        "trim",
        "moulding",
        "molding",
        "lumber",
        "stud",
        "2x4",
        "2x6",
        "2x8",
        "1x4",
        "1x6",
        "board",
        "furring",
        "rebar",
        "angle iron",
        "duct",
        "ductwork",
        "flex duct",
        "b vent",
        "sill plate",
        "joist",
        "rafter",
        "siding",
        "fencing",
        "fence",
    ]
    if any(kw in n for kw in linear_keywords):
        len_matches = re.findall(r"(?:x|\*)(\d+)\b", n)
        pq = max(1, int(len_matches[-1])) if len_matches else 1
        ft_m = re.search(r"(\d+)\s*ft\b", n) or re.search(r"(\d+)\s*'\s*", n)
        if ft_m:
            pq = max(1, int(ft_m.group(1)))
        return "foot", "foot", pq

    liquid_keywords = ["paint", "stain", "primer", "sealer", "thinner", "polyurethane", "varnish"]
    if any(kw in n for kw in liquid_keywords):
        if "quart" in n or "qt" in n:
            return "quart", "quart", 1
        if "pint" in n or "pt" in n:
            return "pint", "pint", 1
        return "gallon", "gallon", 1

    box_keywords = [
        "screw",
        "nail",
        "bolt",
        "nut",
        "washer",
        "anchor",
        "fastener",
        "rivet",
        "staple",
    ]
    if any(kw in n for kw in box_keywords):
        if "box" in n or "bx" in n:
            return "box", "box", 1
        if "pack" in n or "pk" in n or "pkg" in n:
            return "pack", "pack", 1
        if "case" in n:
            return "case", "case", 1
        return "box", "box", 1

    sqft_keywords = [
        "drywall",
        "sheetrock",
        "plywood",
        "osb",
        "mdf",
        "hardboard",
        "insulation board",
        "ceiling tile",
    ]
    if any(kw in n for kw in sqft_keywords):
        return "sqft", "sqft", 1

    bag_keywords = ["concrete", "mortar", "grout", "sand", "gravel", "mulch", "soil", "fertilizer"]
    if any(kw in n for kw in bag_keywords):
        if "lb" in n or "pound" in n:
            return "pound", "pound", 1
        return "bag", "bag", 1

    kit_keywords = ["kit", "assembly", "faucet", "light fixture", "vanity", "toilet", "sink"]
    if any(kw in n for kw in kit_keywords):
        if "kit" in n:
            return "kit", "kit", 1
        return "each", "each", 1

    return "each", "each", 1
