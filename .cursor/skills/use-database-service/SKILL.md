---
name: use-database-service
description: Register lazy-loaded domain database services on DatabaseManager (package under shared/infrastructure/db/services/<context>/, base.py registration, Pyright stubs) and access them consistently via _db_<context>() in application/API code. Use when adding a service, updating DatabaseManager/TransactionScope, or standardizing get_database_manager() usage.
---

# Use database services (SKU-Ops)

This skill covers two things:

1. **Adding** a new lazy domain database service on `DatabaseManager`.
2. **Accessing** `get_database_manager()` and its sub-services in a consistent, safe way.

## Part A: Add a new database service

In this codebase, a **database service** is a class under `backend/shared/infrastructure/db/services/` that subclasses `DomainDatabaseService`, owns ORM-backed persistence for one area, and is exposed as `get_database_manager().<name>` and `async with transaction() as tx: tx.<name>`.

Each service **must** live in its own **package directory** (e.g. `services/mycontext/` with `__init__.py` exporting `MyContextDatabaseService`). Do **not** add new services as a single top-level file next to `base.py` (e.g. `services/mycontext.py`). Existing single-file modules are legacy; new work follows the directory layout only.

This is **not** the same as adding a repository inside a bounded context (`{context}/infrastructure/*_repo.py`). Repos stay in their context; the shared **database service** is the SQLModel/session facade the app uses through `DatabaseManager`.

### Brief checklist (registration)

1. Create package `backend/shared/infrastructure/db/services/<context>/` with `__init__.py` exporting `<Context>DatabaseService(DomainDatabaseService)` (split internals into sibling modules under that directory if needed).
2. Re-export from `services/__init__.py` if you want a stable import path.
3. Register lazy path in `DatabaseManager._service_paths` in `base.py`.
4. Mirror typing: `TYPE_CHECKING` import + attribute on **both** `DatabaseManager` and `TransactionScope` in `base.py`.
5. Optionally extend `warmup()` in `base.py` if this service must be loaded at startup (most do not).

### Detailed registration steps

#### 1. Package layout (required)

- Create a directory `services/<context>/` (lowercase context key, valid Python package name).
- Export `FooDatabaseService` from `services/<context>/__init__.py` so the lazy import path is `shared.infrastructure.db.services.<context>.<Context>DatabaseService` (class name in PascalCase with `DatabaseService` suffix).
- Add modules under the same directory for large areas (e.g. `services/finance/_invoices.py`); keep the public class and `__all__` in `__init__.py` or a single obvious module re-exported there.

Reference implementations:

- `backend/shared/infrastructure/db/services/finance/`
- `backend/shared/infrastructure/db/services/operations/`

#### 2. Implement the service class

- Subclass `DomainDatabaseService` from `shared.infrastructure.db.services._base`.
- Constructor is only `def __init__(self, db_service: BaseDatabaseService) -> None` via the parent; do not add extra required ctor args (the manager always passes `BaseDatabaseService(DATABASE_URL)`).
- Use `async with self.session() as session:` for ORM work. For writes, call `await self.end_write_session(session)` before exiting the block when you intend to commit (see parent class: respects ambient transaction vs standalone session).
- Imports: prefer **absolute** imports. Domain entities may come from the owning context (`jobs.domain`, `finance.domain`, etc.); that is expected for mapping rows to domain objects. Do not import application or API layers from here.
- SQL remains **Postgres-native** ($1 placeholders, etc.) if you mix raw SQL; most services use SQLModel/ORM helpers.

#### 3. Export from `services/__init__.py`

Add:

- `from shared.infrastructure.db.services.<context_pkg> import <Context>DatabaseService`
- Include the class name in `__all__`.

#### 4. Register on `DatabaseManager`

**File:** `backend/shared/infrastructure/db/base.py`

- Add one entry to `_service_paths`, keyed by the **public attribute name** (e.g. `"reports"`: `"shared.infrastructure.db.services.reports.ReportsDatabaseService"`).
- The key must be a valid Python identifier; it becomes `db.reports` / `tx.reports`.

**Special built-ins (do not duplicate names):**

- `"sql"` → `RawSQLService` (no `DomainDatabaseService` subclass pattern).
- `"realtime"` → `RealtimeServiceProxy` (constructed with zero args in `_build_service`).

#### 5. Type checker stubs (Pyright / IDE)

Still in `base.py`, inside `if TYPE_CHECKING:` at module top:

- Import your new class alongside the others.
- Add an attribute line under **both** `DatabaseManager` and `TransactionScope`:

  - `class DatabaseManager:` → `mycontext: MyContextDatabaseService`
  - `class TransactionScope:` → same line

#### 6. Warmup (optional)

`DatabaseManager.warmup()` preloads a fixed tuple of services. Add your key only if startup should pay the import cost early. Otherwise omit.

#### 7. Verification

- Run `uv run ruff check` on touched files (from repo root, or `./bin/dev lint` when appropriate).
- Smoke: `async with transaction() as tx:` then access `tx.<your_key>` and call one read method.

### Boundaries (registration)

- **Database services** live in `shared/infrastructure`; they must **not** contain use-case orchestration, HTTP, or cross-context business rules beyond persistence and simple queries.
- **Mutations** that belong to another context's aggregates should go through that context's **application facade**, not arbitrary updates from a foreign service.
- Prefer **one service package per bounded context** for the main persistence facade; split internal modules with leading underscores (`_ledger.py`) under that package if it grows.

### Adding methods vs adding a service

- **New methods** on an existing `*DatabaseService`: edit that module only; no `base.py` registration changes.
- **New top-level attribute** on `db` / `tx`: new class + full registration and typing steps above.

---

## Part B: Access database services in application and API code

### Why not call `get_database_manager()` inline everywhere?

`get_database_manager()` is effectively a **singleton** (cached `_default_manager`). Each lazy sub-service (e.g. `.catalog`) is constructed once on first access and cached on the manager. Repeated `get_database_manager().catalog.foo()` is **not** a performance bug; it is **verbose** and **inconsistent** across files.

### Standard pattern: `_db_<context>()`

Use one **module-level** private helper per context used in the file. Name it `_db_<context>()` where `<context>` matches the `DatabaseManager` attribute: `catalog`, `finance`, `operations`, `purchasing`, `inventory`, `jobs`, `documents`, `assistant`, `shared`, etc.

```python
from shared.infrastructure.db.base import get_database_manager


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations
```

Call sites:

```python
await _db_finance().invoice_insert(...)
await _db_operations().unlink_withdrawals_from_invoice(...)
```

### Placement and imports

- Put accessors **immediately after imports**, before other module-level definitions (constants may precede them if you already group constants first; keep accessors grouped together).
- **Import `get_database_manager` at module top** from `shared.infrastructure.db.base` (do not stash imports inside functions for this).

### Why a function, not `catalog = get_database_manager().catalog` at module level?

Module-level attribute access triggers lazy import of that service at **import time**, which risks circular imports and running before `init_db()`. A **zero-arg function** defers access until the first call at runtime.

### Local variables inside a function

Inside a single function, you may use locals for readability:

```python
async def foo() -> None:
    fin = _db_finance()
    await fin.payment_insert(...)
```

Avoid reintroducing inconsistent names like `cat`, `pur`, `fin` across the file unless they are short-lived inside one function; prefer `_db_catalog()` at call sites for consistency.

### Multiple services in one function (3+ contexts)

Use a **local** manager binding inside that function (not at module scope):

```python
async def reconcile() -> None:
    db = get_database_manager()
    await db.catalog.foo()
    await db.finance.bar()
    await db.operations.baz()
```

For `RawSQLService`, either `get_database_manager().sql` or the same local `db.sql` pattern.

### Transaction scopes

`async with transaction() as tx:` yields a `TransactionScope` whose `tx.<name>` delegates to the same lazy services as `get_database_manager()`. Either style is valid; most code uses `get_database_manager()` / `_db_*()` inside the block. If you bind `tx`, you can write `await tx.finance.foo()` for symmetry.

### Forbidden patterns

- Module-level eager assignment: `catalog = get_database_manager().catalog` at file top.
- Inconsistent wrapper names: `_finance()`, `_inv()` (*use* `_db_finance()`, `_db_inventory()`).
- Long repeated chains without helpers: many lines of `get_database_manager().catalog.*` *without* `_db_catalog()`.

### Exceptions

- **Circular import guards** (e.g. lazy `get_database_manager` import inside a narrow `try` in infrastructure) may stay as-is when required.
- Code **inside** `shared/infrastructure/db/services/*` that legitimately touches another manager facet (rare) is evaluated case-by-case.

---

## Trigger this skill when

- Wiring a new bounded-context DB facade or splitting a large service package.
- Refactoring a module that calls `get_database_manager()` repeatedly or uses ad hoc `_finance()` / inline locals.
