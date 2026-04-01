"""Stock transaction repository — delegates to InventoryDatabaseService."""

from inventory.domain.stock import StockTransaction
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def insert_transaction(tx: StockTransaction) -> None:
    db = get_database_manager()
    await db.inventory.insert_stock_transaction(tx)


async def list_by_product(
    sku_id: str,
    limit: int = 50,
) -> list[StockTransaction]:
    db = get_database_manager()
    return await db.inventory.list_stock_transactions_by_product(
        get_org_id(), sku_id, limit=limit
    )


class StockRepo:
    insert_transaction = staticmethod(insert_transaction)
    list_by_product = staticmethod(list_by_product)


stock_repo = StockRepo()
