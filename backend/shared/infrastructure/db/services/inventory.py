"""Inventory / stock / cycle counts via SQLModel and session-bound SQL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text, update

from inventory.domain.cycle_count import CycleCount, CycleCountItem
from inventory.domain.stock import StockTransaction, StockTransactionType
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.types.public_sql_model_models import (
    CycleCountItems,
    CycleCounts,
    StockTransactions,
)

if TYPE_CHECKING:
    from datetime import datetime


def _stock_row_to_domain(row: StockTransactions) -> StockTransaction:
    return StockTransaction(
        id=str(row.id),
        organization_id=str(row.organization_id),
        created_at=row.created_at,
        sku_id=str(row.sku_id),
        sku=row.sku,
        product_name=row.product_name,
        quantity_delta=row.quantity_delta,
        quantity_before=row.quantity_before,
        quantity_after=row.quantity_after,
        unit=row.unit,
        transaction_type=StockTransactionType(row.transaction_type),
        reference_id=row.reference_id,
        reference_type=row.reference_type,
        reason=row.reason,
        original_quantity=row.original_quantity,
        original_unit=row.original_unit,
        user_id=str(row.user_id),
        user_name=row.user_name,
    )


def _cycle_row_to_domain(row: CycleCounts) -> CycleCount:
    st = row.status
    if hasattr(st, "value"):
        st = st.value
    return CycleCount(
        id=str(row.id),
        organization_id=str(row.organization_id),
        created_at=row.created_at,
        status=st,
        scope=row.scope,
        created_by_id=str(row.created_by_id),
        created_by_name=row.created_by_name or "",
        committed_by_id=str(row.committed_by_id) if row.committed_by_id else None,
        committed_at=row.committed_at,
    )


def _cci_row_to_domain(row: CycleCountItems) -> CycleCountItem:
    return CycleCountItem(
        id=str(row.id),
        organization_id="",
        cycle_count_id=str(row.cycle_count_id),
        created_at=row.created_at,
        sku_id=str(row.sku_id),
        sku=row.sku,
        product_name=row.product_name,
        snapshot_qty=row.snapshot_qty,
        counted_qty=row.counted_qty,
        variance=row.variance,
        unit=row.unit,
        notes=row.notes,
    )


class InventoryDatabaseService(DomainDatabaseService):
    async def insert_stock_transaction(self, tx: StockTransaction) -> None:
        row = StockTransactions(
            id=as_uuid_required(tx.id),
            sku_id=as_uuid_required(tx.sku_id),
            sku=tx.sku,
            product_name=tx.product_name,
            quantity_delta=tx.quantity_delta,
            quantity_before=tx.quantity_before,
            quantity_after=tx.quantity_after,
            unit=tx.unit,
            transaction_type=tx.transaction_type.value,
            reference_id=tx.reference_id,
            reference_type=tx.reference_type,
            reason=tx.reason,
            original_quantity=tx.original_quantity,
            original_unit=tx.original_unit,
            user_id=as_uuid_required(tx.user_id),
            user_name=tx.user_name,
            organization_id=as_uuid_required(tx.organization_id),
            created_at=tx.created_at,
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def list_stock_transactions_by_product(
        self, org_id: str, sku_id: str, *, limit: int = 50
    ) -> list[StockTransaction]:
        oid = as_uuid_required(org_id)
        sid = as_uuid_required(sku_id)
        async with self.session() as session:
            stmt = (
                select(StockTransactions)
                .where(
                    StockTransactions.sku_id == sid,
                    StockTransactions.organization_id == oid,
                )
                .order_by(StockTransactions.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [_stock_row_to_domain(r) for r in rows]

    async def insert_cycle_count(self, count: CycleCount) -> None:
        d = count.model_dump()
        st = d["status"]
        if hasattr(st, "value"):
            st = st.value
        row = CycleCounts(
            id=as_uuid_required(d["id"]),
            organization_id=as_uuid_required(d["organization_id"]),
            status=st,
            scope=d.get("scope"),
            created_by_id=as_uuid_required(d["created_by_id"]),
            created_by_name=d.get("created_by_name", "") or "",
            committed_by_id=as_uuid_required(d["committed_by_id"])
            if d.get("committed_by_id")
            else None,
            committed_at=d.get("committed_at"),
            created_at=d["created_at"],
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def insert_cycle_count_item(self, item: CycleCountItem) -> None:
        d = item.model_dump()
        row = CycleCountItems(
            id=as_uuid_required(d["id"]),
            cycle_count_id=as_uuid_required(d["cycle_count_id"]),
            sku_id=as_uuid_required(d["sku_id"]),
            sku=d["sku"],
            product_name=d.get("product_name", "") or "",
            snapshot_qty=d["snapshot_qty"],
            counted_qty=d.get("counted_qty"),
            variance=d.get("variance"),
            unit=d.get("unit", "each"),
            notes=d.get("notes"),
            created_at=d["created_at"],
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def update_cycle_count_item_counted(
        self,
        org_id: str,
        item_id: str,
        counted_qty: float,
        variance: float,
        notes: str | None,
    ) -> CycleCountItem | None:
        oid = as_uuid_required(org_id)
        iid = as_uuid_required(item_id)
        async with self.session() as session:
            sub = select(CycleCounts.id).where(CycleCounts.organization_id == oid)
            stmt = (
                update(CycleCountItems)
                .where(
                    CycleCountItems.id == iid,
                    CycleCountItems.cycle_count_id.in_(sub),
                )
                .values(
                    counted_qty=counted_qty,
                    variance=variance,
                    notes=notes,
                )
                .returning(CycleCountItems)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            await self.end_write_session(session)
            return _cci_row_to_domain(row) if row else None

    async def commit_cycle_count(
        self,
        org_id: str,
        count_id: str,
        committed_by_id: str,
        committed_at: datetime,
    ) -> bool:
        oid = as_uuid_required(org_id)
        cid = as_uuid_required(count_id)
        uid = as_uuid_required(committed_by_id)
        async with self.session() as session:
            stmt = (
                update(CycleCounts)
                .where(
                    CycleCounts.id == cid,
                    CycleCounts.status == "open",
                    CycleCounts.organization_id == oid,
                )
                .values(
                    status="committed",
                    committed_by_id=uid,
                    committed_at=committed_at,
                )
            )
            result = await session.execute(stmt)
            await self.end_write_session(session)
            return (result.rowcount or 0) > 0

    async def get_cycle_count(self, org_id: str, count_id: str) -> CycleCount | None:
        oid = as_uuid_required(org_id)
        cid = as_uuid_required(count_id)
        async with self.session() as session:
            r = await session.execute(
                select(CycleCounts).where(CycleCounts.id == cid, CycleCounts.organization_id == oid)
            )
            row = r.scalar_one_or_none()
            return _cycle_row_to_domain(row) if row else None

    async def list_cycle_counts(
        self, org_id: str, *, status: str | None = None
    ) -> list[CycleCount]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(CycleCounts).where(CycleCounts.organization_id == oid)
            if status:
                stmt = stmt.where(CycleCounts.status == status)
            stmt = stmt.order_by(CycleCounts.created_at.desc())
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [_cycle_row_to_domain(r) for r in rows]

    async def list_cycle_count_items(
        self, org_id: str, cycle_count_id: str
    ) -> list[CycleCountItem]:
        oid = as_uuid_required(org_id)
        ccid = as_uuid_required(cycle_count_id)
        async with self.session() as session:
            stmt = (
                select(CycleCountItems)
                .join(
                    CycleCounts,
                    CycleCountItems.cycle_count_id == CycleCounts.id,
                )
                .where(
                    CycleCountItems.cycle_count_id == ccid,
                    CycleCounts.organization_id == oid,
                )
                .order_by(CycleCountItems.sku)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [_cci_row_to_domain(r) for r in rows]

    async def get_cycle_count_item(
        self, org_id: str, item_id: str, cycle_count_id: str
    ) -> CycleCountItem | None:
        oid = as_uuid_required(org_id)
        iid = as_uuid_required(item_id)
        ccid = as_uuid_required(cycle_count_id)
        async with self.session() as session:
            stmt = (
                select(CycleCountItems)
                .join(
                    CycleCounts,
                    CycleCountItems.cycle_count_id == CycleCounts.id,
                )
                .where(
                    CycleCountItems.id == iid,
                    CycleCountItems.cycle_count_id == ccid,
                    CycleCounts.organization_id == oid,
                )
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return _cci_row_to_domain(row) if row else None

    async def withdrawal_velocity(
        self, org_id: str, sku_ids: list[str], since: datetime
    ) -> dict[str, float]:
        if not sku_ids:
            return {}
        oid = as_uuid_required(org_id)
        keys = [f"sid{i}" for i in range(len(sku_ids))]
        ph = ", ".join(f":{k}" for k in keys)
        params: dict[str, Any] = {k: as_uuid_required(sku_ids[i]) for i, k in enumerate(keys)}
        params["since"] = since
        params["org_id"] = oid
        q = text(
            "SELECT sku_id, COALESCE(SUM(ABS(quantity_delta)), 0) AS total_used "
            "FROM stock_transactions "
            f"WHERE sku_id IN ({ph}) AND transaction_type = 'WITHDRAWAL' "
            "AND created_at >= :since AND organization_id = :org_id "
            "GROUP BY sku_id"
        )
        async with self.session() as session:
            result = await session.execute(q, params)
            return {str(row["sku_id"]): float(row["total_used"]) for row in result.mappings()}

    async def daily_withdrawal_activity(
        self, org_id: str, since: datetime, sku_id: str | None = None
    ) -> list[dict]:
        oid = as_uuid_required(org_id)
        params: dict[str, Any] = {"org_id": oid, "since": since}
        sku_filter = ""
        if sku_id:
            sku_filter = " AND sku_id = :sku_id"
            params["sku_id"] = as_uuid_required(sku_id)
        q = text(
            "SELECT DATE(created_at) AS day,"
            " COUNT(*) AS transaction_count,"
            " COALESCE(SUM(ABS(quantity_delta)), 0) AS units_moved"
            " FROM stock_transactions"
            " WHERE organization_id = :org_id"
            " AND transaction_type = 'WITHDRAWAL'"
            " AND created_at >= :since" + sku_filter + " GROUP BY day"
            " ORDER BY day"
        )
        async with self.session() as session:
            result = await session.execute(q, params)
            return [dict(r) for r in result.mappings()]

    async def demand_normalized_velocity(
        self, org_id: str, sku_ids: list[str], days: int = 30
    ) -> dict[str, dict]:
        if not sku_ids:
            return {}
        oid = as_uuid_required(org_id)
        keys = [f"sid{i}" for i in range(len(sku_ids))]
        ph = ", ".join(f":{k}" for k in keys)
        params: dict[str, Any] = {k: as_uuid_required(sku_ids[i]) for i, k in enumerate(keys)}
        params["days"] = days
        params["org_id"] = oid
        query = text(
            f"""
    WITH daily AS (
        SELECT sku_id,
               DATE(created_at) AS day,
               COALESCE(SUM(ABS(quantity_delta)), 0) AS qty
        FROM stock_transactions
        WHERE sku_id IN ({ph})
          AND transaction_type = 'WITHDRAWAL'
          AND created_at >= (NOW() - make_interval(days => :days))
          AND organization_id = :org_id
        GROUP BY sku_id, DATE(created_at)
    ),
    iqr AS (
        SELECT sku_id,
               PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY qty) AS q1,
               PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY qty) AS median_daily,
               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY qty) AS q3,
               COUNT(*) AS total_days,
               SUM(qty) AS raw_total,
               AVG(qty) AS mean_daily
        FROM daily
        GROUP BY sku_id
    )
    SELECT i.sku_id,
           i.raw_total,
           i.median_daily,
           i.mean_daily,
           i.total_days,
           i.q1, i.q3,
           COALESCE(SUM(CASE WHEN d.qty <= i.q3 + 1.5 * (i.q3 - i.q1) THEN d.qty END), 0) AS normalized_total,
           COUNT(CASE WHEN d.qty > i.q3 + 1.5 * (i.q3 - i.q1) THEN 1 END) AS outlier_days
    FROM iqr i
    JOIN daily d ON d.sku_id = i.sku_id
    GROUP BY i.sku_id, i.raw_total, i.median_daily, i.mean_daily, i.total_days, i.q1, i.q3
    """
        )
        async with self.session() as session:
            result = await session.execute(query, params)
            out: dict[str, dict] = {}
            for row in result.mappings():
                r = dict(row)
                total_days = r["total_days"] or 1
                outlier_days = int(r["outlier_days"] or 0)
                clean_days = total_days - outlier_days
                out[str(r["sku_id"])] = {
                    "raw_total": float(r["raw_total"]),
                    "normalized_total": float(r["normalized_total"]),
                    "median_daily": round(float(r["median_daily"]), 2),
                    "mean_daily": round(float(r["mean_daily"]), 2),
                    "normalized_daily": round(float(r["normalized_total"]) / max(clean_days, 1), 2),
                    "outlier_days": outlier_days,
                    "total_days": int(total_days),
                }
            return out

    async def seasonal_pattern(self, org_id: str, sku_id: str, months: int = 12) -> list[dict]:
        oid = as_uuid_required(org_id)
        sid = as_uuid_required(sku_id)
        q = text(
            """SELECT to_char(DATE(created_at), 'YYYY-MM') AS month,
                  COALESCE(SUM(ABS(quantity_delta)), 0) AS total_qty,
                  COUNT(*) AS transaction_count
           FROM stock_transactions
           WHERE sku_id = :sku_id
             AND transaction_type = 'WITHDRAWAL'
             AND created_at >= (NOW() - make_interval(months => :months))
             AND organization_id = :org_id
           GROUP BY month
           ORDER BY month"""
        )
        async with self.session() as session:
            result = await session.execute(q, {"sku_id": sid, "months": months, "org_id": oid})
            return [dict(r) for r in result.mappings()]

    async def sku_demand_profile(self, org_id: str, sku_id: str, days: int = 60) -> dict:
        oid = as_uuid_required(org_id)
        sid = as_uuid_required(sku_id)
        daily_q = text(
            """SELECT DATE(st.created_at) AS day,
                  COALESCE(SUM(ABS(st.quantity_delta)), 0) AS qty
           FROM stock_transactions st
           WHERE st.sku_id = :sku_id
             AND st.transaction_type = 'WITHDRAWAL'
             AND st.created_at >= (NOW() - make_interval(days => :days))
             AND st.organization_id = :org_id
           GROUP BY DATE(st.created_at)
           ORDER BY day"""
        )
        async with self.session() as session:
            daily_result = await session.execute(
                daily_q, {"sku_id": sid, "days": days, "org_id": oid}
            )
            daily_rows = [dict(r) for r in daily_result.mappings()]

        if not daily_rows:
            return {
                "sku_id": sku_id,
                "period_days": days,
                "total_days_active": 0,
                "raw_total": 0,
                "daily": [],
                "stats": None,
                "project_buys": [],
            }

        quantities = sorted(float(r["qty"]) for r in daily_rows)
        n = len(quantities)
        q1 = quantities[n // 4] if n >= 4 else quantities[0]
        q3 = quantities[(3 * n) // 4] if n >= 4 else quantities[-1]
        iqr = q3 - q1
        upper_fence = q3 + 1.5 * iqr

        daily_out = []
        raw_total = 0.0
        baseline_total = 0.0
        for r in daily_rows:
            qty = float(r["qty"])
            raw_total += qty
            is_outlier = qty > upper_fence and iqr > 0
            if not is_outlier:
                baseline_total += qty
            daily_out.append(
                {
                    "day": str(r["day"]),
                    "qty": qty,
                    "outlier": is_outlier,
                }
            )

        baseline_days = sum(1 for d in daily_out if not d["outlier"])
        median_val = quantities[n // 2]

        job_q = text(
            """SELECT w.job_id, SUM(ABS(st.quantity_delta)) AS job_total
           FROM stock_transactions st
           LEFT JOIN withdrawals w
             ON st.reference_id = w.id::text AND st.reference_type = 'withdrawal'
           WHERE st.sku_id = :sku_id
             AND st.transaction_type = 'WITHDRAWAL'
             AND st.created_at >= (NOW() - make_interval(days => :days))
             AND st.organization_id = :org_id
             AND w.job_id IS NOT NULL
           GROUP BY w.job_id
           ORDER BY job_total DESC
           LIMIT 10"""
        )
        async with self.session() as session:
            job_result = await session.execute(job_q, {"sku_id": sid, "days": days, "org_id": oid})
            job_rows = job_result.mappings().all()

        project_buys = []
        for jr in job_rows:
            jd = dict(jr)
            pct = float(jd["job_total"]) / raw_total * 100 if raw_total > 0 else 0
            if pct >= 40:
                project_buys.append(
                    {
                        "job_id": str(jd["job_id"]),
                        "total": round(float(jd["job_total"]), 2),
                        "pct_of_total": round(pct, 1),
                    }
                )

        return {
            "sku_id": sku_id,
            "period_days": days,
            "total_days_active": n,
            "raw_total": round(raw_total, 2),
            "baseline_total": round(baseline_total, 2),
            "daily": daily_out,
            "stats": {
                "median_daily": round(median_val, 2),
                "mean_daily": round(raw_total / n, 2),
                "baseline_daily": round(baseline_total / max(baseline_days, 1), 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "upper_fence": round(upper_fence, 2),
                "outlier_days": n - baseline_days,
            },
            "project_buys": project_buys,
        }
