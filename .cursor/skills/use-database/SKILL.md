---
name: use-database
description: Add and access lazy-loaded database services on DatabaseManager, and regenerate SQLModel types after schema changes. Use when adding a service, accessing get_database_manager() sub-services, modifying Supabase migrations, or regenerating types.
---

# Use the database layer (SKU-Ops)

Three topics: **adding** a database service, **accessing** services in application/API code, and **regenerating types** after schema changes.

For background on how database services work internally, see [references/database-services.md](references/database-services.md).

---

## 1. Add a new database service

Run the scaffolding script from the repo root:

```bash
pixi run uv run --directory backend python .cursor/skills/use-database/scripts/add_database_service.py <context>
```

Replace `<context>` with the lowercase bounded-context key (e.g. `reports`). The script:

1. Creates the package `backend/shared/infrastructure/db/services/<context>/` with `__init__.py` and `<context>.py` containing the `<Context>DatabaseService` class.
2. Adds the re-export to `services/__init__.py`.
3. Registers the lazy path in `DatabaseManager._service_paths` in `base.py`.
4. Adds `TYPE_CHECKING` stubs on both `DatabaseManager` and `TransactionScope` in `base.py`.

After the script runs, verify with `pixi run lint backend`.

### When NOT to use the script

- **Adding methods** to an existing `*DatabaseService`: edit that service module directly; no registration changes needed.
- **Adding a SQL raw query**: use the existing `get_database_manager().sql` service. Avoid using this as much as possible. Always prefer using *DatabaseService methods instead.

---

## 2. Access database services in application and API code

### Standard pattern: `_db_<context>()`

One **module-level** private helper per context used in the file. Name matches the `DatabaseManager` attribute.

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

### Why a function, not a module-level assignment?

`catalog = get_database_manager().catalog` at module level triggers the lazy import at **import time**, risking circular imports and running before `init_db()`. A zero-arg function defers access until runtime.

### Placement

Put accessors **immediately after imports**, before other module-level definitions. Import `get_database_manager` at module top.

### Local variables inside a function

```python
async def foo() -> None:
    fin = _db_finance()
    await fin.payment_insert(...)
```

### Multiple services in one function (3+ contexts)

Bind the manager locally:

```python
async def reconcile() -> None:
    db = get_database_manager()
    await db.catalog.foo()
    await db.finance.bar()
    await db.operations.baz()
```

### Transaction scopes

`async with transaction() as tx:` yields a `TransactionScope`. Either `_db_*()` helpers or `tx.<name>` work inside the block:

```python
async with transaction() as tx:
    await tx.finance.payment_insert(...)
    await _db_operations().update_status(...)  # also valid
```

### Forbidden patterns

| Pattern | Fix |
|---------|-----|
| `catalog = get_database_manager().catalog` at module level | Use `_db_catalog()` function |
| `_finance()`, `_inv()` | Use `_db_finance()`, `_db_inventory()` |
| Many `get_database_manager().catalog.*` lines without a helper | Add `_db_catalog()` |

---

## 3. Regenerate Supabase types after schema changes

When a Supabase migration adds/changes tables or columns, the SQLModel types must be regenerated.

### When to regenerate

- After adding or modifying a file in `supabase/migrations/`.
- After changing `schema_config.py` (adding a new Postgres schema).
- **Supabase** workflow ([`supabase.yml`](../../../.github/workflows/supabase.yml)) checks for drift on push/PR to `main`/`dev` and runs SQLModel tests; on `main` it can push migrations when the **`supabase_deployment`** environment has `PRIVATE_ACCESS_TOKEN`, `PRIVATE_DB_PASSWORD`, and `PUBLIC_PROJECT_ID` (workflow maps the first two to `SUPABASE_*` for the CLI).

### How to regenerate

Local Supabase must be running (`pixi run supabase` or `pixi run start`).

```bash
pixi run supabase typegen
```

This runs the full pipeline:

1. `supabase gen types --lang=python --local` and `--lang=typescript --local`
2. Parses Pydantic types, TS relationships, and PK columns from migrations
3. Generates `{schema}_sql_model_models.py` per schema under `backend/shared/infrastructure/types/`
4. Formats with `ruff`

Commit the regenerated files:

```bash
git add backend/shared/infrastructure/types/
git commit -m 'chore: regenerate SQLModel types'
```

### Adding a new Postgres schema

1. Extend `SCHEMAS` and `SCHEMA_CLASS_PREFIX` in `.cursor/skills/use-database/scripts/supabase_type_generation/schema_config.py`.
2. Ensure Supabase exposes the schema in generated types and migrations.
3. Run `pixi run supabase typegen` and commit.

### Internals

The pipeline lives at `.cursor/skills/use-database/scripts/supabase_type_generation/`. See [its README](scripts/supabase_type_generation/README.md) for module-by-module details. Tests: `backend/tests/unit/test_sqlmodel_generation/` and `backend/tests/integration/test_sqlmodel_db/`.

---

## Trigger this skill when

- Wiring a new bounded-context database service.
- Refactoring code that calls `get_database_manager()` repeatedly or uses ad hoc helpers.
- Adding or modifying Supabase migrations and needing to regenerate types.
