"""Product family CRUD routes - parent concept for SKU grouping."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from catalog.application.product_family_lifecycle import (
    create_product,
    delete_product,
    update_product,
)
from catalog.application.queries import (
    count_product_families,
    get_department_by_id,
    get_product_family_by_id,
    list_skus_by_product,
)
from catalog.application.queries import (
    list_product_families as query_list_product_families,
)
from catalog.application.sku_lifecycle import create_sku
from catalog.domain.product import SkuCreate
from inventory.application.inventory_service import process_import_stock_changes
from shared.api.deps import AdminDep, CurrentUserDep
from shared.infrastructure.middleware.audit import audit_log
from shared.kernel.errors import ResourceNotFoundError

router = APIRouter(prefix="/products", tags=["catalog-products"])


class ProductCreateRequest(BaseModel):
    name: str
    description: str = ""
    category_id: str


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: str | None = None


@router.get("")
async def list_product_families(
    current_user: CurrentUserDep,
    category_id: str | None = None,
    search: str | None = None,
    limit: int | None = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items = await query_list_product_families(
        category_id=category_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    result = [p.model_dump() for p in items]
    if limit is not None:
        total = await count_product_families(category_id=category_id, search=search)
        return {"items": result, "total": total}
    return result


@router.get("/{product_id}")
async def get_product_family(product_id: str, current_user: CurrentUserDep):
    product = await get_product_family_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    skus = await list_skus_by_product(product_id)
    result = product.model_dump()
    result["skus"] = [s.model_dump() for s in skus]
    return result


@router.post("")
async def create_product_family(data: ProductCreateRequest, current_user: AdminDep):
    department = await get_department_by_id(data.category_id)
    if not department:
        raise HTTPException(status_code=400, detail="Category not found")
    try:
        product = await create_product(
            name=data.name,
            category_id=data.category_id,
            category_name=department.name,
            description=data.description,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return product.model_dump()


@router.put("/{product_id}")
async def update_product_family(
    product_id: str, data: ProductUpdateRequest, current_user: AdminDep
):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        result = await update_product(product_id, update_data)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result.model_dump()


@router.delete("/{product_id}")
async def delete_product_family(product_id: str, request: Request, current_user: AdminDep):
    product = await get_product_family_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        await delete_product(product_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await audit_log(
        user_id=current_user.id,
        action="product.delete",
        resource_type="product",
        resource_id=product_id,
        details={"name": product.name},
        request=request,
        org_id=current_user.organization_id,
    )
    return {"message": "Product deleted"}


@router.get("/{product_id}/skus")
async def list_product_skus(product_id: str, current_user: CurrentUserDep):
    product = await get_product_family_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    skus = await list_skus_by_product(product_id)
    return [s.model_dump() for s in skus]


@router.post("/{product_id}/skus")
async def create_product_sku(product_id: str, data: SkuCreate, current_user: AdminDep):
    product = await get_product_family_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    department = await get_department_by_id(data.category_id)
    if not department:
        raise HTTPException(status_code=400, detail="Category not found")
    sku = await create_sku(
        product_id=product_id,
        category_id=data.category_id,
        category_name=department.name,
        name=data.name,
        description=data.description or "",
        price=data.price,
        cost=data.cost,
        quantity=data.quantity,
        min_stock=data.min_stock,
        barcode=data.barcode,
        base_unit=data.base_unit,
        sell_uom=data.sell_uom,
        pack_qty=data.pack_qty,
        purchase_uom=data.purchase_uom,
        purchase_pack_qty=data.purchase_pack_qty,
        user_id=current_user.id,
        user_name=current_user.name,
        on_stock_import=process_import_stock_changes,
    )
    return sku.model_dump()
