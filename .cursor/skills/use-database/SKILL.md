---
name: use-database
description: Add and access lazy-loaded database services on DatabaseManager, edit the database schema via declarative schemas, and regenerate SQLModel types after schema changes. Use when adding a service, accessing get_database_manager() sub-services, modifying Supabase schema or migrations, or regenerating types.
---

# Use the database layer (SKU-Ops)

Four topics: **adding** a database service, **accessing** services in application/API code, **regenerating types** after schema changes, and **editing the database** via declarative schemas.

For background on how database services work internally, see [references/database-services.md](references/database-services.md).
For the full declarative schema reference, see [references/declarative-schema.md](references/declarative-schema.md).

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

## 4. Edit the database (declarative schema workflow)

This project uses **Supabase declarative schemas**. Schema files in `supabase/schemas/` are the source of truth. You **never** hand-write migration files from scratch. You edit schemas, then generate migrations from the diff.

For the full reference (rollbacks, deployment, dependency ordering), see [references/declarative-schema.md](references/declarative-schema.md).

### The workflow

1. **Edit the schema file** - modify the relevant `supabase/schemas/<NN>-<context>-schema.sql`, or create a new numbered file if adding a new table group.
2. **Generate the migration** - `supabase db diff -f "descriptive_name"` creates a shadow DB from existing migrations, compares it against the declared schema, and writes `supabase/migrations/<timestamp>_descriptive_name.sql`.
3. **Review and tweak** - always inspect the generated migration. Tweak as needed (add DML, reorder, remove no-ops).
4. **Apply locally** - `supabase migration up` (or `supabase db reset --local` to replay everything).
5. **Regenerate types** - `pixi run supabase typegen` (see section 3).

```bash
# Example: add a due_date column to invoices
# 1. Edit supabase/schemas/05-finance-schema.sql (append the column)
# 2. Generate
supabase db diff -f "add_invoice_due_date"
# 3. Review supabase/migrations/<timestamp>_add_invoice_due_date.sql
# 4. Apply
supabase migration up --local
# 5. Regenerate types
pixi run supabase typegen
```

### Forbidden patterns

| Pattern | Why | What to do instead |
|---------|-----|--------------------|
| Hand-write a migration without editing schema files | Schema files drift from actual DB state | Edit the schema file first, then generate |
| Edit only the migration file | Future diffs will try to revert your change | Always keep schema files in sync |
| Run `supabase db diff` without reviewing output | Generated SQL can have no-ops or wrong ordering | Always review before applying |

### Key caveats (diff tool gaps)

The `migra` diff tool does **not** capture these - add them manually to the generated migration:

- **DML** (`INSERT`, `UPDATE`, `DELETE`) - never generated
- **RLS policies** - `ALTER POLICY` not generated; only `CREATE`/`DROP`
- **View ownership** - owner, grants, `SECURITY INVOKER` not tracked
- **Materialized views** - tracking issues
- **Comments, partitions, domains, publications** - not tracked

Always note what you have added manually in your response to the user.

See [references/declarative-schema.md](references/declarative-schema.md) for the full list with issue links.

### Creating a new schema file

Pick the next available number prefix (e.g. `12-new-context-schema.sql`), write your `CREATE TABLE` statements, then follow the standard workflow above.

### Appending columns

Always append new columns to the **end** of table definitions. Views and enums are order-sensitive, and mid-table inserts produce messy diffs.

---

## Trigger this skill when

- Wiring a new bounded-context database service.
- Refactoring code that calls `get_database_manager()` repeatedly or uses ad hoc helpers.
- Adding or modifying Supabase migrations and needing to regenerate types.
- Editing, creating, or modifying database tables, columns, views, or functions.
- Needing to understand the declarative schema workflow or its caveats.
