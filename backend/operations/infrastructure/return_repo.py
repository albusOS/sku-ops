"""Return repository."""
import json
from typing import Optional, Union

from operations.domain.returns import MaterialReturn
from shared.infrastructure.database import get_connection


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row) if hasattr(row, "keys") else {}
    if d and "items" in d and isinstance(d["items"], str):
        d["items"] = json.loads(d["items"]) if d["items"] else []
    return d


async def insert(ret: Union[MaterialReturn, dict], conn=None) -> None:
    ret_dict = ret if isinstance(ret, dict) else ret.model_dump()
    in_transaction = conn is not None
    conn = conn or get_connection()
    org_id = ret_dict.get("organization_id") or "default"
    items_json = json.dumps(
        [i if isinstance(i, dict) else i.model_dump() for i in ret_dict["items"]]
    )
    await conn.execute(
        """INSERT INTO returns (id, withdrawal_id, contractor_id, contractor_name,
           billing_entity, job_id, items, subtotal, tax, total, cost_total,
           reason, notes, credit_note_id, processed_by_id, processed_by_name,
           organization_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ret_dict["id"],
            ret_dict["withdrawal_id"],
            ret_dict["contractor_id"],
            ret_dict.get("contractor_name", ""),
            ret_dict.get("billing_entity", ""),
            ret_dict.get("job_id", ""),
            items_json,
            ret_dict["subtotal"],
            ret_dict["tax"],
            ret_dict["total"],
            ret_dict["cost_total"],
            ret_dict.get("reason", "other"),
            ret_dict.get("notes"),
            ret_dict.get("credit_note_id"),
            ret_dict.get("processed_by_id", ""),
            ret_dict.get("processed_by_name", ""),
            org_id,
            ret_dict.get("created_at", ""),
            ret_dict.get("updated_at", ""),
        ),
    )
    if not in_transaction:
        await conn.commit()


async def get_by_id(return_id: str, organization_id: Optional[str] = None) -> Optional[dict]:
    conn = get_connection()
    if organization_id:
        cursor = await conn.execute(
            "SELECT * FROM returns WHERE id = ? AND (organization_id = ? OR organization_id IS NULL)",
            (return_id, organization_id),
        )
    else:
        cursor = await conn.execute("SELECT * FROM returns WHERE id = ?", (return_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row)


async def list_returns(
    contractor_id: Optional[str] = None,
    withdrawal_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 500,
    organization_id: Optional[str] = None,
) -> list:
    conn = get_connection()
    org_id = organization_id or "default"
    query = "SELECT * FROM returns WHERE (organization_id = ? OR organization_id IS NULL)"
    params: list = [org_id]
    if contractor_id:
        query += " AND contractor_id = ?"
        params.append(contractor_id)
    if withdrawal_id:
        query += " AND withdrawal_id = ?"
        params.append(withdrawal_id)
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def list_by_withdrawal(withdrawal_id: str) -> list:
    conn = get_connection()
    cursor = await conn.execute(
        "SELECT * FROM returns WHERE withdrawal_id = ? ORDER BY created_at DESC",
        (withdrawal_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


class ReturnRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_returns = staticmethod(list_returns)
    list_by_withdrawal = staticmethod(list_by_withdrawal)


return_repo = ReturnRepo()
