"""Data analyst agent — ad hoc SQL analysis with sandboxed execution.

Agent construction is deferred to first use so that missing API keys
don't crash the import chain at startup.
"""

import json
import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.analyst.schema_context import format_detail, format_overview
from assistant.agents.analyst.sql_executor import (
    AnalystQueryError,
    execute_sandboxed,
    format_result,
)
from assistant.agents.core.contracts import SpecialistResult, UsageInfo
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.messages import build_message_history
from assistant.agents.core.model_registry import calc_cost, get_model, get_model_name
from assistant.agents.core.tokens import budget_tool_result
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")

MAX_QUERIES_PER_RUN = 8

_agent: Agent[AgentDeps, str] | None = None


def _get_agent() -> Agent[AgentDeps, str]:
    """Lazily construct the PydanticAI Agent on first use."""
    global _agent
    if _agent is not None:
        return _agent
    _agent = Agent(
        get_model("agent:unified"),
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings={"temperature": 0},
    )

    @_agent.tool
    async def get_schema_context(
        ctx: RunContext[AgentDeps],
        tables: list[str] | None = None,
    ) -> str:
        """Get database schema for query planning.

        Call with no arguments for an overview of all tables (names + columns).
        Pass specific table names for full detail (types, PKs, FKs, nullability).
        """
        if tables:
            return budget_tool_result(format_detail(tables))
        return budget_tool_result(format_overview())

    @_agent.tool
    async def run_sql(
        ctx: RunContext[AgentDeps],
        query: str,
        description: str = "",
    ) -> str:
        """Execute a read-only SQL query against the database.

        The query MUST include WHERE organization_id = $1 for org isolation.
        The org_id parameter is injected automatically — do not pass it.
        Max 500 rows returned, 10-second timeout.
        Returns JSON with columns, rows, row_count, and truncated flag.
        """
        query_count = ctx.deps.query_results.get("_count", 0)
        if query_count >= MAX_QUERIES_PER_RUN:
            return json.dumps(
                {
                    "error": f"Query limit reached ({MAX_QUERIES_PER_RUN} per session). "
                    "Synthesize your findings from the data you already have."
                }
            )

        try:
            result_obj = await execute_sandboxed(query)
        except AnalystQueryError as e:
            return json.dumps({"error": str(e)})
        formatted = format_result(result_obj)

        label = description or f"query_{query_count + 1}"
        ctx.deps.query_results[label] = {
            "columns": result_obj.columns,
            "row_count": result_obj.row_count,
            "truncated": result_obj.truncated,
        }
        ctx.deps.query_results["_count"] = query_count + 1

        if result_obj.rows and len(result_obj.columns) >= 2:
            rows_for_block = [
                [str(row.get(c, "")) for c in result_obj.columns] for row in result_obj.rows[:50]
            ]
            block = {
                "type": "data_table",
                "title": description or f"Query result ({result_obj.row_count} rows)",
                "columns": result_obj.columns,
                "rows": rows_for_block,
            }
            ctx.deps.blocks.append(block)

        return budget_tool_result(formatted)

    return _agent


# ── Entry point ───────────────────────────────────────────────────────────────


async def run(question: str, deps: AgentDeps, *, usage=None) -> SpecialistResult:
    """Run the data analyst and return result with usage info."""
    agent = _get_agent()
    msg_history = build_message_history(deps.history)
    run_kwargs = {"message_history": msg_history, "deps": deps}
    if usage is not None:
        run_kwargs["usage"] = usage
    try:
        result = await agent.run(question, **run_kwargs)
    except Exception:
        logger.exception("analyst failed")
        return SpecialistResult(
            response="I ran into an issue running the analysis. Please try again.",
            usage=UsageInfo(),
        )
    response = result.output if isinstance(result.output, str) else str(result.output)
    model_name = get_model_name("agent:analyst")
    usage = result.usage()
    return SpecialistResult(
        response=response,
        usage=UsageInfo(
            cost_usd=calc_cost(model_name, usage),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=model_name,
        ),
    )
