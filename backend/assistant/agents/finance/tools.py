"""Finance helper functions — DB query implementations for the finance agent."""

import json
import logging
from datetime import UTC, datetime, timedelta

from assistant.agents.tools.registry import register as _reg
from assistant.agents.tools.serialization import dumps as _dumps
from finance.application.invoice_service import list_invoices
from operations.application.queries import list_withdrawals
from shared.infrastructure.db import get_org_id

logger = logging.getLogger(__name__)


async def _get_invoice_summary() -> str:
    """Invoice counts and totals by status (draft/sent/paid)."""
    invoices = await list_invoices(limit=10000, organization_id=get_org_id())
    summary: dict[str, dict] = {}
    for inv in invoices:
        status = inv.status or "unknown"
        if status not in summary:
            summary[status] = {"count": 0, "total": 0.0}
        summary[status]["count"] += 1
        summary[status]["total"] += inv.total
    for s in summary.values():
        s["total"] = round(s["total"], 2)
    grand_total = round(sum(inv.total for inv in invoices), 2)
    return json.dumps(
        {"total_invoices": len(invoices), "grand_total": grand_total, "by_status": summary}
    )


async def _get_outstanding_balances(limit: int = 20) -> str:
    """Unpaid balances by billing entity."""
    limit = min(limit, 100)
    withdrawals = await list_withdrawals(payment_status="unpaid", limit=10000)
    entity_map: dict[str, dict] = {}
    for w in withdrawals:
        entity = w.billing_entity or w.contractor_name or "Unknown"
        created = w.created_at or ""
        if entity not in entity_map:
            entity_map[entity] = {
                "balance": 0.0,
                "withdrawal_count": 0,
                "oldest": created,
            }
        else:
            if created and (
                not entity_map[entity]["oldest"] or created < entity_map[entity]["oldest"]
            ):
                entity_map[entity]["oldest"] = created
        entity_map[entity]["balance"] += w.total
        entity_map[entity]["withdrawal_count"] += 1
    sorted_entities = sorted(entity_map.items(), key=lambda x: x[1]["balance"], reverse=True)
    out = [
        {
            "entity": entity,
            "balance": round(data["balance"], 2),
            "withdrawal_count": data["withdrawal_count"],
            "oldest_unpaid": data["oldest"][:10],
        }
        for entity, data in sorted_entities[:limit]
    ]
    total_outstanding = sum(w.total for w in withdrawals)
    return json.dumps(
        {
            "total_outstanding": round(total_outstanding, 2),
            "entity_count": len(entity_map),
            "balances": out,
        }
    )


async def _get_revenue_summary(days: int = 30) -> str:
    """Revenue breakdown by payment status over a period."""
    days = min(days, 365)
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    withdrawals = await list_withdrawals(start_date=since, limit=10000)
    total_revenue = sum(w.total for w in withdrawals)
    total_tax = sum(w.tax for w in withdrawals)
    paid = sum(w.total for w in withdrawals if w.payment_status == "paid")
    unpaid = sum(w.total for w in withdrawals if w.payment_status == "unpaid")
    invoiced = sum(w.total for w in withdrawals if w.payment_status == "invoiced")
    return json.dumps(
        {
            "period_days": days,
            "transaction_count": len(withdrawals),
            "total_revenue": round(total_revenue, 2),
            "total_tax": round(total_tax, 2),
            "revenue_ex_tax": round(total_revenue - total_tax, 2),
            "paid": round(paid, 2),
            "unpaid": round(unpaid, 2),
            "invoiced": round(invoiced, 2),
        }
    )


async def _get_pl_summary(days: int = 30) -> str:
    """Profit & loss: revenue, COGS, gross profit and margin."""
    days = min(days, 365)
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    withdrawals = await list_withdrawals(start_date=since, limit=10000)
    total_revenue = sum(w.total for w in withdrawals)
    total_cost = sum(w.cost_total for w in withdrawals)
    gross_profit = total_revenue - total_cost
    margin_pct = round((gross_profit / total_revenue * 100), 1) if total_revenue > 0 else 0
    return _dumps(
        {
            "period_days": days,
            "transaction_count": len(withdrawals),
            "revenue": round(total_revenue, 2),
            "cost_of_goods": round(total_cost, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": margin_pct,
        }
    )


# ── Registry ──────────────────────────────────────────────────────────────────

_reg(
    "get_invoice_summary", "finance", _get_invoice_summary, use_cases=["invoices", "invoice status"]
)
_reg(
    "get_outstanding_balances",
    "finance",
    _get_outstanding_balances,
    use_cases=["outstanding", "unpaid balances"],
)
_reg("get_revenue_summary", "finance", _get_revenue_summary, use_cases=["revenue", "sales summary"])
_reg("get_pl_summary", "finance", _get_pl_summary, use_cases=["P&L", "profit loss", "margin"])
