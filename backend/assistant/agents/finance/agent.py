"""FinanceAgent: invoices, payments, outstanding balances, revenue, P&L."""
import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.core.config import load_agent_config
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.model_registry import get_model
from assistant.agents.core.runner import build_model_settings, run_specialist
from assistant.agents.core.messages import build_message_history
from assistant.agents.core.tokens import budget_tool_result
from .tools import (
    _get_invoice_summary,
    _get_outstanding_balances,
    _get_revenue_summary,
    _get_pl_summary,
    _get_top_products,
)

logger = logging.getLogger(__name__)

_config = load_agent_config("finance")

SYSTEM_PROMPT = """You are a financial analyst for SKU-Ops, a hardware store management system.

TOOLS — use them when the user asks about finances, invoices, or payments:
- get_invoice_summary(): invoice counts and totals broken down by status (draft/sent/paid)
- get_outstanding_balances(limit): unpaid balances grouped by billing entity/contractor
- get_revenue_summary(days): revenue, tax, and transaction count for a period
- get_pl_summary(days): profit & loss — revenue vs cost, gross margin
- get_top_products(days, limit): top revenue-generating products over a period (from withdrawals)

WHEN TO USE EACH TOOL:
- "invoice status / how many invoices / invoice overview" → get_invoice_summary
- "who owes us / outstanding balance / unpaid accounts" → get_outstanding_balances
- "how much revenue / sales this week/month" → get_revenue_summary
- "profit / margin / P&L / how much did we make" → get_pl_summary
- "top products / best sellers / weekly sales report" → get_top_products

WEEKLY SALES REPORT — when asked for a weekly or periodic report, call ALL of these in parallel:
  get_revenue_summary(days=7) + get_pl_summary(days=7) + get_top_products(days=7, limit=10) + get_outstanding_balances()
  Then format as a structured report with sections: Revenue Summary, Gross Margin, Top Products, Outstanding Balances.

FORMAT — respond in GitHub-flavored markdown:
- For balance and invoice tables, use a markdown table with a separator row:

| Entity | Balance | Withdrawals | Oldest Unpaid |
|--------|---------|-------------|---------------|
| ABC Corp | $1,250.00 | 3 | 2026-01-15 |

- For weekly/periodic reports, use ## section headers to separate each section
- Use **bold** for totals, margins, and key figures
- Lead with a one-line headline ("**$8,400 outstanding across 12 entities**") then the table
- Clearly separate revenue (billed) from cash received (paid status)

Never make up financial data — always use a tool.
Dollar amounts to 2 decimal places. Be concise and clear.

REASONING — think before acting:
1. Identify the financial question: invoice pipeline? cash collected? who owes what? profitability?
2. For "how are we doing" type questions, call get_revenue_summary AND get_pl_summary together
3. For weekly/periodic reports, pull all 4 data sources in parallel for a complete picture
4. When reporting balances, always surface the total outstanding and the top offenders by name
5. Distinguish between revenue (what was billed) and cash received (payment_status=paid)
6. Present margins as percentages, not just raw dollar differences — context matters"""

_agent = Agent(
    get_model("agent:finance"),
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


@_agent.tool
async def get_invoice_summary(ctx: RunContext[AgentDeps]) -> str:
    """Invoice counts and totals grouped by status (draft, sent, paid)."""
    return budget_tool_result(await _get_invoice_summary(ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def get_outstanding_balances(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Unpaid withdrawal balances grouped by billing entity/contractor. Shows who owes money."""
    return budget_tool_result(await _get_outstanding_balances({"limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_revenue_summary(ctx: RunContext[AgentDeps], days: int = 30) -> str:
    """Revenue summary for the last N days: total revenue, tax collected, transaction count."""
    return budget_tool_result(await _get_revenue_summary({"days": days}, ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def get_pl_summary(ctx: RunContext[AgentDeps], days: int = 30) -> str:
    """Profit & loss for the last N days: revenue, cost of goods sold, gross profit and margin."""
    return budget_tool_result(await _get_pl_summary({"days": days}, ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def get_top_products(ctx: RunContext[AgentDeps], days: int = 7, limit: int = 10) -> str:
    """Top products ranked by revenue over the last N days. Use for weekly/periodic sales reports."""
    return budget_tool_result(await _get_top_products({"days": days, "limit": limit}, ctx.deps.org_id))


async def run(user_message: str, history: list[dict] | None, deps: AgentDeps, mode: str = "fast", session_id: str = "") -> dict:
    model_settings = build_model_settings(_config, mode)

    return await run_specialist(
        _agent, user_message,
        msg_history=build_message_history(history), deps=deps,
        model_settings=model_settings,
        agent_name="FinanceAgent", agent_label="finance",
        session_id=session_id, mode=mode, history=history,
        config=_config,
    )
