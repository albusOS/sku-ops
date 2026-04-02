"""Stock history and adjustment routes - inventory bounded context."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from inventory.application.inventory_service import (
    get_stock_history,
    process_adjustment_stock_changes,
)
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.middleware.audit import audit_log

router = APIRouter(prefix="/stock", tags=["stock"])


class AdjustStockRequest(BaseModel):
    quantity_delta: float
    reason: str = "correction"


@router.get("/{sku_id}/history")
async def get_product_stock_history(
    sku_id: str,
    current_user: AdminDep,
    limit: int = Query(50, ge=1, le=500),
):
    product = await get_database_manager().catalog.get_sku_by_id(
        sku_id, get_org_id()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    history = await get_stock_history(sku_id=sku_id, limit=limit)
    return {"sku_id": sku_id, "sku": product.sku, "history": history}


@router.post("/{sku_id}/adjust")
async def adjust_stock(
    sku_id: str,
    data: AdjustStockRequest,
    request: Request,
    current_user: AdminDep,
):
    try:
        await process_adjustment_stock_changes(
            sku_id=sku_id,
            quantity_delta=data.quantity_delta,
            reason=data.reason,
            user_id=current_user.id,
            user_name=current_user.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await audit_log(
        user_id=current_user.id,
        action="stock.adjust",
        resource_type="sku",
        resource_id=sku_id,
        details={"quantity_delta": data.quantity_delta, "reason": data.reason},
        request=request,
        org_id=current_user.organization_id,
    )
    return {"message": "Stock adjusted"}
