"""Ops agent helper functions — facade-backed queries for operations data."""

import logging
from datetime import UTC, datetime, timedelta

from assistant.agents.tools.models import (
    ContractorHistoryResult,
    DailyActivityResult,
    ErrorResult,
    JobMaterialItem,
    JobMaterialsResult,
    PaymentStatusResult,
    PendingRequest,
    PendingRequestsResult,
    RecentWithdrawalsResult,
    WithdrawalDetail,
    WithdrawalSummary,
)
from assistant.agents.tools.registry import register as _reg
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


async def _get_contractor_history(name: str = "", limit: int = 20) -> str:
    """Withdrawal history for a contractor (by name)."""
    name = name.strip()
    limit = min(limit, 100)
    all_withdrawals = await get_database_manager().operations.list_withdrawals(
        get_org_id(), limit=500
    )
    name_lower = name.lower()
    matched = [
        w
        for w in all_withdrawals
        if name_lower in (w.contractor_name or "").lower()
        or name_lower in (w.contractor_company or "").lower()
    ]
    details = [
        WithdrawalDetail(
            date=w.created_at.strftime("%Y-%m-%d")
            if isinstance(w.created_at, datetime)
            else (w.created_at or "")[:10],
            job_id=w.job_id,
            service_address=w.service_address,
            contractor=w.contractor_name,
            company=w.contractor_company,
            total=round(float(w.total), 2),
            cost_total=round(float(w.cost_total), 2),
            payment_status=w.payment_status,
            item_count=len(w.items),
        )
        for w in matched[:limit]
    ]
    total_spent = sum(float(w.total) for w in matched)
    unpaid = sum(float(w.total) for w in matched if w.payment_status == "unpaid")
    return ContractorHistoryResult(
        contractor_search=name,
        count=len(details),
        total_spent=round(total_spent, 2),
        unpaid_balance=round(unpaid, 2),
        withdrawals=details,
    ).serialize()


async def _get_job_materials(job_id: str = "") -> str:
    """All materials pulled for a specific job ID."""
    job_id = job_id.strip()
    all_withdrawals = await get_database_manager().operations.list_withdrawals(
        get_org_id(), limit=1000
    )
    job_withdrawals = [w for w in all_withdrawals if (w.job_id or "").lower() == job_id.lower()]
    if not job_withdrawals:
        job_withdrawals = [w for w in all_withdrawals if job_id.lower() in (w.job_id or "").lower()]
    if not job_withdrawals:
        return ErrorResult(error=f"No withdrawals found for job '{job_id}'").serialize()
    item_map: dict[str, JobMaterialItem] = {}
    for w in job_withdrawals:
        for item in w.items:
            sku = item.sku
            if sku in item_map:
                prev = item_map[sku]
                item_map[sku] = JobMaterialItem(
                    sku=prev.sku,
                    name=prev.name,
                    quantity=prev.quantity + float(item.quantity),
                    unit=prev.unit,
                    price=prev.price,
                    subtotal=round(prev.subtotal + float(item.subtotal), 2),
                )
            else:
                item_map[sku] = JobMaterialItem(
                    sku=sku,
                    name=item.name,
                    quantity=float(item.quantity),
                    unit=item.unit,
                    price=float(item.unit_price),
                    subtotal=round(float(item.subtotal), 2),
                )
    items_out = list(item_map.values())
    total = sum(float(w.total) for w in job_withdrawals)
    return JobMaterialsResult(
        job_id=job_id,
        service_address=job_withdrawals[0].service_address,
        contractor=job_withdrawals[0].contractor_name,
        withdrawal_count=len(job_withdrawals),
        total=round(total, 2),
        items=items_out,
    ).serialize()


async def _list_recent_withdrawals(days: int = 7, limit: int = 20) -> str:
    """Recent material withdrawals across all jobs."""
    days = min(days, 365)
    limit = min(limit, 100)
    since = datetime.now(UTC) - timedelta(days=days)
    withdrawals = await get_database_manager().operations.list_withdrawals(
        get_org_id(), start_date=since, limit=limit
    )
    summaries = [
        WithdrawalSummary(
            date=w.created_at.strftime("%Y-%m-%d")
            if isinstance(w.created_at, datetime)
            else (w.created_at or "")[:10],
            job_id=w.job_id,
            contractor=w.contractor_name,
            service_address=w.service_address,
            total=round(float(w.total), 2),
            payment_status=w.payment_status,
            item_count=len(w.items),
        )
        for w in withdrawals
    ]
    total_value = sum(float(w.total) for w in withdrawals)
    return RecentWithdrawalsResult(
        period_days=days,
        count=len(summaries),
        total_value=round(total_value, 2),
        withdrawals=summaries,
    ).serialize()


async def _list_pending_material_requests(limit: int = 20) -> str:
    """Material requests from contractors awaiting approval."""
    limit = min(limit, 100)
    rows = await get_database_manager().operations.list_pending_material_requests(
        get_org_id(), limit=limit
    )
    requests = [
        PendingRequest(
            id=r.id,
            contractor=r.contractor_name,
            job_id=r.job_id,
            service_address=r.service_address,
            notes=r.notes,
            item_count=len(r.items),
            requested_at=(r.created_at or "")[:16],
        )
        for r in rows
    ]
    return PendingRequestsResult(count=len(requests), pending_requests=requests).serialize()


async def _get_daily_withdrawal_activity(days: int = 30, sku_id: str = "") -> str:
    """Daily withdrawal volume over the last N days."""
    days = min(days, 365)
    since = datetime.now(UTC) - timedelta(days=days)
    sku_id_val = sku_id.strip() or None
    activity = await get_database_manager().inventory.daily_withdrawal_activity(
        get_org_id(), since, sku_id=sku_id_val
    )
    return DailyActivityResult(
        period_days=days,
        data_points=len(activity),
        activity=activity,
    ).serialize()


async def _get_payment_status_breakdown(days: int = 30) -> str:
    """Withdrawal totals by payment status (paid/invoiced/unpaid)."""
    days = min(days, 365)
    since = datetime.now(UTC) - timedelta(days=days)
    end = datetime.now(UTC)
    breakdown = await get_database_manager().operations.payment_status_breakdown(
        get_org_id(), start_date=since, end_date=end
    )
    total = round(sum(float(v) for v in breakdown.values()), 2)
    return PaymentStatusResult(
        period_days=days,
        total=total,
        by_status={k: round(float(v), 2) for k, v in breakdown.items()},
    ).serialize()


# ── Registry ──────────────────────────────────────────────────────────────────

_reg(
    "get_contractor_history",
    "ops",
    _get_contractor_history,
    use_cases=["contractor", "withdrawal history"],
)
_reg(
    "get_job_materials",
    "ops",
    _get_job_materials,
    use_cases=["job materials", "job details"],
)
_reg(
    "list_recent_withdrawals",
    "ops",
    _list_recent_withdrawals,
    use_cases=["withdrawals", "recent activity"],
)
_reg(
    "list_pending_material_requests",
    "ops",
    _list_pending_material_requests,
    use_cases=["pending requests", "material requests"],
)
_reg(
    "get_daily_withdrawal_activity",
    "ops",
    _get_daily_withdrawal_activity,
    use_cases=["daily activity", "withdrawal chart"],
)
_reg(
    "get_payment_status_breakdown",
    "ops",
    _get_payment_status_breakdown,
    use_cases=["payment status", "paid unpaid"],
)
