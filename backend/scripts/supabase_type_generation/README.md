# Supabase SQLModel type generation

Database-first pipeline: Postgres (via Supabase) is the source of truth. This package turns Supabase’s generated API types plus relationship metadata into **`SQLModel`** table classes for `backend/shared/infrastructure/types/`.

## How to run

From the **repo root**, with local Supabase up (`./bin/dev db` or `supabase start`):

```bash
PYTHONPATH=backend:. uv run python -m backend.scripts.supabase_type_generation.supabase_db_to_sql_models --local
```

- **`--skip-cli`** - Do not call `supabase gen types`; reuse existing `{schema}_database_types.py` / `.ts` under `types/`.
- **`--schemas public,other`** - Override schemas (default: `schema_config.SCHEMAS`).
- **`--types-dir /path`** - Override output directory (default: `backend/shared/infrastructure/types`).

CI runs the same entrypoint after `supabase start` and fails if generated files drift; see `.github/workflows/codegen.yml`.

## Execution order (what runs when)

You normally invoke only **`supabase_db_to_sql_models.py`**. It runs steps in this order:

1. **`supabase gen types --lang=python --local`** and **`--lang=typescript --local`** (unless `--skip-cli`).
2. **Write raw dumps** per configured schema: `{schema}_database_types.py` and `{schema}_database_types.ts`.
3. **`supabase_sql_migration_pk_parser.extract_primary_keys`** - Scan `supabase/migrations/` for primary key columns (DDL only used for PKs).
4. **Per schema**:
   - **`supabase_types_to_pydantic_models.parse_pydantic_types`** - AST parse the Python types; keep row models, drop Insert/Update `TypedDict`s.
   - **`supabase_ts_relationship_parser.parse_ts_relationships`** - Parse TS output for FK metadata and M2M link tables (`referencedRelation`, etc.).
   - **`supabase_pydantic_models_to_sql_models.generate_sqlmodel_code`** - Merge fields, FKs, relationships, `back_populates`, link models, ordering; uses **`pydantic_to_sql_model_type_mapping`** for column/Python types.
5. **Write** `{schema}_sql_model_models.py`.
6. **`ruff format`** on generated `*_sql_model_models.py` files (via `uv run` when available).

There is no separate “runner” script; the orchestrator imports the modules above in that sequence.

## Module map

| Module | Role |
|--------|------|
| `schema_config.py` | Lists schemas to generate and class name prefixes; order matters for cross-schema FK resolution. |
| `supabase_db_to_sql_models.py` | CLI + orchestration, file I/O, ruff. |
| `supabase_types_to_pydantic_models.py` | Parse Supabase Python types into internal model/field structures. |
| `supabase_ts_relationship_parser.py` | Relationships and link tables from Supabase TypeScript types. |
| `supabase_sql_migration_pk_parser.py` | PK columns from migration SQL. |
| `pydantic_to_sql_model_type_mapping.py` | Pydantic-style annotations to SQLModel/SQLAlchemy types. |
| `supabase_pydantic_models_to_sql_models.py` | Emit final `SQLModel` code (relationships, M2M, ordering, reserved-name fixes). |

## Outputs

Under `backend/shared/infrastructure/types/` (by default):

- `{schema}_database_types.py` - Raw `supabase gen types --lang=python`.
- `{schema}_database_types.ts` - Raw `supabase gen types --lang=typescript`.
- `{schema}_sql_model_models.py` - Generated **`SQLModel`** classes (what the app should import for ORM usage).

Adding a new Postgres schema later: extend **`SCHEMAS`** (and **`SCHEMA_CLASS_PREFIX`**) in `schema_config.py`, ensure Supabase exposes it in generated types and migrations, then regenerate and commit the new files.

## Tests

- **Unit:** `backend/tests/unit/test_sqlmodel_generation/` - Parsers, mapping, generator behavior.
- **Integration:** `backend/tests/integration/test_sqlmodel_db/` - CRUD and relationships against a real DB (`DATABASE_URL` / local Supabase).
