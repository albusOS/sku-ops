"""SKU generation and preview routes."""

from fastapi import APIRouter, HTTPException

from catalog.application import queries as catalog_queries
from catalog.application.sku_service import slug_from_name
from shared.api.deps import CurrentUserDep

router = APIRouter(tags=["sku"])

SKU_FORMAT = "DEPT-SLUG-XXXXX"


@router.get("/sku/preview")
async def get_sku_preview(
    _current_user: CurrentUserDep,
    department_id: str,
    product_name: str | None = None,
):
    """Preview the next SKU for a department (without consuming it)."""
    department = await catalog_queries.get_department_by_id(department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    code = department.code
    next_num = await catalog_queries.get_next_sku_number(code)
    slug = slug_from_name(product_name or "", max_len=6) if product_name else "ITM"
    next_sku = f"{code}-{slug}-{str(next_num).zfill(6)}"
    return {"next_sku": next_sku, "department_code": code, "format": SKU_FORMAT, "slug": slug}


@router.get("/sku/overview")
async def get_sku_overview(
    _current_user: CurrentUserDep,
    product_name: str | None = None,
):
    """SKU system overview: format, departments with next available SKU."""
    departments = await catalog_queries.list_departments()
    counters = await catalog_queries.get_sku_counters()
    slug = slug_from_name(product_name or "", max_len=6) if product_name else "ITM"
    depts_with_next = []
    for d in departments:
        code = d["code"]
        next_num = counters.get(code, 0) + 1
        depts_with_next.append(
            {
                **d,
                "next_sku": f"{code}-{slug}-{str(next_num).zfill(6)}",
            }
        )
    return {"format": SKU_FORMAT, "departments": depts_with_next}
