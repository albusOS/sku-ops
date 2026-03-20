# Supabase Cutover Inventory

## Canonical schema and migration surface today

- The current schema source of truth is Python DDL aggregated in `backend/shared/infrastructure/full_schema.py`.
- Runtime schema bootstrap happens in `backend/shared/infrastructure/migrations/runner.py`.
- App startup always initializes the database and runs schema bootstrap through `backend/startup.py`.
- The current connection and transaction contract lives in `backend/shared/infrastructure/db/__init__.py`.
- The low-level PostgreSQL adapter is `backend/shared/infrastructure/db/postgres.py`.

## Database behavior that must be preserved

- Ambient transaction scope via `transaction()` and a contextvar-backed current connection.
- Nested transaction reuse instead of opening a second transactional connection.
- Ambient org and user context via `org_id_var` and `user_id_var`.
- Backend-only access for domain data. The frontend currently uses backend APIs for business data and Supabase only for auth.
- Direct Postgres connections for production. The current backend explicitly rejects the Supabase transaction pooler port.

## Current blast radius

### Shared infrastructure

- `backend/shared/infrastructure/schema.py`
- `backend/shared/infrastructure/full_schema.py`
- `backend/shared/infrastructure/migrations/runner.py`
- `backend/shared/infrastructure/db/__init__.py`
- `backend/shared/infrastructure/db/postgres.py`
- `backend/shared/infrastructure/database.py`
- `backend/shared/infrastructure/config.py`
- `backend/startup.py`

### Assistant code that currently depends on Python DDL

- `backend/assistant/agents/analyst/schema_context.py`
- `backend/assistant/agents/analyst/sql_executor.py`
- `backend/assistant/application/entity_graph.py`
- `backend/assistant/infrastructure/embedding_store.py`

### Test files that currently depend on Python DDL or raw connection behavior

- `backend/tests/integration/test_schema_single_source.py`
- `backend/tests/integration/test_repo_contracts.py`
- `backend/tests/conftest.py`
- `backend/tests/e2e/test_org_isolation.py`

## Contexts with infrastructure repositories or direct DB-heavy application code

### Catalog

- Repo files under `backend/catalog/infrastructure/`
- Application query and lifecycle modules under `backend/catalog/application/`

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

## Migration sequence locked by this inventory

1. Generate and commit the root `supabase/` project.
2. Add a centralized SQLModel plus SQLAlchemy backend layer without breaking the current repo contract.
3. Replace local Postgres-only dev flow with local Supabase stack flow.
4. Cut auth over to Supabase in all environments.
5. Migrate context repos and query modules behind the new database layer.
6. Remove Python DDL bootstrap and update assistant schema tooling to use database metadata or Supabase-owned SQL artifacts.
