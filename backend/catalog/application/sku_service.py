"""SKU generation — slug derivation and sequential counter management.

SKU format: DEPT-FAMILYSLUG-NN
  - DEPT: department code (e.g. HDW, PLM, ELC)
  - FAMILYSLUG: derived from the product family name (up to 6 chars)
  - NN: per-family counter, zero-padded to 2 digits (variants rarely exceed 99)
"""

import re

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.errors import ResourceNotFoundError

SKU_FORMAT = "DEPT-FAMILYSLUG-NN"
_DEFAULT_SLUG = "ITM"


def slug_from_name(name: str, max_len: int = 6) -> str:
    """Derive a short alphanumeric slug from product name (e.g. 'copper pipe' → 'COPPER').

    Uppercase, alphanumeric only, truncated to max_len.
    """
    if not name or not str(name).strip():
        return _DEFAULT_SLUG
    s = str(name).strip().upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    if not s:
        return _DEFAULT_SLUG
    return s[:max_len] if len(s) > max_len else s


def _db_catalog():
    return get_database_manager().catalog


async def generate_sku(
    department_code: str,
    product_family_id: str,
    family_name: str | None = None,
) -> str:
    """Generate SKU: DEPT-FAMILYSLUG-NN with per-family counter.

    Uses an 8-char slug from the family name. If the resulting SKU code
    already exists (slug collision between different families), appends
    a hash suffix to disambiguate.
    """
    org_id = get_org_id()
    number = await _db_catalog().sku_counter_increment(
        org_id, product_family_id
    )
    raw_slug = (
        slug_from_name(family_name or "", max_len=8)
        if family_name
        else _DEFAULT_SLUG
    )
    candidate = f"{department_code}-{raw_slug}-{str(number).zfill(2)}"

    # Check for collision and disambiguate if needed
    existing = await _db_catalog().find_sku_by_code(org_id, candidate)
    if existing is None:
        return candidate

    # Collision — use a shorter slug + hash from the family ID
    suffix = product_family_id[:4].upper()
    slug = (
        slug_from_name(family_name or "", max_len=4)
        if family_name
        else _DEFAULT_SLUG
    )
    return f"{department_code}-{slug}{suffix}-{str(number).zfill(2)}"


async def preview_sku(
    category_id: str,
    product_family_id: str | None = None,
    family_name: str | None = None,
) -> dict:
    """Preview the next SKU for a family without consuming the counter."""
    org_id = get_org_id()
    department = await _db_catalog().get_department_by_id(category_id, org_id)
    if not department:
        raise ResourceNotFoundError("Category", category_id)
    code = department.code
    slug = (
        slug_from_name(family_name or "", max_len=8)
        if family_name
        else _DEFAULT_SLUG
    )
    if product_family_id:
        next_num = await _db_catalog().sku_counter_next_preview(
            org_id, product_family_id
        )
    else:
        next_num = 1
    return {
        "next_sku": f"{code}-{slug}-{str(next_num).zfill(2)}",
        "department_code": code,
        "format": SKU_FORMAT,
        "slug": slug,
    }


async def sku_overview(family_name: str | None = None) -> dict:
    """Return SKU format info and example SKU for every department."""
    org_id = get_org_id()
    departments = await _db_catalog().list_departments(org_id)
    slug = (
        slug_from_name(family_name or "", max_len=8)
        if family_name
        else _DEFAULT_SLUG
    )
    depts = []
    for d in departments:
        dept_data = d.model_dump()
        dept_data["example_sku"] = f"{d.code}-{slug}-01"
        depts.append(dept_data)
    return {"format": SKU_FORMAT, "departments": depts}
