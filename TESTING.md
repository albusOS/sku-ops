# Testing

## Prerequisites

- **Pixi:** ([install](https://pixi.sh)) — installs Python 3.13, uv, Node 20, pnpm from [pixi.toml](pixi.toml) / [pixi.lock](pixi.lock)
- **Supabase CLI:** for local DB (`pixi run db`, `db-reset`) — not bundled by pixi; install per [Supabase CLI docs](https://supabase.com/docs/guides/cli)
- **Docker:** (optional, for production verification and e2e)

## Install everything

```bash
pixi install
pixi run doctor                                              # tools must resolve from .pixi/envs/default/

# Backend venv (pixi Python + uv.lock)
pixi run uv sync --dev --directory backend

# Frontend deps
pixi run pnpm --dir frontend install --frozen-lockfile

# E2e package (Playwright); install browsers once from repo root: `( cd e2e && pnpx playwright install --with-deps chromium )` using a shell where `pnpx` is the pixi env (e.g. after `pixi shell` or any `pixi run` task)
pixi run pnpm --dir e2e install --frozen-lockfile
```

`pixi run uv sync --dev --directory backend` creates `backend/.venv` linked to the pixi-managed interpreter. [`backend/uv.lock`](backend/uv.lock) governs Python packages.

## Running tests

### All tests (backend + frontend)

```bash
pixi run test
```

### Backend only

```bash
pixi run test-backend                                   # all backend tests
pixi run test-backend -- -- tests/unit/         # unit tests only
pixi run test-backend -- -- tests/integration/  # integration tests only
pixi run test-backend -- -- tests/api/          # API tests only
pixi run test-backend -- -- -k test_smoke              # single test by name
pixi run test-backend -- -- --tb=short -v              # verbose with short tracebacks
```

(Pass any pytest args after `--`.)

### Frontend only

```bash
pixi run test-frontend              # single run (vitest run)
pixi run pnpm --dir frontend run test   # watch mode (vitest)
```

### End-to-end (Playwright)

```bash
pixi run test-e2e
```

`test-e2e` runs `pnpm install --frozen-lockfile` in `e2e/` then Playwright. Ensure browsers are installed if needed.

## How imports resolve

Backend test files import production code with bare module names:

```python
from catalog.application.product_lifecycle import create_product
from shared.infrastructure.db import sql_execute
from shared.kernel.types import CurrentUser
```

This works because `pythonpath = [".", ".."]` in [`backend/pyproject.toml`](backend/pyproject.toml) adds `backend/` (first-party modules like `shared`) and the repo root (`backend.*` test imports) to `sys.path`. Combined with `--import-mode=importlib`, modules resolve without ad hoc `sys.path` hacks.

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

Canonical SQL seeds live under `supabase/seeds/` (edit there, then `pixi run db-reset` or `supabase db reset --local`). Evals live in `devtools/`. Pixi Python tasks set `PYTHONPATH=.:..` with `uv run --directory backend` so `devtools` and backend code import correctly.

## Linting

```bash
pixi run lint-backend
pixi run format-backend
pixi run lint-frontend
pixi run format-frontend
pixi run check                     # all four
```

Ruff config lives in [`backend/pyproject.toml`](backend/pyproject.toml). Per-file-ignores are scoped to `tests/**`, `../devtools/**`, and specific paths under `backend/`.

## Docker

The Docker image contains only production code and dependencies:

```bash
docker build -f backend/Dockerfile .   # build context is workspace root
```

- `uv sync --frozen --no-dev --no-editable --directory backend` in the Dockerfile installs only `[project.dependencies]`.
- Devtools live at workspace root, structurally outside the `COPY backend/ .` layer.
- `backend/tests/` is excluded via `.dockerignore`.
