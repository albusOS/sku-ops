"""
Chat AI assistant with tools and ReAct reasoning loops.
Uses Gemini 1.5 Flash (free tier). Tools: search products, inventory stats, low stock, departments, vendors.
"""
import asyncio
import json
import logging

from config import GEMINI_AVAILABLE, GEMINI_MODEL, LLM_API_KEY, LLM_SETUP_URL
from db import get_connection

logger = logging.getLogger(__name__)

# Chat assistant requires Gemini (uses its function-calling API directly).
# Document parsing, enrichment, and UOM classification support Ollama too via llm.py.
LLM_NOT_CONFIGURED_MSG = (
    "Chat assistant requires a Gemini API key. Add LLM_API_KEY to backend/.env. "
    f"Get a free key at {LLM_SETUP_URL}"
)

MAX_ACT_LOOPS = 8  # Prevent runaway tool loops

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


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return JSON string result."""
    from repositories import product_repo, department_repo, vendor_repo

    try:
        if name == "search_products":
            query = (args.get("query") or "").strip()
            limit = int(args.get("limit") or 20)
            limit = min(limit, 50)
            items = await product_repo.list_products(search=query, limit=limit)
            # Simplify for LLM
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
            return json.dumps({
                "total_products": total_products,
                "total_quantity": total_qty,
                "total_cost_value": total_value,
                "low_stock_count": low_count,
            })

        if name == "list_low_stock":
            limit = int(args.get("limit") or 20)
            limit = min(limit, 50)
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


def _build_tools():
    """Build Gemini Tool from declarations."""
    from google.generativeai.types import Tool, FunctionDeclaration

    decls = [
        FunctionDeclaration(
            name=d["name"],
            description=d.get("description", ""),
            parameters=d.get("parameters", {}),
        )
        for d in TOOL_DECLARATIONS
    ]
    return [Tool(function_declarations=decls)]


def _serialize_history(history) -> list[dict]:
    """Serialize Gemini chat history to JSON-safe dicts (preserves tool call/response turns)."""
    result = []
    for content in history:
        parts = []
        for part in content.parts:
            if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                parts.append({
                    "function_call": {
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args) if part.function_call.args else {},
                    }
                })
            elif hasattr(part, "function_response") and part.function_response and part.function_response.name:
                parts.append({
                    "function_response": {
                        "name": part.function_response.name,
                        "response": dict(part.function_response.response) if part.function_response.response else {},
                    }
                })
            elif hasattr(part, "text") and part.text:
                parts.append({"text": part.text})
        if parts:
            result.append({"role": content.role, "parts": parts})
    return result


async def chat(messages: list[dict], user_message: str, history: list[dict] | None = None) -> dict:
    """
    ReAct loop: send to Gemini with tools, execute any function_call, feed result back, repeat.
    Returns { "response": "...", "tool_calls": [...], "history": [...] }.
    history: full Gemini history from prior response (preserves tool call/response turns).
    """
    if not GEMINI_AVAILABLE:
        return {"response": LLM_NOT_CONFIGURED_MSG, "tool_calls": [], "history": []}

    try:
        import google.generativeai as genai
        genai.configure(api_key=LLM_API_KEY)
        tools = _build_tools()
        model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_PROMPT, tools=tools)
    except Exception as e:
        logger.warning(f"Assistant init: {e}")
        return {"response": f"Could not initialize AI: {e}", "tool_calls": [], "history": []}

    # Prefer the full serialized history (includes tool turns) over text-only reconstruction.
    # Fall back to text reconstruction when history is not yet available (first turn).
    if history:
        prior_history = history
    else:
        prior_history = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            text = (m.get("content") or "").strip()
            if text:
                prior_history.append({"role": role, "parts": [{"text": text}]})

    tool_calls_made = []

    chat = model.start_chat(history=prior_history, enable_automatic_function_calling=False)
    to_send = user_message

    for _ in range(MAX_ACT_LOOPS):
        try:
            response = await asyncio.to_thread(chat.send_message, to_send)
        except Exception as e:
            logger.warning(f"Assistant generate: {e}")
            return {"response": f"AI error: {e}", "tool_calls": tool_calls_made, "history": _serialize_history(chat.history)}

        if not response or not response.candidates:
            return {"response": "No response from AI.", "tool_calls": tool_calls_made, "history": _serialize_history(chat.history)}

        parts = response.candidates[0].content.parts if response.candidates[0].content else []
        function_call = None
        text_part = None

        for p in parts:
            if hasattr(p, "function_call") and p.function_call:
                function_call = p.function_call
                break
            if hasattr(p, "text") and p.text:
                text_part = p.text
                break

        if function_call:
            name = getattr(function_call, "name", None) or getattr(function_call, "get", lambda _: None)("name")
            args = getattr(function_call, "args", None) or getattr(function_call, "get", lambda _: {})("args") or {}
            if hasattr(args, "items"):
                args = dict(args)
            else:
                args = {}
            result = await execute_tool(name, args)
            tool_calls_made.append({"tool": name, "args": args})

            # Send function response as next user turn
            from google.generativeai.protos import Part, FunctionResponse
            from google.protobuf import struct_pb2
            try:
                resp_struct = struct_pb2.Struct()
                resp_struct.update({"result": result})
                fr = FunctionResponse(name=name, response=resp_struct)
                to_send = Part(function_response=fr)
            except Exception as proto_err:
                logger.debug(f"Protobuf FunctionResponse failed, using dict fallback: {proto_err}")
                to_send = {"function_response": {"name": name, "response": {"result": result}}}
            continue

        # Text response - we're done
        final = text_part or (response.text if response else "")
        if not final and hasattr(response, "text"):
            final = str(response.text) if response.text else ""
        return {"response": final or "I couldn't generate a response.", "tool_calls": tool_calls_made, "history": _serialize_history(chat.history)}

    return {"response": "Reached maximum reasoning steps. Try a simpler question.", "tool_calls": tool_calls_made, "history": _serialize_history(chat.history)}
