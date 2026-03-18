"""Units of measure: allowed set, family groupings, conversion logic, and normalization."""

from typing import Any

ALLOWED_BASE_UNITS: frozenset[str] = frozenset(
    {
        "each",
        "case",
        "box",
        "pack",
        "bag",
        "roll",
        "kit",
        "set",
        "pair",
        "bottle",
        "can",
        "tube",
        "sheet",
        "gallon",
        "quart",
        "pint",
        "liter",
        "pound",
        "ounce",
        "foot",
        "inch",
        "meter",
        "yard",
        "sqft",
    }
)

# Each family maps unit → factor relative to the smallest unit in that family.
UNIT_FAMILIES: dict[str, dict[str, float]] = {
    "length": {
        "inch": 1.0,
        "foot": 12.0,
        "yard": 36.0,
        "meter": 39.3701,
    },
    "volume": {
        "pint": 1.0,
        "quart": 2.0,
        "gallon": 8.0,
        "liter": 2.11338,
    },
    "weight": {
        "ounce": 1.0,
        "pound": 16.0,
    },
    "area": {
        "sqft": 1.0,
    },
    "discrete": {
        "each": 1.0,
        "pack": 1.0,
        "box": 1.0,
        "case": 1.0,
        "bag": 1.0,
        "roll": 1.0,
        "kit": 1.0,
        "set": 1.0,
        "pair": 1.0,
        "bottle": 1.0,
        "can": 1.0,
        "tube": 1.0,
        "sheet": 1.0,
    },
}

_UNIT_TO_FAMILY: dict[str, str] = {
    unit: family for family, units in UNIT_FAMILIES.items() for unit in units
}


def family_for_unit(unit: str) -> str | None:
    """Return the family name for a unit, or None if unknown."""
    return _UNIT_TO_FAMILY.get(unit.lower())


def convert_quantity(qty: float, from_unit: str, to_unit: str) -> float:
    """Convert qty between two units in the same family.

    Raises ValueError if the units belong to different families or are unknown.
    Returns qty unchanged if from_unit == to_unit.
    """
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    if from_unit == to_unit:
        return qty

    from_family = _UNIT_TO_FAMILY.get(from_unit)
    to_family = _UNIT_TO_FAMILY.get(to_unit)

    if from_family is None:
        raise ValueError(f"Unknown unit: {from_unit}")
    if to_family is None:
        raise ValueError(f"Unknown unit: {to_unit}")
    if from_family != to_family:
        raise ValueError(
            f"Cannot convert between {from_unit} ({from_family}) and {to_unit} ({to_family})"
        )

    from_factor = UNIT_FAMILIES[from_family][from_unit]
    to_factor = UNIT_FAMILIES[to_family][to_unit]
    return round(qty * from_factor / to_factor, 6)


def are_compatible(unit_a: str, unit_b: str) -> bool:
    """True if two units belong to the same family (convertible)."""
    fa = _UNIT_TO_FAMILY.get(unit_a.lower())
    fb = _UNIT_TO_FAMILY.get(unit_b.lower())
    return fa is not None and fa == fb


def cost_per_sell_unit(
    cost_per_base: float,
    base_unit: str,
    sell_uom: str,
    pack_qty: int = 1,
) -> float:
    """Return the cost expressed per sell-unit (pack_qty × sell_uom).

    All costs are stored at the base_unit level.  A sell-unit may differ
    both in the physical unit (e.g. base=inch, sell=foot) and in pack size
    (pack_qty=12 means one sell-unit = 12 feet).

    Examples:
        cost_per_sell_unit(1.00, "foot", "foot", 1)  → 1.00
        cost_per_sell_unit(1.00, "inch", "foot", 1)  → 12.00   (1 foot = 12 inches)
        cost_per_sell_unit(1.00, "each", "each", 12) → 12.00   (1 case of 12)
    """
    pack_qty = max(pack_qty, 1)
    base_unit = (base_unit or "each").lower()
    sell_uom = (sell_uom or "each").lower()
    if base_unit == sell_uom and pack_qty == 1:
        return cost_per_base
    base_per_sell = (
        convert_quantity(1, sell_uom, base_unit) if are_compatible(base_unit, sell_uom) else 1.0
    )
    return round(cost_per_base * base_per_sell * pack_qty, 6)


def compute_sell_fields(
    price: float,
    cost: float,
    quantity: float,
    base_unit: str,
    sell_uom: str,
    pack_qty: int = 1,
) -> dict[str, float]:
    """Derive sell_price, sell_cost, sell_quantity from base_unit stored values.

    sell_price / sell_cost = what the customer pays/costs per sell-unit
    (a sell-unit is ``pack_qty`` of ``sell_uom``).
    sell_quantity = available stock expressed in sell-units.
    """
    pack_qty = max(pack_qty, 1)
    base_unit = (base_unit or "each").lower()
    sell_uom = (sell_uom or "each").lower()

    if base_unit != sell_uom and are_compatible(base_unit, sell_uom):
        base_per_sell = convert_quantity(1, sell_uom, base_unit)
        sell_per_base = convert_quantity(1, base_unit, sell_uom)
    else:
        base_per_sell = 1.0
        sell_per_base = 1.0

    return {
        "sell_price": round(price * base_per_sell * pack_qty, 4),
        "sell_cost": round(cost * base_per_sell * pack_qty, 4),
        "sell_quantity": round(quantity * sell_per_base / pack_qty, 6),
    }


# ── LLM output normalization ────────────────────────────────────────────────
# Maps common abbreviations and LLM variations to ALLOWED_BASE_UNITS.

_UNIT_ALIASES: dict[str, str] = {
    "gal": "gallon",
    "gals": "gallon",
    "gallons": "gallon",
    "gal.": "gallon",
    "qts": "quart",
    "quarts": "quart",
    "qt": "quart",
    "qt.": "quart",
    "pt": "pint",
    "pints": "pint",
    "pts": "pint",
    "pt.": "pint",
    "lbs": "pound",
    "lb": "pound",
    "pounds": "pound",
    "lb.": "pound",
    "oz": "ounce",
    "ozs": "ounce",
    "ounces": "ounce",
    "oz.": "ounce",
    "ft": "foot",
    "feet": "foot",
    "lf": "foot",
    "lnft": "foot",
    "ln ft": "foot",
    "linear foot": "foot",
    "in": "inch",
    "in.": "inch",
    "inches": "inch",
    "inch": "inch",
    "m": "meter",
    "meters": "meter",
    "metres": "meter",
    "yd": "yard",
    "yards": "yard",
    "yds": "yard",
    "sq ft": "sqft",
    "sqft": "sqft",
    "square feet": "sqft",
    "sq. ft": "sqft",
    "bx": "box",
    "cs": "case",
    "pk": "pack",
    "pkg": "pack",
    "pkgs": "pack",
    "ea": "each",
    "pc": "each",
    "pcs": "each",
    "piece": "each",
    "pieces": "each",
}


def normalize_unit(raw: Any, known_units: frozenset[str] | None = None) -> str:
    """Map raw LLM output or abbreviation to a known unit code.

    When ``known_units`` is provided, validates against that set (org units from DB).
    Falls back to ``ALLOWED_BASE_UNITS`` when not provided.
    Returns "each" for unknown, empty, or non-string inputs.
    """
    if not raw or not isinstance(raw, str):
        return "each"
    v = raw.lower().strip()
    v = _UNIT_ALIASES.get(v, v)
    valid = known_units if known_units is not None else ALLOWED_BASE_UNITS
    return v if v in valid else "each"


def normalize_pack_qty(val: Any) -> int:
    """Coerce a raw value to a valid positive pack quantity (min 1)."""
    if val is None:
        return 1
    try:
        return max(1, int(val))
    except (ValueError, TypeError):
        return 1
