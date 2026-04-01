"""SKU counter repository — per-product-family counters."""

from shared.infrastructure.db import get_org_id, sql_execute


async def get_next_number(product_family_id: str) -> int:
    """Return the next counter value without incrementing (for preview)."""
    org_id = get_org_id()
    res = await sql_execute(
        "SELECT counter FROM sku_counters WHERE organization_id = $1 AND product_family_id = $2",
        (org_id, product_family_id),
        read_only=True,
        max_rows=2,
    )
    row = res.rows[0] if res.rows else None
    return (row["counter"] + 1) if row else 1


async def get_all_counters() -> dict:
    """Return {family_key: counter} for org's families with counters."""
    org_id = get_org_id()
    res = await sql_execute(
        "SELECT product_family_id, counter FROM sku_counters WHERE organization_id = $1",
        (org_id,),
        read_only=True,
        max_rows=10_000,
    )
    rows = res.rows
    return (
        {row["product_family_id"]: row["counter"] for row in rows}
        if rows
        else {}
    )


async def increment_and_get(product_family_id: str) -> int:
    org_id = get_org_id()
    await sql_execute(
        """INSERT INTO sku_counters (organization_id, product_family_id, counter)
           VALUES ($1, $2, 1)
           ON CONFLICT(organization_id, product_family_id)
           DO UPDATE SET counter = sku_counters.counter + 1""",
        (org_id, product_family_id),
        read_only=False,
    )
    res = await sql_execute(
        "SELECT counter FROM sku_counters WHERE organization_id = $1 AND product_family_id = $2",
        (org_id, product_family_id),
        read_only=True,
        max_rows=2,
    )
    row = res.rows[0] if res.rows else None
    return row["counter"] if row else 1


class SkuCounterRepo:
    get_next_number = staticmethod(get_next_number)
    get_all_counters = staticmethod(get_all_counters)
    increment_and_get = staticmethod(increment_and_get)


sku_counter_repo = SkuCounterRepo()
