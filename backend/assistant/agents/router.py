"""
Intelligent message router — classifies user messages and dispatches to
the right specialist agent(s). Uses Haiku for cheap/fast classification.

Supports multi-agent fan-out: for cross-domain questions, dispatches to
multiple specialists in parallel, then merges their results.
"""
import asyncio
import json
import logging

import anthropic

from shared.infrastructure.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_FAST_MODEL,
    AGENT_PRIMARY_MODEL,
    ANTHROPIC_AVAILABLE,
)

logger = logging.getLogger(__name__)

_VALID_AGENTS = {"inventory", "ops", "finance", "insights", "general"}

_ROUTER_SYSTEM = """You classify user messages for a hardware store management system (SKU-Ops).
Pick the best specialist agent(s) for the question. Return ONLY valid JSON.

AGENTS:
- inventory: product search, stock levels, reorders, departments, vendors, SKUs, barcodes
- ops: withdrawals, material requests, contractors, jobs, service addresses
- finance: revenue, invoices, payments, P&L, outstanding balances, margins, Xero
- insights: trends, top products, forecasting, velocity, slow movers, analytics
- general: greetings, help, navigation, or unclear/ambiguous questions

RULES:
- Single-domain question → one agent: {"agents": ["inventory"]}
- Cross-domain question → multiple agents: {"agents": ["inventory", "finance"]}
- If unsure, use general — it has cross-domain tools
- Max 3 agents (never fan out to all 5)
- Greetings/chat/help → general only
- "overview" or "summary" or "dashboard" → general (it has cross-domain tools for this)

EXAMPLES:
"do we have PVC pipes?" → {"agents": ["inventory"]}
"what's our revenue this week?" → {"agents": ["finance"]}
"pending material requests" → {"agents": ["ops"]}
"top selling products" → {"agents": ["insights"]}
"how's the business doing?" → {"agents": ["general"]}
"show me low stock items and who owes us" → {"agents": ["inventory", "finance"]}
"what products are running out and what's our margin?" → {"agents": ["insights", "finance"]}
"hi" → {"agents": ["general"]}"""

_MERGE_SYSTEM = """You are merging responses from multiple specialist agents into one coherent answer.
Combine the information naturally. Use markdown formatting. Don't mention the agents by name —
just present the unified answer as if one assistant gathered all the data."""


async def classify(message: str, history: list[dict] | None = None) -> list[str]:
    """Classify a user message into one or more agent types. Returns list of agent names."""
    if not ANTHROPIC_AVAILABLE:
        return ["general"]

    # Quick heuristic shortcuts for obvious patterns (skip the LLM call entirely)
    route = _heuristic_route(message)
    if route:
        return route

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        context = ""
        if history and len(history) >= 2:
            recent = history[-4:]
            context = "\n".join(f"{h['role']}: {h['content'][:100]}" for h in recent)
            context = f"\nRecent conversation:\n{context}\n"

        resp = await asyncio.wait_for(
            client.messages.create(
                model=ANTHROPIC_FAST_MODEL,
                max_tokens=80,
                system=_ROUTER_SYSTEM,
                messages=[{"role": "user", "content": f"{context}User message: {message}"}],
            ),
            timeout=8,
        )

        text = resp.content[0].text.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        agents = data.get("agents", ["general"])
        agents = [a for a in agents if a in _VALID_AGENTS]
        if not agents:
            agents = ["general"]
        return agents[:3]

    except Exception as e:
        logger.warning(f"Router classification failed, falling back to general: {e}")
        return ["general"]


def _heuristic_route(message: str) -> list[str] | None:
    """Fast keyword-based routing for obvious cases. Returns None to defer to LLM."""
    m = message.lower().strip()

    if len(m) < 15 and any(w in m for w in ("hi", "hello", "hey", "help", "thanks", "thank you")):
        return ["general"]

    # Strong single-domain signals
    inv_words = ("stock", "reorder", "sku", "barcode", "product", "low stock", "out of stock", "department", "vendor")
    ops_words = ("withdrawal", "material request", "contractor", "job", "service address")
    fin_words = ("revenue", "invoice", "payment", "p&l", "profit", "margin", "outstanding", "owes", "xero", "balance")
    ins_words = ("trend", "forecast", "stockout", "velocity", "top sell", "best sell", "slow mover", "analytics")

    scores = {
        "inventory": sum(1 for w in inv_words if w in m),
        "ops": sum(1 for w in ops_words if w in m),
        "finance": sum(1 for w in fin_words if w in m),
        "insights": sum(1 for w in ins_words if w in m),
    }
    hits = {k: v for k, v in scores.items() if v > 0}

    if not hits:
        return None  # defer to LLM

    if len(hits) == 1:
        return [list(hits.keys())[0]]

    # Multiple domains detected — return top 2 by score
    ranked = sorted(hits.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in ranked[:2]]


async def merge_responses(question: str, results: list[dict]) -> dict:
    """Merge responses from multiple agents into one coherent answer."""
    if len(results) == 1:
        return results[0]

    successful = [r for r in results if r.get("response") and "ran into an issue" not in r.get("response", "")]
    if not successful:
        return results[0]
    if len(successful) == 1:
        return successful[0]

    # Combine context for the merger
    agent_sections = []
    all_tool_calls = []
    total_cost = 0.0
    total_input = 0
    total_output = 0
    agents_used = []

    for r in successful:
        agent = r.get("agent", "unknown")
        agents_used.append(agent)
        agent_sections.append(f"[{agent} agent]:\n{r.get('response', '')}")
        all_tool_calls.extend(r.get("tool_calls", []))
        usage = r.get("usage", {})
        total_cost += usage.get("cost_usd", 0)
        total_input += usage.get("input_tokens", 0)
        total_output += usage.get("output_tokens", 0)

    separator = "\n\n---\n\n"
    combined_input = f"User question: {question}\n\nAgent responses to merge:\n{separator.join(agent_sections)}"

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await asyncio.wait_for(
            client.messages.create(
                model=ANTHROPIC_FAST_MODEL,
                max_tokens=2000,
                system=_MERGE_SYSTEM,
                messages=[{"role": "user", "content": combined_input}],
            ),
            timeout=15,
        )
        merged_text = resp.content[0].text
        merge_usage = resp.usage
        total_cost += (merge_usage.input_tokens * 0.80 + merge_usage.output_tokens * 4.00) / 1_000_000
        total_input += merge_usage.input_tokens
        total_output += merge_usage.output_tokens
    except Exception as e:
        logger.warning(f"Merge failed, concatenating responses: {e}")
        merged_text = separator.join(r.get("response", "") for r in successful)

    best_history = max(successful, key=lambda r: len(r.get("history", []))).get("history", [])

    return {
        "response": merged_text,
        "tool_calls": all_tool_calls,
        "thinking": [],
        "history": best_history,
        "usage": {
            "cost_usd": round(total_cost, 6),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "model": AGENT_PRIMARY_MODEL,
        },
        "agent": "+".join(agents_used),
        "routed_to": agents_used,
    }
