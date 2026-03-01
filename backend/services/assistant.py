"""
Chat AI assistant with tools and ReAct reasoning loops.
Uses Anthropic Claude. Tools: search products, inventory stats, low stock, departments, vendors.
"""
import asyncio
import json
import logging
from typing import Any

from config import ANTHROPIC_AVAILABLE, ANTHROPIC_API_KEY, ANTHROPIC_FAST_MODEL, LLM_SETUP_URL
from db import get_connection

logger = logging.getLogger(__name__)

LLM_NOT_CONFIGURED_MSG = (
    "Chat assistant requires an Anthropic API key. Add ANTHROPIC_API_KEY to backend/.env. "
    f"Get a key at {LLM_SETUP_URL}"
)

MAX_ACT_LOOPS = 8

SYSTEM_PROMPT = """You are an inventory assistant for SKU-Ops, a hardware store management system.

TOOLS — use them whenever the user asks about inventory data:
- search_products(query, limit): find products by name, SKU, or barcode
- get_inventory_stats(): total product count, quantity, cost value, and low-stock count
- list_low_stock(limit): products at or below their reorder point
- list_departments(): all departments with product counts
- list_vendors(): all vendors with product counts

WHEN TO USE EACH TOOL:
- "do we have nails / find X / search for Y" → search_products
- "how many products / what's our inventory value / overall stats" → get_inventory_stats
- "what's low stock / what needs reordering / running low" → list_low_stock
- "list departments / what departments exist" → list_departments
- "list vendors / who are our suppliers" → list_vendors

OUTPUT FORMAT when listing products: SKU | Name | Qty on Hand | Min Stock
Never make up inventory data — always use a tool to retrieve it.
Be concise. If no results match, say so clearly."""

TOOL_DECLARATIONS = [
    {
        "name": "search_products",
        "description": "Search products by name, SKU, or barcode. Returns matching products with sku, name, quantity, min_stock, department_name.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for product name, SKU, or barcode"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_inventory_stats",
        "description": "Get high-level inventory stats: total products, total quantity/value, low stock count.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_low_stock",
        "description": "List products at or below their reorder point (quantity <= min_stock).",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max products to return", "default": 20},
            },
        },
    },
    {
        "name": "list_departments",
        "description": "List all departments with product counts and next SKU.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_vendors",
        "description": "List all vendors with product counts.",
        "parameters": {"type": "object", "properties": {}},
    },
]

# Anthropic tool schema format
TOOL_SCHEMAS = [
    {
        "name": d["name"],
        "description": d.get("description", ""),
        "input_schema": d.get("parameters", {"type": "object", "properties": {}}),
    }
    for d in TOOL_DECLARATIONS
]


def _get_client():
    """Return configured Anthropic client, or None if not available."""
    if not ANTHROPIC_AVAILABLE:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


def _serialize_content(content: Any) -> Any:
    """Convert Anthropic SDK content blocks to JSON-serializable form."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return [
            block.model_dump() if hasattr(block, "model_dump") else block
            for block in content
        ]
    if hasattr(content, "model_dump"):
        return content.model_dump()
    return str(content)


def _serialize_conversation(conversation: list) -> list:
    """Ensure full conversation is JSON-serializable for returning to frontend."""
    return [
        {"role": msg["role"], "content": _serialize_content(msg["content"])}
        for msg in conversation
    ]


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return JSON string result."""
    from repositories import product_repo, department_repo, vendor_repo

    try:
        if name == "search_products":
            query = (args.get("query") or "").strip()
            limit = min(int(args.get("limit") or 20), 50)
            items = await product_repo.list_products(search=query, limit=limit)
            out = [{"sku": p.get("sku"), "name": p.get("name"), "quantity": p.get("quantity"), "min_stock": p.get("min_stock"), "department": p.get("department_name")} for p in items]
            return json.dumps({"count": len(out), "products": out[:limit]})

        if name == "get_inventory_stats":
            conn = get_connection()
            cur = await conn.execute("SELECT COUNT(*) FROM products")
            total_products = (await cur.fetchone())[0]
            cur = await conn.execute("SELECT COALESCE(SUM(quantity), 0), COALESCE(SUM(quantity * cost), 0) FROM products")
            row = await cur.fetchone()
            total_qty = int(row[0]) if row else 0
            total_value = round(float(row[1] or 0), 2)
            cur = await conn.execute("SELECT COUNT(*) FROM products WHERE quantity <= min_stock")
            low_count = (await cur.fetchone())[0]
            return json.dumps({"total_products": total_products, "total_quantity": total_qty, "total_cost_value": total_value, "low_stock_count": low_count})

        if name == "list_low_stock":
            limit = min(int(args.get("limit") or 20), 50)
            items = await product_repo.list_low_stock(limit=limit)
            out = [{"sku": p.get("sku"), "name": p.get("name"), "quantity": p.get("quantity"), "min_stock": p.get("min_stock")} for p in items]
            return json.dumps({"count": len(out), "products": out})

        if name == "list_departments":
            depts = await department_repo.list_all()
            from repositories import sku_repo
            counters = await sku_repo.get_all_counters()
            out = []
            for d in depts:
                code = d.get("code", "")
                next_num = counters.get(code, 0) + 1
                next_sku = f"{code}-ITM-{str(next_num).zfill(6)}"
                out.append({"name": d.get("name"), "code": code, "product_count": d.get("product_count", 0), "next_sku": next_sku})
            return json.dumps({"departments": out})

        if name == "list_vendors":
            vendors = await vendor_repo.list_all()
            out = [{"name": v.get("name"), "product_count": v.get("product_count", 0)} for v in vendors]
            return json.dumps({"vendors": out})

        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.warning(f"Tool {name} error: {e}")
        return json.dumps({"error": str(e)})


async def chat(messages: list[dict], user_message: str, history: list[dict] | None = None) -> dict:
    """
    ReAct loop: send to Claude with tools, execute any tool_use blocks, feed results back, repeat.
    Returns { "response": "...", "tool_calls": [...], "history": [...] }.
    history: full Anthropic-format message list from prior response (preserves tool call/result turns).
    """
    if not ANTHROPIC_AVAILABLE:
        return {"response": LLM_NOT_CONFIGURED_MSG, "tool_calls": [], "history": []}

    client = _get_client()
    if not client:
        return {"response": "Could not initialize AI client.", "tool_calls": [], "history": []}

    # Use full history from previous turn when available (fixes multi-turn tool context).
    # Fall back to text-only reconstruction for the first turn.
    if history:
        conversation = list(history)
    else:
        conversation = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "assistant"
            text = (m.get("content") or "").strip()
            if text:
                conversation.append({"role": role, "content": text})

    conversation.append({"role": "user", "content": user_message})

    tool_calls_made = []

    for _ in range(MAX_ACT_LOOPS):
        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model=ANTHROPIC_FAST_MODEL,
                system=SYSTEM_PROMPT,
                messages=conversation,
                tools=TOOL_SCHEMAS,
                max_tokens=4096,
            )
        except Exception as e:
            logger.warning(f"Assistant generate: {e}")
            return {"response": f"AI error: {e}", "tool_calls": tool_calls_made, "history": _serialize_conversation(conversation)}

        if response.stop_reason == "tool_use":
            # Append assistant turn (with tool_use blocks) to history
            conversation.append({
                "role": "assistant",
                "content": [b.model_dump() for b in response.content],
            })

            # Execute all tool calls in parallel
            tool_results = []
            tool_tasks = []
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            for block in tool_use_blocks:
                args = dict(block.input) if block.input else {}
                tool_tasks.append((block.id, block.name, args, execute_tool(block.name, args)))

            for tool_use_id, name, args, coro in tool_tasks:
                result = await coro
                tool_calls_made.append({"tool": name, "args": args})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result,
                })

            conversation.append({"role": "user", "content": tool_results})
            continue

        # end_turn — extract text
        text = next(
            (b.text for b in response.content if hasattr(b, "text") and b.text),
            "I couldn't generate a response.",
        )
        conversation.append({"role": "assistant", "content": text})
        return {
            "response": text,
            "tool_calls": tool_calls_made,
            "history": _serialize_conversation(conversation),
        }

    return {
        "response": "Reached maximum reasoning steps. Try a simpler question.",
        "tool_calls": tool_calls_made,
        "history": _serialize_conversation(conversation),
    }
