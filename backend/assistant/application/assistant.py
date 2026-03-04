"""Chat assistant entrypoint — orchestrates routing, dispatch, and coordination.

Routing modes:
- "auto" (default): complexity classification → dispatch strategy
  - TRIVIAL: canned response or cheap model
  - STRUCTURED: DAG fast path (no LLM orchestration)
  - SIMPLE: single specialist agent
  - COMPLEX: coordinator or parallel fan-out
- Explicit agent_type ("inventory", "ops", etc.): bypasses router, dispatches directly
"""
import asyncio
import importlib
import logging
import uuid

from shared.infrastructure.config import ANTHROPIC_AVAILABLE, OPENROUTER_AVAILABLE, LLM_SETUP_URL
from assistant.agents.deps import AgentDeps
from assistant.agents.contracts import (
    AgentResult, Complexity, RouteDecision, TurnState, UsageInfo,
)

logger = logging.getLogger(__name__)

LLM_NOT_CONFIGURED_MSG = (
    "Chat assistant requires an API key. Set OPENROUTER_API_KEY (preferred) or "
    f"ANTHROPIC_API_KEY in backend/.env.  Get a key at {LLM_SETUP_URL}"
)

_AGENT_MODULES = {
    "inventory":   "assistant.agents.inventory",
    "ops":         "assistant.agents.ops",
    "finance":     "assistant.agents.finance",
    "insights":    "assistant.agents.insights",
    "general":     "assistant.agents.general",
    "dashboard":   "assistant.agents.general",
    "coordinator": "assistant.agents.coordinator",
}


async def chat(
    user_message: str,
    history: list[dict] | None,
    ctx: dict | None = None,
    mode: str = "fast",
    agent_type: str = "auto",
    session_id: str = "",
) -> dict:
    """Dispatch user message to the appropriate specialist agent(s)."""
    if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE:
        return {"response": LLM_NOT_CONFIGURED_MSG, "tool_calls": [], "history": [], "agent": None}

    ctx = ctx or {}
    deps = AgentDeps(
        org_id=ctx.get("org_id", "default"),
        user_id=ctx.get("user_id", ""),
        user_name=ctx.get("user_name", ""),
    )

    if agent_type == "auto":
        return await _orchestrate(user_message, history, deps, mode, session_id)

    module_path = _AGENT_MODULES.get(agent_type, _AGENT_MODULES["general"])
    agent_module = importlib.import_module(module_path)
    return await agent_module.run(user_message, history=history, deps=deps, mode=mode, session_id=session_id)


# ── Trivial response (no LLM) ────────────────────────────────────────────────

_TRIVIAL_RESPONSES = {
    "hi": "Hello! How can I help you today?",
    "hello": "Hello! How can I help you today?",
    "hey": "Hey! What can I help you with?",
    "thanks": "You're welcome! Let me know if you need anything else.",
    "thank you": "You're welcome! Let me know if you need anything else.",
    "ok": "Got it. What would you like to know?",
    "okay": "Got it. What would you like to know?",
    "bye": "Goodbye! Come back anytime.",
    "goodbye": "Goodbye! Come back anytime.",
    "good morning": "Good morning! What can I help you with today?",
    "good afternoon": "Good afternoon! What can I help you with today?",
}


def _trivial_response(turn: TurnState) -> dict:
    """Return a canned response for trivial queries — zero LLM cost."""
    m = turn.query.lower().strip()
    for trigger, response in _TRIVIAL_RESPONSES.items():
        if trigger in m:
            result = AgentResult(agent="system", response=response)
            d = result.to_dict()
            d["routed_to"] = ["trivial"]
            return d

    result = AgentResult(
        agent="system",
        response="Hello! I can help with inventory, operations, finances, and insights. What would you like to know?",
    )
    d = result.to_dict()
    d["routed_to"] = ["trivial"]
    return d


# ── DAG fast path ─────────────────────────────────────────────────────────────

async def _dag_dispatch(turn: TurnState, deps: AgentDeps) -> dict:
    """Execute a structured DAG plan — parallel tool calls, cheap LLM synthesis."""
    from assistant.agents.dag import match_plan, execute_plan

    plan = match_plan(turn.query)
    if not plan:
        return await _single_dispatch("general", turn.query, None, deps, "fast", turn.session_id)

    tool_runner = _build_tool_runner(deps.org_id)
    dag_result = await execute_plan(plan, tool_runner, deps.org_id)

    synth_node = plan.synthesis_node
    if synth_node and synth_node.id in dag_result.node_results:
        import json
        synth_data = dag_result.node_results[synth_node.id]
        try:
            sections = json.loads(synth_data)
        except (json.JSONDecodeError, TypeError):
            sections = {"data": synth_data}

        response = await _synthesize_dag_results(turn.query, sections)
    else:
        parts = [f"**{k}**: {v}" for k, v in dag_result.node_results.items() if k != "synth"]
        response = "\n\n".join(parts)

    result = AgentResult(
        agent="dag",
        response=response,
        usage=UsageInfo(model="dag", tier="cheap"),
    )
    d = result.to_dict()
    d["routed_to"] = ["dag"]
    d["dag_template"] = plan.template_name
    return d


async def _synthesize_dag_results(query: str, sections: dict) -> str:
    """Use a cheap LLM to synthesize DAG tool results into a coherent answer."""
    import json
    try:
        from assistant.infrastructure.llm.catalog import resolve_tier_model
        from assistant.infrastructure.llm import get_model

        model_id = resolve_tier_model("cheap")
        if not model_id:
            return _format_dag_sections(sections)

        from pydantic_ai import Agent as SynthAgent
        synth = SynthAgent(
            get_model(model_id),
            system_prompt=(
                "You synthesize structured data into a clear markdown report. "
                "Use ## headers, tables, and bold for key figures. Be concise."
            ),
        )
        result = await asyncio.wait_for(
            synth.run(f"Question: {query}\n\nData:\n{json.dumps(sections, indent=2)}"),
            timeout=15,
        )
        return result.output if isinstance(result.output, str) else str(result.output)
    except Exception as e:
        logger.warning(f"DAG synthesis failed, using raw format: {e}")
        return _format_dag_sections(sections)


def _format_dag_sections(sections: dict) -> str:
    """Fallback formatting when LLM synthesis is unavailable."""
    parts = []
    for key, value in sections.items():
        if isinstance(value, str) and value.strip():
            parts.append(f"## {key.replace('_', ' ').title()}\n\n{value}")
    return "\n\n---\n\n".join(parts) if parts else "No data available."


def _build_tool_runner(org_id: str):
    """Map tool name strings to the actual DB-query helper functions."""
    from assistant.agents.inventory import (
        _search_products, _get_inventory_stats, _list_low_stock,
        _get_reorder_suggestions, _get_department_health, _get_slow_movers,
    )
    from assistant.agents.ops import (
        _list_recent_withdrawals, _list_pending_material_requests,
    )
    from assistant.agents.finance import (
        _get_revenue_summary, _get_outstanding_balances, _get_pl_summary,
        _get_top_products as _fin_top_products,
    )
    from assistant.agents.insights import (
        _get_top_products, _forecast_stockout,
    )

    tool_map = {
        "search_products":             lambda args, oid: _search_products(args, oid),
        "get_inventory_stats":         lambda args, oid: _get_inventory_stats(oid),
        "list_low_stock":              lambda args, oid: _list_low_stock(args, oid),
        "get_reorder_suggestions":     lambda args, oid: _get_reorder_suggestions(args, oid),
        "get_department_health":       lambda args, oid: _get_department_health(oid),
        "get_slow_movers":             lambda args, oid: _get_slow_movers(args, oid),
        "list_recent_withdrawals":     lambda args, oid: _list_recent_withdrawals(args, oid),
        "list_pending_material_requests": lambda args, oid: _list_pending_material_requests(args, oid),
        "get_revenue_summary":         lambda args, oid: _get_revenue_summary(args, oid),
        "get_outstanding_balances":    lambda args, oid: _get_outstanding_balances(args, oid),
        "get_pl_summary":              lambda args, oid: _get_pl_summary(args, oid),
        "get_top_products":            lambda args, oid: _get_top_products(args, oid),
        "forecast_stockout":           lambda args, oid: _forecast_stockout(args, oid),
    }

    async def runner(tool_name: str, args: dict, oid: str) -> str:
        fn = tool_map.get(tool_name)
        if not fn:
            return f'{{"error": "unknown tool: {tool_name}"}}'
        result = await fn(args, oid)
        return result if isinstance(result, str) else str(result)

    return runner


# ── Single agent dispatch ─────────────────────────────────────────────────────

async def _single_dispatch(
    agent_name: str,
    user_message: str,
    history: list[dict] | None,
    deps: AgentDeps,
    mode: str,
    session_id: str,
) -> dict:
    """Dispatch to a single agent by name."""
    module_path = _AGENT_MODULES.get(agent_name, _AGENT_MODULES["general"])
    agent_module = importlib.import_module(module_path)
    result = await agent_module.run(
        user_message, history=history, deps=deps, mode=mode, session_id=session_id,
    )
    result["routed_to"] = [agent_name]
    return result


# ── Parallel fan-out ──────────────────────────────────────────────────────────

async def _parallel_dispatch(
    agents: list[str],
    user_message: str,
    history: list[dict] | None,
    deps: AgentDeps,
    mode: str,
    session_id: str,
) -> dict:
    """Run multiple agents in parallel and merge their results."""
    from assistant.agents.router import merge_responses

    async def _run_one(agent_name: str) -> dict:
        try:
            return await _single_dispatch(agent_name, user_message, history, deps, mode, session_id)
        except Exception as e:
            logger.error(f"Fan-out agent {agent_name} failed: {e}")
            return {
                "response": f"The {agent_name} agent encountered an issue.",
                "tool_calls": [], "history": history or [], "thinking": [],
                "agent": agent_name,
                "usage": {"cost_usd": 0, "input_tokens": 0, "output_tokens": 0},
            }

    results = await asyncio.gather(*[_run_one(a) for a in agents])
    return merge_responses(user_message, list(results))


# ── Orchestration loop ────────────────────────────────────────────────────────

async def _orchestrate(
    user_message: str,
    history: list[dict] | None,
    deps: AgentDeps,
    mode: str,
    session_id: str,
) -> dict:
    """Full orchestration: classify complexity → route → dispatch → validate → maybe re-route."""
    from assistant.agents.router import route, classify_complexity
    from shared.infrastructure.config import SESSION_COST_CAP

    trace_id = str(uuid.uuid4())[:8]
    complexity = classify_complexity(user_message)

    turn = TurnState(
        trace_id=trace_id,
        query=user_message,
        session_id=session_id,
        complexity=complexity,
    )
    deps.turn_state = turn
    deps.trace_id = trace_id

    # Fast paths: no routing needed
    if complexity == Complexity.TRIVIAL:
        logger.info(f"[{trace_id}] trivial → canned response")
        return _trivial_response(turn)

    if complexity == Complexity.STRUCTURED:
        logger.info(f"[{trace_id}] structured → DAG fast path")
        return await _dag_dispatch(turn, deps)

    # Full routing for SIMPLE and COMPLEX
    decision = await route(user_message, history)
    turn.route = decision
    logger.info(
        f"[{trace_id}] {complexity.value} → {decision.strategy} "
        f"primary={decision.primary} supporting={decision.supporting}"
    )

    result = await _dispatch_decision(decision, user_message, history, deps, mode, session_id)

    # Check for handoff requests from the agent result
    agent_result = result.get("_agent_result")
    if (
        agent_result
        and isinstance(agent_result, AgentResult)
        and agent_result.needs_handoff
        and turn.iteration < turn.max_iterations
    ):
        handoff = agent_result.needs_handoff
        turn.handoff_chain.append(handoff.source_agent)
        turn.iteration += 1
        logger.info(
            f"[{trace_id}] handoff: {handoff.source_agent} → {handoff.target_agent} "
            f"reason={handoff.reason}"
        )
        context_msg = user_message
        if handoff.partial_result:
            context_msg = (
                f"{user_message}\n\n"
                f"[Context from {handoff.source_agent}: {handoff.partial_result}]"
            )
        result = await _single_dispatch(
            handoff.target_agent, context_msg, history, deps, mode, session_id,
        )

    # Validation-triggered re-routing
    validation = result.get("validation", {})
    if (
        validation
        and not validation.get("passed", True)
        and turn.iteration < turn.max_iterations
    ):
        failures = validation.get("failures", [])
        if "domain_mismatch" in failures:
            turn.iteration += 1
            logger.info(f"[{trace_id}] re-routing due to domain_mismatch")
            decision = await route(user_message, history)
            result = await _dispatch_decision(
                decision, user_message, history, deps, mode, session_id,
            )

    return result


async def _dispatch_decision(
    decision: RouteDecision,
    user_message: str,
    history: list[dict] | None,
    deps: AgentDeps,
    mode: str,
    session_id: str,
) -> dict:
    """Dispatch based on a RouteDecision's strategy."""
    if decision.strategy == "dag":
        turn = deps.turn_state or TurnState(
            trace_id="", query=user_message, session_id=session_id,
            complexity=Complexity.STRUCTURED,
        )
        return await _dag_dispatch(turn, deps)

    if decision.strategy == "parallel":
        agents = [decision.primary] + decision.supporting
        return await _parallel_dispatch(agents, user_message, history, deps, mode, session_id)

    if decision.strategy == "coordinate":
        return await _single_dispatch("coordinator", user_message, history, deps, mode, session_id)

    # default: single agent
    return await _single_dispatch(decision.primary, user_message, history, deps, mode, session_id)
