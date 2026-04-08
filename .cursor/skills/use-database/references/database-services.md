# Database services - how they work

Background on the `DatabaseManager` lazy-service architecture. For usage patterns, see [../SKILL.md](../SKILL.md).

## What is a database service?

A class under `backend/shared/infrastructure/db/services/` that subclasses `DomainDatabaseService`, owns ORM-backed persistence for one bounded context, and is exposed as `get_database_manager().<name>` / `async with transaction() as tx: tx.<name>`.

This is **not** the same as a repository inside a bounded context (`{context}/infrastructure/*_repo.py`). Repos stay in their context. Database services are the shared SQLModel/session facade the app routes through `DatabaseManager`.

## Package layout

Each service lives in its own **package directory**:

```
backend/shared/infrastructure/db/services/
├── __init__.py             # re-exports all service classes
├── _base.py                # DomainDatabaseService base class
├── raw_sql.py              # RawSQLService (special, not a DomainDatabaseService)
├── catalog/
│   ├── __init__.py          # exports CatalogDatabaseService
│   └── catalog.py           # implementation
├── finance/
│   ├── __init__.py
│   ├── finance.py
│   └── _invoices.py         # split module for large areas
├── operations/
│   ├── __init__.py
│   └── operations.py
└── ...
```

Do **not** add new services as a single top-level file next to `_base.py` (e.g. `services/mycontext.py`). Existing single-file modules are legacy.

Reference implementations: `finance/`, `operations/`, `purchasing/`.

## Lazy loading via DatabaseManager

`DatabaseManager._service_paths` maps attribute names to dotted import paths:

```python
_service_paths = {
    "catalog": "shared.infrastructure.db.services.catalog.CatalogDatabaseService",
    "finance": "shared.infrastructure.db.services.finance.FinanceDatabaseService",
    ...
}
```

On first access (`db.catalog`), `__getattr__` imports the module, instantiates the class with `BaseDatabaseService(DATABASE_URL)`, caches it, and returns it. Subsequent accesses hit the cache.

## DomainDatabaseService base class

Located in `_base.py`:

```python
class DomainDatabaseService:
    def __init__(self, db_service: BaseDatabaseService) -> None:
        self.db_service = db_service

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with get_session() as session:
            yield session

    @staticmethod
    async def end_write_session(session: AsyncSession) -> None:
        ambient = uow._tx_session.get()
        if ambient is not None and ambient is session:
            await session.flush()
        else:
            await session.commit()
```

- Constructor only takes `BaseDatabaseService` - no extra args.
- `async with self.session() as session:` for ORM work.
- `await self.end_write_session(session)` to commit (or flush when inside an ambient transaction).

## Implementing a service class

- Subclass `DomainDatabaseService`.
- Use absolute imports. Domain entities may come from the owning context (`jobs.domain`, `finance.domain`).
- Do not import application or API layers.
- SQL is Postgres-native (`$1` placeholders) when mixing raw SQL; most services use SQLModel/ORM helpers.

## Registration steps (manual)

If not using the scaffolding script, registration requires:

### 1. Create the package

`services/<context>/` with `__init__.py` exporting `<Context>DatabaseService`.

### 2. Re-export from services/__init__.py

```python
from shared.infrastructure.db.services.<context> import <Context>DatabaseService
```

Add to `__all__`.

### 3. Register on DatabaseManager

In `base.py`, add to `_service_paths`:

```python
"<context>": "shared.infrastructure.db.services.<context>.<Context>DatabaseService",
```

### 4. Type checker stubs

In `base.py`, inside `if TYPE_CHECKING:` at module top, import the class. Add attribute lines on **both** `DatabaseManager` and `TransactionScope`:

```python
if TYPE_CHECKING:
    from shared.infrastructure.db.services.<context> import <Context>DatabaseService

class DatabaseManager:
    if TYPE_CHECKING:
        <context>: <Context>DatabaseService

class TransactionScope:
    if TYPE_CHECKING:
        <context>: <Context>DatabaseService
```

### 5. Warmup (optional)

`DatabaseManager.warmup()` preloads a fixed tuple. Add the key only if the service must be loaded at startup.

## Special services

- `"sql"` - `RawSQLService` (not a `DomainDatabaseService` subclass).
- `"realtime"` - `RealtimeServiceProxy` (constructed with zero args).

## Boundaries

- Database services live in `shared/infrastructure`; they must not contain use-case orchestration, HTTP, or cross-context business rules.
- Mutations that belong to another context's aggregates go through that context's application facade.
- Prefer one service package per bounded context. Split internals with leading underscores (`_ledger.py`).

## TransactionScope

`async with db.transaction() as tx:` creates a `TransactionScope` that delegates `__getattr__` to `DatabaseManager`. This means `tx.finance` and `db.finance` resolve to the same cached service instance, but the ambient `_tx_session` contextvar ensures ORM sessions participate in the transaction.

## Singleton behavior

`get_database_manager()` returns a module-level `_default_manager`. Each lazy sub-service is constructed once and cached. Repeated `get_database_manager().catalog.foo()` is not a performance problem - it's just verbose, which is why the `_db_<context>()` accessor pattern exists.
