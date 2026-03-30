-- Default units of measure for catalog API (org-scoped; matches pytest uom_seed_sql ids).

INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-each', 'each', 'Each', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-case', 'case', 'Case', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-box', 'box', 'Box', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-pack', 'pack', 'Pack', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-bag', 'bag', 'Bag', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-roll', 'roll', 'Roll', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-kit', 'kit', 'Kit', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-set', 'set', 'Set', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-pair', 'pair', 'Pair', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-bottle', 'bottle', 'Bottle', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-can', 'can', 'Can', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-tube', 'tube', 'Tube', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-sheet', 'sheet', 'Sheet', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-gallon', 'gallon', 'Gallon', 'volume', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-quart', 'quart', 'Quart', 'volume', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-pint', 'pint', 'Pint', 'volume', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-liter', 'liter', 'Liter', 'volume', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-pound', 'pound', 'Pound', 'weight', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-ounce', 'ounce', 'Ounce', 'weight', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-foot', 'foot', 'Foot', 'length', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-inch', 'inch', 'Inch', 'length', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-meter', 'meter', 'Meter', 'length', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-yard', 'yard', 'Yard', 'length', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-sqft', 'sqft', 'Square Foot', 'area', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-bundle', 'bundle', 'Bundle', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-pallet', 'pallet', 'Pallet', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at) VALUES ('supply-yard-uom-slab', 'slab', 'Slab', 'discrete', 'supply-yard', '2024-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING;
