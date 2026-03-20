-- Generated from legacy Python seed definitions during the Supabase cutover.

INSERT INTO organizations (id, name, slug, created_at) VALUES ('supply-yard', 'Supply Yard', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-each', 'each', 'Each', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-case', 'case', 'Case', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-box', 'box', 'Box', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-pack', 'pack', 'Pack', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-bag', 'bag', 'Bag', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-roll', 'roll', 'Roll', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-kit', 'kit', 'Kit', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-set', 'set', 'Set', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-pair', 'pair', 'Pair', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-bottle', 'bottle', 'Bottle', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-can', 'can', 'Can', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-tube', 'tube', 'Tube', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-sheet', 'sheet', 'Sheet', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-gallon', 'gallon', 'Gallon', 'volume', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-quart', 'quart', 'Quart', 'volume', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-pint', 'pint', 'Pint', 'volume', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-liter', 'liter', 'Liter', 'volume', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-pound', 'pound', 'Pound', 'weight', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-ounce', 'ounce', 'Ounce', 'weight', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-foot', 'foot', 'Foot', 'length', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-inch', 'inch', 'Inch', 'length', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-meter', 'meter', 'Meter', 'length', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-yard', 'yard', 'Yard', 'length', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-sqft', 'sqft', 'Square Foot', 'area', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-bundle', 'bundle', 'Bundle', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-pallet', 'pallet', 'Pallet', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;

INSERT INTO units_of_measure (id, code, name, family, created_at)
        VALUES ('uom-slab', 'slab', 'Slab', 'discrete', '2024-01-01T00:00:00+00:00')
        ON CONFLICT DO NOTHING;
