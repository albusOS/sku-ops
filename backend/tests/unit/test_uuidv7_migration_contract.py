"""Contract tests for the UUIDv7 primary-key migration baseline."""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND.parent
UUID_PATTERN = re.compile("[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", re.IGNORECASE)

def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

def test_shared_schema_uses_uuid_for_internal_primary_keys():
    shared_schema = _read("supabase/schemas/01-shared-schema.sql")
    assert "id UUID PRIMARY KEY" in shared_schema
    assert "organization_id UUID REFERENCES organizations(id)" in shared_schema
    assert "user_id UUID NOT NULL REFERENCES users(id)" in shared_schema

def test_rls_function_returns_uuid_tenant_key():
    rls_sql = _read("supabase/schemas/11-rls-policies.sql")
    assert "RETURNS uuid" in rls_sql
    assert "::uuid" in rls_sql

def test_seeded_org_and_auth_claim_use_uuidv7():
    org_seed = _read("supabase/seeds/01_org.sql")
    users_seed = _read("supabase/seeds/04_users.sql")
    org_ids = UUID_PATTERN.findall(org_seed)
    assert org_ids, "expected a literal UUIDv7 org id in seed SQL"
    assert any(org_id in users_seed for org_id in org_ids)

def test_uuid_helper_exposes_uuidv7_generators():
    from shared.helpers.uuid import new_uuid7, new_uuid7_str
    generated = new_uuid7()
    generated_text = new_uuid7_str()
    assert generated.version == 7
    assert UUID_PATTERN.fullmatch(str(generated))
    assert UUID_PATTERN.fullmatch(generated_text)
