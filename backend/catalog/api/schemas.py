
from pydantic import BaseModel


class SuggestUomRequest(BaseModel):
    name: str
    description: str | None = None


class BulkGroupAssign(BaseModel):
    product_ids: list[str]
    product_group: str | None = None
