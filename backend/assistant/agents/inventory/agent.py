"""InventoryAgent: product search, stock levels, reorders, departments, vendors."""
import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.core.config import load_agent_config
from assistant.agents.core.runner import build_model_settings, run_specialist
from assistant.agents.core.messages import build_message_history
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.model_registry import get_model
from assistant.agents.core.tokens import budget_tool_result
from .tools import (
    _search_products, _search_semantic, _get_product_details,
    _get_inventory_stats, _list_low_stock, _list_departments,
    _list_vendors, _get_usage_velocity, _get_reorder_suggestions,
    _get_department_health, _get_slow_movers,
    _get_top_products, _get_department_activity, _forecast_stockout,
)

logger = logging.getLogger(__name__)

_config = load_agent_config("inventory")

SYSTEM_PROMPT = """You are an inventory specialist for SKU-Ops, a hardware store management system.

TOOLS:
- search_products(query, limit): find products by name, SKU, or barcode
- search_semantic(query, limit): concept search — use when search_products finds nothing or query is descriptive ("something for fixing pipes")
- get_product_details(sku): full details for one product
- get_inventory_stats(): catalogue summary — SKU count, cost value, low/out-of-stock counts
- list_low_stock(limit): products at or below their reorder point
- list_departments(): all departments with product counts
- list_vendors(): all vendors with product counts
- get_usage_velocity(sku, days): how fast a product moves
- get_reorder_suggestions(limit): priority reorder list by urgency
- get_department_health(): per-department breakdown of healthy/low/out-of-stock product counts
- get_slow_movers(limit, days): products with stock on hand but very low withdrawal activity (dead or slow stock)
- get_top_products(days, by, limit): top products by volume (units) or revenue over a period
- get_department_activity(dept_code, days): stock movement summary for a department
- forecast_stockout(limit): products predicted to run out soon based on usage velocity

WHEN TO USE EACH TOOL:
- "do we have X / find X / search for Y" → search_products first, search_semantic if no results
- "details on [product] / tell me about SKU X" → get_product_details
- "overall stats / how many products / catalogue size" → get_inventory_stats
- "low stock / needs reordering / running low" → list_low_stock
- "list departments / what departments" → list_departments
- "list vendors / suppliers" → list_vendors
- "how fast does X move / usage rate" → get_usage_velocity
- "what should we reorder / reorder priority" → get_reorder_suggestions
- "department health / stock health by department" → get_department_health
- "slow movers / dead stock / not moving / sitting on shelf" → get_slow_movers
- "top selling / most used / best products / highest revenue" → get_top_products
- "how is [dept] performing / department activity / PLU/ELE/HDW movement" → get_department_activity
- "what's going to run out / stockout forecast / upcoming shortages" → forecast_stockout

Department codes: PLU=plumbing, ELE=electrical, PNT=paint, LUM=lumber,
                  TOL=tools, HDW=hardware, GDN=garden, APP=appliances

DEEP INVENTORY ANALYSIS — when asked for a full analysis, call in parallel:
  get_inventory_stats() + get_department_health() + get_slow_movers() + get_reorder_suggestions()
  Then write a structured report with sections: Overview, Department Health, Slow Movers, Reorder Priority.

TERMINOLOGY — be precise, hardware products have different units:
- "total_skus" = number of distinct product lines in the catalogue (not a physical count)
- "quantity" = stock on hand in that product's sell_uom (e.g. 5 gallons, 3 boxes, 12 each)
- NEVER say "X units" or "X items" — always include the specific UOM from sell_uom
- NEVER report total_quantity_sum as meaningful — it adds gallons + boxes + each, which is nonsense
- "low stock" means on-hand quantity is at or below the reorder point for that product

FORMAT — respond in GitHub-flavored markdown:
- For product lists, use a markdown table with a separator row:

| SKU | Name | On Hand | UOM | Reorder At |
|-----|------|---------|-----|------------|
| PLU-001 | Copper Pipe 3/4" | 8 | each | 10 |

- Use **bold** for critical numbers (zero stock, amounts) and key names
- Use bullet lists (- item) for multi-item summaries without tabular structure
- Keep prose responses to 1–3 sentences unless the question needs more

RESPONSE RULES:
- Stats: say "47 distinct products" or "47 SKUs" — not "47 products worth of units"
- Stock: say "8 each on hand" or "3 gallons on hand" — not "8 units"
- Low stock: "Copper Pipe: 8 each on hand, reorder at 10"
- If a product is out of stock (quantity=0), say "out of stock"
- Never make up data — always use a tool
- Be concise. If no results, say so clearly.

REASONING — think before acting:
1. Identify exactly what data the question needs before calling any tool
2. Call independent tools in the same turn when they don't depend on each other
   (e.g. get_inventory_stats + list_low_stock can run together)
3. After each tool result, ask: "Is this sufficient to answer accurately?" — if not, call more
4. Chain tools for multi-part questions: "What's low AND moving fast?" → list_low_stock, then
   get_usage_velocity for the critical items
5. If search_products finds nothing, always try search_semantic before concluding unavailable
6. Never stop early with partial data when a follow-up tool call would give a complete answer"""

_agent = Agent(
    get_model("agent:inventory"),
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


@_agent.tool
async def search_products(ctx: RunContext[AgentDeps], query: str, limit: int = 20) -> str:
    """Search products by name, SKU, or barcode. Returns matching products with SKU, name, quantity, min_stock, department."""
    return budget_tool_result(await _search_products({"query": query, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def search_semantic(ctx: RunContext[AgentDeps], query: str, limit: int = 10) -> str:
    """Semantic/concept search for products. Use when exact search fails or query is descriptive (e.g. 'something for fixing pipes', 'waterproof coating')."""
    return budget_tool_result(await _search_semantic({"query": query, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_product_details(ctx: RunContext[AgentDeps], sku: str) -> str:
    """Get full details for one product by SKU: price, cost, vendor, UOM, barcode, reorder point."""
    return budget_tool_result(await _get_product_details({"sku": sku}, ctx.deps.org_id), max_tokens=400)


@_agent.tool
async def get_inventory_stats(ctx: RunContext[AgentDeps]) -> str:
    """Catalogue summary: total_skus (distinct product lines), total_cost_value, low_stock_count, out_of_stock_count. Does NOT return a meaningful total unit count — products have different units."""
    return budget_tool_result(await _get_inventory_stats(ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def list_low_stock(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """List products at or below their reorder point (quantity <= min_stock)."""
    return budget_tool_result(await _list_low_stock({"limit": limit}, ctx.deps.org_id))


@_agent.tool
async def list_departments(ctx: RunContext[AgentDeps]) -> str:
    """List all departments with product counts and next SKU."""
    return budget_tool_result(await _list_departments(ctx.deps.org_id))


@_agent.tool
async def list_vendors(ctx: RunContext[AgentDeps]) -> str:
    """List all vendors with product counts."""
    return budget_tool_result(await _list_vendors(ctx.deps.org_id))


@_agent.tool
async def get_usage_velocity(ctx: RunContext[AgentDeps], sku: str, days: int = 30) -> str:
    """How fast a product moves: total and average daily withdrawals over the last N days."""
    return budget_tool_result(await _get_usage_velocity({"sku": sku, "days": days}, ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def get_reorder_suggestions(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Priority reorder list: low-stock products ranked by urgency (days until stockout based on usage velocity)."""
    return budget_tool_result(await _get_reorder_suggestions({"limit": limit}, ctx.deps.org_id), max_tokens=600)


@_agent.tool
async def get_department_health(ctx: RunContext[AgentDeps]) -> str:
    """Per-department breakdown showing healthy, low-stock, and out-of-stock product counts."""
    return budget_tool_result(await _get_department_health(ctx.deps.org_id))


@_agent.tool
async def get_slow_movers(ctx: RunContext[AgentDeps], limit: int = 20, days: int = 30) -> str:
    """Products with stock on hand but very low or zero withdrawal activity — dead or slow-moving stock tying up inventory."""
    return budget_tool_result(await _get_slow_movers({"limit": limit, "days": days}, ctx.deps.org_id))


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

    return await run_specialist(
        _agent, user_message,
        msg_history=build_message_history(history), deps=deps,
        model_settings=model_settings,
        agent_name="InventoryAgent", agent_label="inventory",
        session_id=session_id, mode=mode, history=history,
        config=_config,
    )
