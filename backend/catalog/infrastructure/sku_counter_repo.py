"""SKU counter repository — per-product-family counters."""

from shared.infrastructure.database import get_connection, get_org_id


def _counter_key(product_family_id: str) -> str:
    """Composite key for org-scoped, family-scoped SKU counters."""
    org = get_org_id()
    return f"{org}|{product_family_id}"


async def get_next_number(product_family_id: str) -> int:
    """Return the next counter value without incrementing (for preview)."""
    conn = get_connection()
    key = _counter_key(product_family_id)
    cursor = await conn.execute(
        "SELECT counter FROM sku_counters WHERE department_code = $1",
        (key,),
    )
    row = await cursor.fetchone()
    return (row[0] + 1) if row else 1


async def get_all_counters() -> dict:
    """Return {family_key: counter} for org's families with counters."""
    conn = get_connection()
    org_id = get_org_id()
    prefix = f"{org_id}|"
    cursor = await conn.execute(
        "SELECT department_code, counter FROM sku_counters WHERE department_code LIKE $1",
        (f"{prefix}%",),
    )
    rows = await cursor.fetchall()
    return {row[0].split("|", 1)[-1]: row[1] for row in rows} if rows else {}


async def increment_and_get(product_family_id: str) -> int:
    key = _counter_key(product_family_id)
    conn = get_connection()
    await conn.execute(
        """INSERT INTO sku_counters (department_code, counter) VALUES ($1, 1)
           ON CONFLICT(department_code) DO UPDATE SET counter = sku_counters.counter + 1""",
        (key,),
    )
    cursor = await conn.execute(
        "SELECT counter FROM sku_counters WHERE department_code = $1",
        (key,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 1


class SkuCounterRepo:
    get_next_number = staticmethod(get_next_number)
    get_all_counters = staticmethod(get_all_counters)
    increment_and_get = staticmethod(increment_and_get)


sku_counter_repo = SkuCounterRepo()
