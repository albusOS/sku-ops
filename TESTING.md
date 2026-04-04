# Testing

## Prerequisites

- **Python:** 3.13+ (managed via `.python-version`)
- **Pixi:** ([install](https://pixi.sh)) - unified dev tasks (`test`, `db`, `dev`, …)
- **uv:** 0.6+ ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js:** 20+ with npm
- **Docker:** (optional, for production verification and e2e)

## Install everything

```bash
# Python tooling (backend deps + pytest + ruff + commitizen)
uv sync

# Frontend deps
npm install --prefix frontend

# Playwright (optional, for e2e tests)
cd e2e && npm install && npx playwright install --with-deps chromium && cd ..
```

`uv sync` at the workspace root installs `sku-ops-backend` as an editable workspace member plus all dev dependencies (pytest, ruff, commitizen, rich). A single `uv.lock` at the workspace root governs all Python dependencies.

## Running tests

### All tests (backend + frontend)

```bash
pixi run test
```

### Backend only

```bash
pixi run test-backend                                   # all backend tests
pixi run test-backend -- -- backend/tests/unit/         # unit tests only
pixi run test-backend -- -- backend/tests/integration/  # integration tests only
pixi run test-backend -- -- backend/tests/api/          # API tests only
pixi run test-backend -- -- -k test_smoke              # single test by name
pixi run test-backend -- -- --tb=short -v              # verbose with short tracebacks
```

(Pass any pytest args after `--`.)

### Frontend only

```bash
pixi run test-frontend              # single run (vitest run)
npm run test --prefix frontend      # watch mode (vitest)
```

### End-to-end (Playwright)

```bash
pixi run test-e2e
```

Playwright will start the backend dev server automatically if not already running.

## How imports resolve

Backend test files import production code with bare module names:

```python
from catalog.application.product_lifecycle import create_product
from shared.infrastructure.db import sql_execute
from shared.kernel.types import CurrentUser
```

This works because `pythonpath = ["backend"]` in the root `pyproject.toml` pytest config adds `backend/` to `sys.path`. Combined with `--import-mode=importlib`, all backend modules resolve without `sys.path` hacks.

## Shared test infrastructure

All backend tests run against a real Postgres database provided by the local Supabase stack. `pixi run test` and `pixi run test-backend` reset the local database from `supabase/migrations/` and `supabase/seeds/*.sql` (via `supabase/config.toml` `[db.seed] sql_paths`) before pytest starts.

A session-scoped `TestClient` boots the ASGI app once for the entire test run. Before each test that needs a clean slate, `_truncate_and_seed()` truncates all tables then applies `supabase/seeds/pytest_minimal.sql` plus org-scoped UOM rows from `supabase/seeds/02_units_of_measure.sql` (via `catalog.application.uom_seed.uom_seed_sql`).

**To extend test fixture data:** edit `supabase/seeds/pytest_minimal.sql` and/or `backend/tests/conftest.py`. Do not create duplicate seed fixtures in sub-conftest files.

## Test structure

Each deployable owns its tests. E2e tests live at the workspace root.

```
backend/tests/                         # backend tests
├── conftest.py                        # env vars + session-scoped TestClient + truncate/seed
├── helpers/                           # shared test utilities
│   ├── auth.py                        # JWT token/header factories
│   ├── factories.py                   # domain object factories
│   └── xero.py                        # Xero mock helpers
├── unit/                              # pure logic, no DB
│   ├── test_architecture.py           # DDD boundary validation (AST-based)
│   ├── test_barcode_validation.py
│   └── ...
├── integration/                       # DB + application logic
│   ├── test_cycle_count.py
│   ├── test_product_lifecycle.py
│   └── ...
├── api/                               # HTTP tests via TestClient
│   ├── conftest.py                    # client + auth_headers fixtures
│   ├── test_smoke.py
│   └── ...
└── e2e/                               # backend e2e pipelines (Postgres, no browser)
    ├── conftest.py                    # pipeline-specific fixtures
    ├── helpers.py                     # shared e2e utilities
    ├── test_withdrawal_pipeline.py
    ├── test_payment_pipeline.py
    ├── test_po_receiving_pipeline.py
    └── ...

frontend/src/                          # frontend co-located unit tests
├── hooks/__tests__/useBarcodeScanner.test.js
├── hooks/__tests__/useProductMatch.test.js
├── lib/__tests__/api-client.test.js
└── test/setup.js

e2e/                                   # cross-stack browser e2e (Playwright)
├── playwright.config.ts
├── package.json
└── specs/
    ├── health.spec.ts
    ├── 01-withdrawal-financials.spec.ts
    ├── 02-invoice-payment-cycle.spec.ts
    └── ...
```

## Adding a new test

### Backend unit test

Create `backend/tests/unit/test_<name>.py`. Import domain/kernel code directly. No `db` fixture needed.

### Backend integration test

Create `backend/tests/integration/test_<name>.py`. Use the `db` or `_db` fixture for database access. Import application and infrastructure modules.

### Backend API test

Create `backend/tests/api/test_<name>.py`. Use the `client`, `db`, and `auth_headers` fixtures. Test through HTTP.

### Frontend unit test

Co-locate with the source file: create `frontend/src/<module>/__tests__/<name>.test.js`. Uses Vitest + jsdom + `@testing-library/react`. The `@` alias resolves to `frontend/src/`. Frontend unit tests stay inside `frontend/` because they depend on `node_modules` resolution and relative imports to source files.

### E2e test

Create `e2e/specs/<name>.spec.ts`. Uses Playwright. Server starts automatically.

## Seeds and evals

```bash
pixi run db-reset
pixi run eval -- --suite all
pixi run eval -- --suite routing --model anthropic/claude-haiku-4-5
```

Canonical SQL seeds live under `supabase/seeds/` (edit there, then `pixi run db-reset` or `supabase db reset --local`). Evals live in `devtools/`. They import backend production code via `PYTHONPATH=backend:.` as set by `pixi` Python tasks.

## Linting

```bash
pixi run lint-backend
pixi run format-backend
pixi run lint-frontend
pixi run format-frontend
pixi run check                     # all four
```

Ruff config lives in the root `pyproject.toml`. Per-file-ignores are scoped to `backend/tests/**`, `devtools/**`, and specific backend paths.

## Docker

The Docker image contains only production code and dependencies:

```bash
docker build -f backend/Dockerfile .   # build context is workspace root
```

- `uv sync --frozen --no-dev --no-editable` in the Dockerfile installs only `[project.dependencies]`.
- Devtools live at workspace root, structurally outside the `COPY backend/ .` layer.
- `backend/tests/` is excluded via `.dockerignore`.
