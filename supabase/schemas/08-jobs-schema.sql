-- Jobs: job master data.

CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL DEFAULT '',
        billing_entity_id UUID REFERENCES billing_entities(id),
        status TEXT NOT NULL DEFAULT 'active',
        service_address TEXT NOT NULL DEFAULT '',
        notes TEXT,
        organization_id UUID NOT NULL REFERENCES organizations(id),
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(organization_id, code)
    );

CREATE INDEX IF NOT EXISTS idx_jobs_org_code ON jobs(organization_id, code);

CREATE INDEX IF NOT EXISTS idx_jobs_org_status ON jobs(organization_id, status);
