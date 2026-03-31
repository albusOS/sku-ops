"""SKU counter repository — per-product-family counters."""

from shared.infrastructure.database import get_connection, get_org_id


async def get_next_number(product_family_id: str) -> int:
    """Return the next counter value without incrementing (for preview)."""
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT counter FROM sku_counters WHERE organization_id = $1 AND product_family_id = $2",
        (org_id, product_family_id),
    )
    row = await cursor.fetchone()
    return (row[0] + 1) if row else 1


async def get_all_counters() -> dict:
    """Return {family_key: counter} for org's families with counters."""
    conn = get_connection()
    org_id = get_org_id()
    cursor = await conn.execute(
        "SELECT product_family_id, counter FROM sku_counters WHERE organization_id = $1",
        (org_id,),
    )
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows} if rows else {}


async def increment_and_get(product_family_id: str) -> int:
    conn = get_connection()
    org_id = get_org_id()
    await conn.execute(
        """INSERT INTO sku_counters (organization_id, product_family_id, counter)
           VALUES ($1, $2, 1)
           ON CONFLICT(organization_id, product_family_id)
           DO UPDATE SET counter = sku_counters.counter + 1""",
        (org_id, product_family_id),
    )
    cursor = await conn.execute(
        "SELECT counter FROM sku_counters WHERE organization_id = $1 AND product_family_id = $2",
        (org_id, product_family_id),
    )
    row = await cursor.fetchone()
    return row[0] if row else 1


class SkuCounterRepo:
    get_next_number = staticmethod(get_next_number)
    get_all_counters = staticmethod(get_all_counters)
    increment_and_get = staticmethod(increment_and_get)


sku_counter_repo = SkuCounterRepo()
