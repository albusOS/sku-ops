"""API test fixtures — HTTP client with full lifespan, portal-seeded DB.

The TestClient uses the context manager to run FastAPI's lifespan (which
initialises the asyncpg pool in the correct event loop). All DB seeding
runs through ``client.portal.call()`` so it executes inside the app's
event loop — preventing the asyncpg InterfaceError that occurs when the
pool is created in a different event loop than the one executing queries.
"""

import pytest
from starlette.testclient import TestClient

from tests.helpers.auth import admin_headers, contractor_headers

# ── Seed helpers (run inside the app event loop via portal.call) ─────────


async def _truncate_all() -> None:
    from shared.infrastructure.database import get_connection

    conn = get_connection()
    await conn.execute(
        """DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$"""
    )
    await conn.commit()


async def _seed_base_data() -> None:
    from shared.infrastructure.database import get_connection
    from shared.infrastructure.logging_config import org_id_var, user_id_var

    org_id_var.set("default")
    user_id_var.set("user-1")
    conn = get_connection()
    await conn.execute(
        """INSERT INTO organizations (id, name, slug, created_at)
           VALUES ('default', 'Default', 'default', NOW())
           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, slug = EXCLUDED.slug"""
    )
    await conn.execute(
        """INSERT INTO departments (id, name, code, description, sku_count, organization_id, created_at)
           VALUES ('dept-1', 'Hardware', 'HDW', 'Hardware dept', 0, 'default', NOW())
           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, code = EXCLUDED.code,
           description = EXCLUDED.description, sku_count = EXCLUDED.sku_count,
           organization_id = EXCLUDED.organization_id"""
    )
    await conn.execute(
        """INSERT INTO users (id, email, password, name, role, is_active, organization_id, created_at)
           VALUES ('user-1', 'test@test.com', 'hash', 'Test User', 'admin', 1, 'default', NOW())
           ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, password = EXCLUDED.password,
           name = EXCLUDED.name, role = EXCLUDED.role, is_active = EXCLUDED.is_active,
           organization_id = EXCLUDED.organization_id"""
    )
    await conn.execute(
        """INSERT INTO users (id, email, password, name, role, company, billing_entity,
           is_active, organization_id, created_at)
           VALUES ('contractor-1', 'contractor@test.com', 'hash', 'Contractor User',
           'contractor', 'ACME', 'ACME Inc', 1, 'default', NOW())
           ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, password = EXCLUDED.password,
           name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company,
           billing_entity = EXCLUDED.billing_entity, is_active = EXCLUDED.is_active,
           organization_id = EXCLUDED.organization_id"""
    )
    await conn.commit()


async def _seed_bcrypt_user() -> None:
    import bcrypt

    from shared.infrastructure.database import get_connection

    hashed = bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    await conn.execute(
        "INSERT INTO users "
        "(id, email, password, name, role, is_active, organization_id, created_at) "
        "VALUES ('bcrypt-user-1', 'bcrypt@test.com', $1, 'Bcrypt User', 'admin', 1, 'default', NOW()) "
        "ON CONFLICT (id) DO UPDATE SET password = EXCLUDED.password",
        (hashed,),
    )
    await conn.commit()


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    """HTTP client with full lifespan — pool lives in the app's event loop."""
    from server import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db(client):
    """Truncate + seed minimal data via the app's event loop."""
    client.portal.call(_truncate_all)
    client.portal.call(_seed_base_data)
    return


@pytest.fixture
def _db(db):
    """Alias for ``db`` — many test files reference this name."""
    return


@pytest.fixture
def _db_with_bcrypt_user(db, client):
    """DB with a user whose password is a real bcrypt hash."""
    client.portal.call(_seed_bcrypt_user)
    return


@pytest.fixture
def auth_headers():
    """Admin auth headers."""
    return admin_headers()


@pytest.fixture
def contractor_auth_headers():
    """Contractor auth headers."""
    return contractor_headers()
