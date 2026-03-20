# Supabase Cutover Inventory

## Canonical schema and migration surface today

- **DDL source of truth**: declarative SQL under `supabase/schemas/` (`01-shared-schema.sql` through `10-entity-edges-schema.sql`), listed in `supabase/config.toml` under `[db.migrations] schema_paths`.
- **Applied schema**: versioned files in `supabase/migrations/` (baseline plus follow-up migrations). `supabase db reset --local` applies migrations only; use `supabase db diff` to generate new migrations from declarative schema changes.
- App startup initializes the pool via `init_db()` in `backend/startup.py` - it does **not** run DDL at runtime.
- Connection and transaction contract: `backend/shared/infrastructure/db/__init__.py`.
- Low-level PostgreSQL adapter: `backend/shared/infrastructure/db/postgres.py`.

## Database behavior that must be preserved

- Ambient transaction scope via `transaction()` and a contextvar-backed current connection.
- Nested transaction reuse instead of opening a second transactional connection.
- Ambient org and user context via `org_id_var` and `user_id_var`.
- Backend-only access for domain data. The frontend currently uses backend APIs for business data and Supabase only for auth.
- Direct Postgres connections for production. The current backend explicitly rejects the Supabase transaction pooler port.

## Current blast radius

### Supabase / SQL

- `supabase/schemas/*.sql`
- `supabase/migrations/*.sql`
- `supabase/config.toml`
- `supabase/seed.sql`

### Shared infrastructure (backend)

- `backend/shared/infrastructure/db/__init__.py`
- `backend/shared/infrastructure/db/postgres.py`
- `backend/shared/infrastructure/database.py`
- `backend/shared/infrastructure/config.py`
- `backend/startup.py`

### Assistant code tied to schema shape

- `backend/assistant/agents/analyst/schema_context.py` (parses `CREATE TABLE` from declarative schema files)
- `backend/assistant/agents/analyst/sql_executor.py`
- `backend/assistant/application/entity_graph.py`
- `backend/assistant/infrastructure/embedding_store.py`

### Test files

- `backend/tests/integration/test_schema_single_source.py`
- `backend/tests/integration/test_repo_contracts.py`
- `backend/tests/conftest.py`
- `backend/tests/e2e/test_org_isolation.py`

## Contexts with infrastructure repositories or direct DB-heavy application code

### Catalog

- Repo files under `backend/catalog/infrastructure/`
- Application query and lifecycle modules under `backend/catalog/application/` (e.g. `uom_seed.py` for test DML)

### Inventory

- Repo files under `backend/inventory/infrastructure/`
- Application query and service modules under `backend/inventory/application/`

### Operations

- Repo files under `backend/operations/infrastructure/`
- Application services with direct DB interactions under `backend/operations/application/`

### Finance

- Repo files under `backend/finance/infrastructure/`
- Analytics and query modules under `backend/finance/application/`

### Purchasing

- Repo files under `backend/purchasing/infrastructure/`
- Query and analytics modules under `backend/purchasing/application/`

### Documents

- Repo files under `backend/documents/infrastructure/`

### Jobs

- Repo files under `backend/jobs/infrastructure/`

### Shared

- Shared persistence modules under `backend/shared/infrastructure/`

## Frontend boundary

- `frontend/src/lib/api-client.js` is the current domain-data access boundary.
- `frontend/src/context/AuthContext.jsx` currently supports Supabase auth plus a backend bridge fallback.
- `frontend/src/lib/supabase.js` is auth-only today.
- The cutover keeps business data behind the backend and removes the bridge auth fallback.

## Migration sequence (historical checklist)

1. Generate and commit the root `supabase/` project.
2. Add a centralized SQLModel plus SQLAlchemy backend layer without breaking the current repo contract. *(Optional / not current path.)*
3. Replace local Postgres-only dev flow with local Supabase stack flow.
4. Cut auth over to Supabase in all environments.
5. Migrate context repos and query modules behind the new database layer.
6. ~~Remove Python DDL bootstrap~~ Done: DDL lives in `supabase/schemas/` and migrations; assistant reads declarative SQL for catalog generation.
