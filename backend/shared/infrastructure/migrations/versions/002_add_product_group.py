"""Add product_group column and index to products table."""


async def up(conn, dialect: str) -> None:
    await conn.execute("ALTER TABLE products ADD COLUMN product_group TEXT")
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_group ON products (product_group)"
    )
