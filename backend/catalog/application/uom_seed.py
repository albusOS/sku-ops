"""Test and fixture seed data for default units of measure (DML, not DDL)."""

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
