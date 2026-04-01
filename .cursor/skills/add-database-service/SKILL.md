---
name: add-database-service
description: Registers a new lazy-loaded domain database service on DatabaseManager (e.g. db.mycontext) and keeps Pyright stubs in sync. New services must be a package directory under shared/infrastructure/db/services/<context>/ (never a single services/foo.py file). Use when wiring a new bounded-context DB facade, updating DatabaseManager and TransactionScope, or splitting a large service package.
---

# Add a new database service (SKU-Ops)

In this codebase, a **database service** is a class under `backend/shared/infrastructure/db/services/` that subclasses `DomainDatabaseService`, owns ORM-backed persistence for one area, and is exposed as `get_database_manager().<name>` and `async with transaction() as tx: tx.<name>`.

Each service **must** live in its own **package directory** (e.g. `services/mycontext/` with `__init__.py` exporting `MyContextDatabaseService`). Do **not** add new services as a single top-level file next to `base.py` (e.g. `services/mycontext.py`). Existing single-file modules are legacy; new work follows the directory layout only.

This is **not** the same as adding a repository inside a bounded context (`{context}/infrastructure/*_repo.py`). Repos stay in their context; the shared **database service** is the SQLModel/session facade the app uses through `DatabaseManager`.

## Brief checklist

1. Create package `backend/shared/infrastructure/db/services/<context>/` with `__init__.py` exporting `<Context>DatabaseService(DomainDatabaseService)` (split internals into sibling modules under that directory if needed).
2. Re-export from `services/__init__.py` if you want a stable import path.
3. Register lazy path in `DatabaseManager._service_paths` in `base.py`.
4. Mirror typing: `TYPE_CHECKING` import + attribute on **both** `DatabaseManager` and `TransactionScope` in `base.py`.
5. Optionally extend `warmup()` in `base.py` if this service must be loaded at startup (most do not).

## Detailed steps

### 1. Package layout (required)

- Create a directory `services/<context>/` (lowercase context key, valid Python package name).
- Export `FooDatabaseService` from `services/<context>/__init__.py` so the lazy import path is `shared.infrastructure.db.services.<context>.<Context>DatabaseService` (class name in PascalCase with `DatabaseService` suffix).
- Add modules under the same directory for large areas (e.g. `services/finance/_invoices.py`); keep the public class and `__all__` in `__init__.py` or a single obvious module re-exported there.

Reference implementations:

- `backend/shared/infrastructure/db/services/finance/`
- `backend/shared/infrastructure/db/services/operations/`

### 2. Implement the service class

- Subclass `DomainDatabaseService` from `shared.infrastructure.db.services._base`.
- Constructor is only `def __init__(self, db_service: BaseDatabaseService) -> None` via the parent; do not add extra required ctor args (the manager always passes `BaseDatabaseService(DATABASE_URL)`).
- Use `async with self.session() as session:` for ORM work. For writes, call `await self.end_write_session(session)` before exiting the block when you intend to commit (see parent class: respects ambient transaction vs standalone session).
- Imports: prefer **absolute** imports. Domain entities may come from the owning context (`jobs.domain`, `finance.domain`, etc.); that is expected for mapping rows to domain objects. Do not import application or API layers from here.
- SQL remains **Postgres-native** ($1 placeholders, etc.) if you mix raw SQL; most services use SQLModel/ORM helpers.

### 3. Export from `services/__init__.py`

Add:

- `from shared.infrastructure.db.services.<context_pkg> import <Context>DatabaseService`
- Include the class name in `__all__`.

Keeps `from shared.infrastructure.db.services import ...` usable and documents the public surface.

### 4. Register on `DatabaseManager`

**File:** `backend/shared/infrastructure/db/base.py`

- Add one entry to `_service_paths`, keyed by the **public attribute name** (e.g. `"reports"`: `"shared.infrastructure.db.services.reports.ReportsDatabaseService"`).
- The key must be a valid Python identifier; it becomes `db.reports` / `tx.reports`.

**Special built-ins (do not duplicate names):**

- `"sql"` → `RawSQLService` (no `DomainDatabaseService` subclass pattern).
- `"realtime"` → `RealtimeServiceProxy` (constructed with zero args in `_build_service`).

### 5. Type checker stubs (Pyright / IDE)

Still in `base.py`, inside `if TYPE_CHECKING:` at module top:

- Import your new class alongside the others.
- Add an attribute line under **both** class bodies that use the pattern:

  - `class DatabaseManager:` → `mycontext: MyContextDatabaseService`
  - `class TransactionScope:` → same line

If you skip this, runtime works but `tx.mycontext` / `db.mycontext` will not autocomplete or type-check.

### 6. Warmup (optional)

`DatabaseManager.warmup()` preloads a fixed tuple of services. Add your key only if startup should pay the import cost early (e.g. hot path for health or first request). Otherwise omit to keep startup lean.

### 7. Verification

- Run `uv run ruff check` on touched files (from repo root, or `./bin/dev lint` when appropriate).
- Smoke: `async with transaction() as tx:` then access `tx.<your_key>` and call one read method.

## Boundaries (do not violate)

- **Database services** live in `shared/infrastructure`; they must **not** contain use-case orchestration, HTTP, or cross-context business rules beyond persistence and simple queries.
- **Mutations** that belong to another context’s aggregates should go through that context’s **application facade**, not arbitrary updates from a foreign service.
- Prefer **one service package per bounded context** for the main persistence facade; split internal modules with leading underscores (`_ledger.py`) under that package if it grows.

## Adding methods vs adding a service

- **New methods** on an existing `*DatabaseService`: edit that module only; no `base.py` registration changes.
- **New top-level attribute** on `db` / `tx`: new class + full registration and typing steps above.
