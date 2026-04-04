"""Financial dashboard and export routes.

Summary reads from the financial_ledger (immutable event log).
Export still reads individual withdrawals for line-level CSV output.
"""

import asyncio
import csv
import io
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.types import round_money

logger = logging.getLogger(__name__)


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations


router = APIRouter(prefix="/financials", tags=["financials"])


@router.get("/summary")
async def get_financial_summary(
    current_user: AdminDep,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """P&L summary sourced from the financial ledger."""
    try:
        org_id = get_org_id()
        fin = _db_finance()
        date_kw = {"start_date": start_date, "end_date": end_date}
        (
            accounts,
            by_department,
            by_entity_rows,
            by_contractor_rows,
            counts,
        ) = await asyncio.gather(
            fin.ledger_summary_by_account(org_id, **date_kw),
            fin.ledger_summary_by_department(org_id, **date_kw),
            fin.ledger_summary_by_billing_entity(org_id, **date_kw),
            fin.ledger_summary_by_contractor(org_id, **date_kw),
            fin.analytics_reference_counts(org_id, **date_kw),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in get_financial_summary")
        raise

    revenue = accounts.get("revenue", 0)
    cogs = accounts.get("cogs", 0)
    tax = accounts.get("tax_collected", 0)
    shrinkage = accounts.get("shrinkage", 0)

    gross_profit = round_money(revenue - cogs)
    # float for JSON-friendly percentage
    margin_pct = round(float(gross_profit / revenue * 100), 1) if revenue > 0 else 0.0

    by_entity = {}
    for row in by_entity_rows:
        name = row["billing_entity"] or "Unknown"
        by_entity[name] = {
            "total": row["revenue"],
            "ar_balance": row.get("ar_balance", 0),
            "count": row.get("transaction_count", 0),
        }

    dept_dict = {}
    for row in by_department:
        dept_dict[row["department"]] = {
            "revenue": row["revenue"],
            "cost": row["cost"],
            "shrinkage": row.get("shrinkage", 0),
            "profit": row["profit"],
            "margin_pct": row["margin_pct"],
        }

    return {
        "gross_revenue": round_money(revenue),
        "net_revenue": round_money(revenue),
        "total_cost": round_money(cogs),
        "gross_profit": gross_profit,
        "gross_margin_pct": margin_pct,
        "tax_collected": round_money(tax),
        "shrinkage": round_money(shrinkage),
        "transaction_count": counts.get("withdrawal", 0),
        "return_count": counts.get("return", 0),
        "by_billing_entity": by_entity,
        "by_contractor": by_contractor_rows,
        "by_department": dept_dict,
        "total_revenue": round_money(revenue),
        "gross_margin": gross_profit,
    }


@router.get("/export")
async def export_financials(
    current_user: AdminDep,
    _format: str = "csv",
    payment_status: str | None = None,
    billing_entity: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Export financial data as CSV (line-level, from operational tables)."""
    try:
        ops = _db_operations()
        withdrawals = await ops.list_withdrawals(
            current_user.organization_id,
            payment_status=payment_status,
            billing_entity=billing_entity,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in export_financials")
        raise

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Transaction ID",
            "Date",
            "Contractor",
            "Company",
            "Billing Entity",
            "Job ID",
            "Service Address",
            "Subtotal",
            "Tax",
            "Total",
            "Cost",
            "Margin",
            "Payment Status",
            "Items",
        ]
    )

    for w in withdrawals:
        items_str = "; ".join([f"{i['name']} x{i['quantity']}" for i in w.get("items", [])])
        writer.writerow(
            [
                w.get("id", ""),
                w.get("created_at", "")[:10],
                w.get("contractor_name", ""),
                w.get("contractor_company", ""),
                w.get("billing_entity", ""),
                w.get("job_id", ""),
                w.get("service_address", ""),
                w.get("subtotal", 0),
                w.get("tax", 0),
                w.get("total", 0),
                w.get("cost_total", 0),
                round_money(w.get("total", 0) - w.get("cost_total", 0)),
                w.get("payment_status", ""),
                items_str,
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=financials_{datetime.now(UTC).strftime('%Y%m%d')}.csv"},
    )
