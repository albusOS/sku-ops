-- Seed: Supply Yard demo (canonical in repo)
INSERT INTO organizations (id, name, slug, created_at) VALUES ('0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', 'Supply Yard', 'supply-yard', '2025-03-17T12:00:00+00:00') ON CONFLICT (id) DO NOTHING;
INSERT INTO org_settings (organization_id, auto_invoice, default_tax_rate) VALUES ('0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', FALSE, 0.10) ON CONFLICT (organization_id) DO NOTHING;
