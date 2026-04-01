"""Department repository."""

from datetime import UTC, datetime

from catalog.domain.department import Department
from shared.infrastructure.db import get_org_id, sql_execute


def _row_to_model(row) -> Department | None:
    if row is None:
        return None
    d = dict(row)
    return Department.model_validate(d)


async def list_all() -> list[Department]:
    org_id = get_org_id()
    cursor = await sql_execute(
        """SELECT id, name, code, description, sku_count, organization_id, created_at FROM departments
           WHERE organization_id = $1 AND deleted_at IS NULL""",
        (org_id,),
    )
    rows = cursor.rows
    return [d for r in rows if (d := _row_to_model(r)) is not None]


async def get_by_id(dept_id: str) -> Department | None:
    org_id = get_org_id()
    cursor = await sql_execute(
        """SELECT id, name, code, description, sku_count, organization_id, created_at FROM departments
           WHERE id = $1 AND organization_id = $2 AND deleted_at IS NULL""",
        (dept_id, org_id),
    )
    row = (cursor.rows[0] if cursor.rows else None)
    return _row_to_model(row)


async def get_by_code(code: str) -> Department | None:
    org_id = get_org_id()
    cursor = await sql_execute(
        """SELECT id, name, code, description, sku_count, organization_id, created_at FROM departments
           WHERE code = $1 AND organization_id = $2 AND deleted_at IS NULL""",
        (code.upper(), org_id),
    )
    row = (cursor.rows[0] if cursor.rows else None)
    return _row_to_model(row)


async def insert(department: Department) -> None:
    dept_dict = department.model_dump()
    dept_dict["organization_id"] = dept_dict.get("organization_id") or get_org_id()
    org_id = dept_dict["organization_id"]
    await sql_execute(
        """INSERT INTO departments (id, name, code, description, sku_count, organization_id, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        (
            dept_dict["id"],
            dept_dict["name"],
            dept_dict["code"].upper(),
            dept_dict.get("description", ""),
            dept_dict.get("sku_count", 0),
            org_id,
            dept_dict.get("created_at") or datetime.now(UTC),
        ),
    )


async def update(dept_id: str, name: str, description: str) -> Department | None:
    org_id = get_org_id()
    params: list = [name, description or "", dept_id]
    where = "WHERE id = $3 AND organization_id = $4"
    params.append(org_id)
    query = "UPDATE departments SET name = $1, description = $2 "
    query += where
    await sql_execute(query, params)
    await sql_execute(
        "UPDATE skus SET category_name = $1 WHERE category_id = $2 AND organization_id = $3",
        (name, dept_id, org_id),
    )
    await sql_execute(
        "UPDATE products SET category_name = $1 WHERE category_id = $2 AND organization_id = $3",
        (name, dept_id, org_id),
    )
    return await get_by_id(dept_id)


async def count_skus_by_department(dept_id: str) -> int:
    org_id = get_org_id()
    cursor = await sql_execute(
        "SELECT COUNT(*) FROM skus WHERE category_id = $1 AND deleted_at IS NULL AND organization_id = $2",
        (dept_id, org_id),
    )
    row = (cursor.rows[0] if cursor.rows else None)
    return row[0] if row else 0


async def delete(dept_id: str) -> int:
    org_id = get_org_id()
    now = datetime.now(UTC)
    params: list = [now, dept_id]
    where = "WHERE id = $2 AND deleted_at IS NULL AND organization_id = $3"
    params.append(org_id)
    query = "UPDATE departments SET deleted_at = $1 "
    query += where
    cursor = await sql_execute(query, params)
    return cursor.rowcount


async def increment_sku_count(dept_id: str, delta: int) -> None:
    org_id = get_org_id()
    params: list = [delta, dept_id]
    where = "WHERE id = $2 AND organization_id = $3"
    params.append(org_id)
    query = "UPDATE departments SET sku_count = sku_count + $1 "
    query += where
    await sql_execute(query, params)


class DepartmentRepo:
    list_all = staticmethod(list_all)
    get_by_id = staticmethod(get_by_id)
    get_by_code = staticmethod(get_by_code)
    insert = staticmethod(insert)
    update = staticmethod(update)
    count_skus_by_department = staticmethod(count_skus_by_department)
    delete = staticmethod(delete)
    increment_sku_count = staticmethod(increment_sku_count)


department_repo = DepartmentRepo()
