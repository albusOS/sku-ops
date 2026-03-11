"""Stock repository port — testable contract for stock transaction persistence."""

from typing import Protocol, runtime_checkable

from inventory.domain.stock import StockTransaction


@runtime_checkable
class StockRepoPort(Protocol):
    async def insert_transaction(self, transaction: StockTransaction) -> None: ...

    async def list_by_product(self, product_id: str, limit: int = 50) -> list[dict]: ...
