"""InsightsAgent: trends, top products, velocity, stockout forecasting.

Tools: get_top_products, get_department_activity, forecast_stockout.
"""
import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.contracts import load_agent_config
from assistant.agents.deps import AgentDeps
from assistant.agents.model_registry import get_model
from assistant.agents.agent_utils import build_model_settings, build_message_history, run_agent_with_reflection
from assistant.agents.tokens import budget_tool_result
from .tools import _get_top_products, _get_department_activity, _forecast_stockout

logger = logging.getLogger(__name__)

_config = load_agent_config("insights")

SYSTEM_PROMPT = """You are a business insights analyst for SKU-Ops, a hardware store management system.

TOOLS — use them when the user asks about trends, analytics, or forecasting:
- get_top_products(days, by, limit): top products by volume (units) or revenue over a period
- get_department_activity(dept_code, days): stock movement summary for a department
- forecast_stockout(limit): products predicted to run out soon based on usage velocity

WHEN TO USE EACH TOOL:
- "top selling / most used / best products / highest revenue" → get_top_products
- "how is [dept] performing / department activity / PLU/ELE/HDW movement" → get_department_activity
- "what's going to run out / stockout forecast / upcoming shortages" → forecast_stockout

Department codes: PLU=plumbing, ELE=electrical, PNT=paint, LUM=lumber,
                  TOL=tools, HDW=hardware, GDN=garden, APP=appliances

FORMAT — respond in GitHub-flavored markdown:
- For rankings and forecasts, use a markdown table with a separator row:

| Rank | Product | Units | Revenue |
|------|---------|-------|---------|
| 1 | PVC Pipe 1/2" | 142 | $284.00 |

- Use **bold** for #1 items, critical-risk stockouts, and key totals
- Lead with a summary sentence ("**Top product earned 3× more than #2**") before the table
- For stockout forecasts, sort by urgency; flag ≤3 days as critical with bold or a note

Never make up analytics data — always use a tool.
Be specific with numbers, trends, and time periods.

REASONING — think before acting:
1. Identify the analytical lens: ranking? trend over time? risk/forecast? department health?
2. For "what's popular" → get_top_products; for "what's at risk" → forecast_stockout; for dept-specific → get_department_activity
3. If the question spans multiple departments or timeframes, call tools in parallel
4. After results, go beyond the raw list: note the gap between #1 and #2, flag critical-risk items, highlight outliers
5. Always state the time period for any trend or ranking — "top products over 30 days" not just "top products"
6. For stockout forecasts, prioritise critical (≤3 days) over high (≤7 days) — tell the user what needs action today"""

_agent = Agent(
    get_model("agent:insights"),
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


@_agent.tool
async def get_top_products(ctx: RunContext[AgentDeps], days: int = 30, by: str = "revenue", limit: int = 10) -> str:
    """Top products ranked by units withdrawn or revenue generated over the last N days. by: 'volume' or 'revenue'."""
    return budget_tool_result(await _get_top_products({"days": days, "by": by, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_department_activity(ctx: RunContext[AgentDeps], dept_code: str, days: int = 30) -> str:
    """Stock movement summary for a department over the last N days (withdrawals, receiving, net change)."""
    return budget_tool_result(await _get_department_activity({"dept_code": dept_code, "days": days}, ctx.deps.org_id), max_tokens=400)


@_agent.tool
async def forecast_stockout(ctx: RunContext[AgentDeps], limit: int = 15) -> str:
    """Products predicted to run out soonest based on recent withdrawal velocity. Returns days-until-zero estimates."""
    return budget_tool_result(await _forecast_stockout({"limit": limit}, ctx.deps.org_id), max_tokens=600)


async def run(user_message: str, history: list[dict] | None, deps: AgentDeps, mode: str = "fast", session_id: str = "") -> dict:
    model_settings = build_model_settings(_config, mode)

    return await run_agent_with_reflection(
        _agent, user_message,
        msg_history=build_message_history(history), deps=deps,
        model_settings=model_settings,
        agent_name="InsightsAgent", agent_label="insights",
        session_id=session_id, mode=mode, history=history,
        config=_config,
    )
