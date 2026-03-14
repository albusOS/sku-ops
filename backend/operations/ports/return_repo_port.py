"""Return repository port."""

from typing import Protocol

from operations.domain.returns import MaterialReturn


class ReturnRepoPort(Protocol):
    async def insert(self, ret: MaterialReturn) -> None: ...
    async def get_by_id(
        self,
        return_id: str,
    ) -> MaterialReturn | None: ...
    async def list_returns(
        self,
        contractor_id: str | None = None,
        withdrawal_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 500,
    ) -> list[MaterialReturn]: ...
    async def list_by_withdrawal(self, withdrawal_id: str) -> list[MaterialReturn]: ...
