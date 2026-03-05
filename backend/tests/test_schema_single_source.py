"""
Schema single-source-of-truth tests.

Verifies that the context schema.py files (the single source of truth)
produce the exact same logical schema as running the full SQLite migration
chain.  If these tests fail, either a context schema.py is out of date or
a migration introduced a column/table that was never added to the context
schema — i.e. the very drift that caused us pain before.
"""
import aiosqlite
import pytest

from full_schema import FULL_SCHEMA
from shared.infrastructure.migrations.runner import (
    _SQLITE_MIGRATIONS,
    _COMMON_MIGRATIONS,
)


async def _create_db_from_context_schemas() -> dict[str, list[tuple]]:
    """Create a fresh in-memory SQLite DB using the context schemas (single source)."""
    db = await aiosqlite.connect(":memory:")
    for stmt in FULL_SCHEMA:
        await db.execute(stmt)
    await db.commit()
    return await _extract_schema(db)


async def _create_db_from_migration_chain() -> dict[str, list[tuple]]:
    """Create a fresh in-memory SQLite DB by replaying the full migration chain."""
    db = await aiosqlite.connect(":memory:")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)
    await db.commit()

    for _version, migrate_fn in _SQLITE_MIGRATIONS:
        await migrate_fn(db)
    for _version, migrate_fn in _COMMON_MIGRATIONS:
        await migrate_fn(db, dialect="sqlite")

    return await _extract_schema(db)


async def _extract_schema(db: aiosqlite.Connection) -> dict[str, list[tuple]]:
    """Extract {table_name: [(col_name, col_type, notnull, default, pk), ...]} from SQLite."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = [row[0] for row in await cursor.fetchall()]

    schema: dict[str, list[tuple]] = {}
    for table in tables:
        if table == "schema_migrations":
            continue
        cursor = await db.execute(f"PRAGMA table_info({table})")
        cols = await cursor.fetchall()
        schema[table] = [(c[1], c[2], c[3], c[4], c[5]) for c in cols]

    await db.close()
    return schema


@pytest.mark.asyncio
async def test_context_schemas_and_migration_chain_produce_same_tables():
    """Both paths must create the exact same set of tables."""
    ctx_schema = await _create_db_from_context_schemas()
    mig_schema = await _create_db_from_migration_chain()

    ctx_tables = set(ctx_schema.keys())
    mig_tables = set(mig_schema.keys())

    only_in_context = ctx_tables - mig_tables
    only_in_migrations = mig_tables - ctx_tables

    assert not only_in_context, (
        f"Tables in context schemas but missing from migration chain: {only_in_context}\n"
        "Add a migration, or the migration chain is stale."
    )
    assert not only_in_migrations, (
        f"Tables in migration chain but missing from context schemas: {only_in_migrations}\n"
        "Update the relevant context schema.py file."
    )


@pytest.mark.asyncio
async def test_context_schemas_and_migration_chain_produce_same_columns():
    """Every table must have the same columns (name, type, constraints) in both paths."""
    ctx_schema = await _create_db_from_context_schemas()
    mig_schema = await _create_db_from_migration_chain()

    common_tables = set(ctx_schema.keys()) & set(mig_schema.keys())
    diffs: list[str] = []

    for table in sorted(common_tables):
        ctx_cols = {c[0]: c for c in ctx_schema[table]}
        mig_cols = {c[0]: c for c in mig_schema[table]}

        only_ctx = set(ctx_cols) - set(mig_cols)
        only_mig = set(mig_cols) - set(ctx_cols)

        if only_ctx:
            diffs.append(
                f"  {table}: columns in context schema but not migration chain: {only_ctx}"
            )
        if only_mig:
            diffs.append(
                f"  {table}: columns in migration chain but not context schema: {only_mig}"
            )

        for col_name in sorted(set(ctx_cols) & set(mig_cols)):
            ctx_col = ctx_cols[col_name]
            mig_col = mig_cols[col_name]
            if ctx_col != mig_col:
                diffs.append(
                    f"  {table}.{col_name}: context={ctx_col} vs migrations={mig_col}"
                )

    assert not diffs, (
        "Schema drift detected between context schemas and migration chain:\n"
        + "\n".join(diffs)
        + "\n\nContext schemas are the source of truth. Fix the migration chain "
        "or update the context schema."
    )
