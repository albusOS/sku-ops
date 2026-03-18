"""SKU generation and preview routes."""

from fastapi import APIRouter, HTTPException

from catalog.application.sku_service import preview_sku, sku_overview
from shared.api.deps import CurrentUserDep
from shared.kernel.errors import ResourceNotFoundError

router = APIRouter(prefix="/sku", tags=["sku"])


@router.get("/preview")
async def get_sku_preview(
    _current_user: CurrentUserDep,
    category_id: str,
    product_family_id: str | None = None,
    family_name: str | None = None,
):
    """Preview the next SKU for a category and family (without consuming it)."""
    try:
        return await preview_sku(category_id, product_family_id, family_name)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/overview")
async def get_sku_overview(
    _current_user: CurrentUserDep,
    family_name: str | None = None,
):
    """SKU system overview: format, departments with example SKUs."""
    return await sku_overview(family_name)
