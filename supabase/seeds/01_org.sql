-- Seed: Supply Yard demo (canonical in repo)
INSERT INTO organizations (id, name, slug, created_at) VALUES ('supply-yard', 'Supply Yard', 'supply-yard', '2025-03-17T12:00:00+00:00') ON CONFLICT (id) DO NOTHING;
INSERT INTO org_settings (organization_id, auto_invoice, default_tax_rate) VALUES ('supply-yard', FALSE, 0.10) ON CONFLICT (organization_id) DO NOTHING;
