"""Repository for agent_runs — insert + query for monitoring."""

import json
import logging
from datetime import UTC, datetime

from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import get_org_id, sql_execute, transaction

logger = logging.getLogger(__name__)


async def log_agent_run(
    *,
    session_id: str,
    user_id: str = "",
    agent_name: str,
    model: str,
    mode: str = "fast",
    user_message: str = "",
    response_text: str = "",
    tool_calls: list[dict] | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    duration_ms: int = 0,
    attempts: int = 1,
    error: str | None = None,
    error_kind: str | None = None,
    parent_run_id: str | None = None,
    handoff_from: str | None = None,
    validation_passed: bool | None = None,
    validation_failures: list[str] | None = None,
    validation_scores: dict | None = None,
) -> str:
    run_id = new_uuid7_str()
    now = datetime.now(UTC)
    org_id = get_org_id()
    async with transaction():
        await sql_execute(
            """INSERT INTO agent_runs
               (id, session_id, org_id, user_id, agent_name, model, mode,
                user_message, response_text, tool_calls,
                input_tokens, output_tokens, cost_usd, duration_ms,
                attempts, error, error_kind, parent_run_id, handoff_from, created_at,
                validation_passed, validation_failures, validation_scores)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23)""",
            (
                run_id,
                session_id,
                org_id,
                user_id,
                agent_name,
                model,
                mode,
                (user_message or "")[:2000],
                (response_text or "")[:4000],
                json.dumps(tool_calls or []),
                input_tokens,
                output_tokens,
                round(cost_usd, 6),
                duration_ms,
                attempts,
                error,
                error_kind,
                parent_run_id,
                handoff_from,
                now,
                validation_passed,
                json.dumps(validation_failures or []),
                json.dumps(validation_scores or {}),
            ),
            read_only=False,
        )
    return run_id


async def list_runs(
    *,
    agent_name: str | None = None,
    session_id: str | None = None,
    minutes: int = 60,
    limit: int = 50,
    validation_failed_only: bool = False,
) -> list[dict]:
    org_id = get_org_id()
    n = 1
    clauses = [
        f"created_at::timestamptz >= NOW() - INTERVAL '{minutes} minutes'"
    ]
    params: list = []

    clauses.append(f"org_id = ${n}")
    params.append(org_id)
    n += 1

    if agent_name:
        clauses.append(f"agent_name = ${n}")
        params.append(agent_name)
        n += 1
    if session_id:
        clauses.append(f"session_id = ${n}")
        params.append(session_id)
        n += 1
    if validation_failed_only:
        clauses.append("validation_passed = FALSE")

    params.append(limit)
    query = "SELECT * FROM agent_runs WHERE " + " AND ".join(clauses)
    query += f" ORDER BY created_at DESC LIMIT ${n}"
    res = await sql_execute(query, params, read_only=True, max_rows=limit + 1)
    rows = list(res.rows)
    for r in rows:
        if isinstance(r.get("tool_calls"), str):
            r["tool_calls"] = json.loads(r["tool_calls"])
        if isinstance(r.get("validation_failures"), str):
            r["validation_failures"] = json.loads(r["validation_failures"])
        if isinstance(r.get("validation_scores"), str):
            r["validation_scores"] = json.loads(r["validation_scores"])
    return rows


async def get_stats(*, hours: int = 24) -> dict:
    org_id = get_org_id()
    since_expr = f"org_id = $1 AND created_at::timestamptz >= NOW() - INTERVAL '{hours} hours'"

    res_agent = await sql_execute(
        "SELECT"
        " agent_name,"
        " COUNT(*) as runs,"
        " SUM(input_tokens) as total_input_tokens,"
        " SUM(output_tokens) as total_output_tokens,"
        " SUM(cost_usd) as total_cost,"
        " AVG(duration_ms) as avg_duration_ms,"
        " MAX(duration_ms) as max_duration_ms,"
        " SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as errors"
        " FROM agent_runs"
        " WHERE " + since_expr + " GROUP BY agent_name"
        " ORDER BY runs DESC",
        [org_id],
        read_only=True,
        max_rows=500,
    )
    by_agent = res_agent.rows

    res_totals = await sql_execute(
        "SELECT"
        " COUNT(*) as total_runs,"
        " SUM(input_tokens) as total_input_tokens,"
        " SUM(output_tokens) as total_output_tokens,"
        " SUM(cost_usd) as total_cost,"
        " AVG(duration_ms) as avg_duration_ms,"
        " SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as total_errors"
        " FROM agent_runs"
        " WHERE " + since_expr,
        [org_id],
        read_only=True,
        max_rows=2,
    )
    totals = res_totals.rows[0] if res_totals.rows else None

    res_model = await sql_execute(
        "SELECT model, COUNT(*) as runs, SUM(cost_usd) as cost"
        " FROM agent_runs WHERE "
        + since_expr
        + " GROUP BY model ORDER BY cost DESC",
        [org_id],
        read_only=True,
        max_rows=500,
    )
    by_model = res_model.rows

    return {
        "period_hours": hours,
        "totals": totals,
        "by_agent": by_agent,
        "by_model": by_model,
    }


async def get_session_trace(session_id: str) -> list[dict]:
    org_id = get_org_id()
    res = await sql_execute(
        "SELECT * FROM agent_runs WHERE session_id = $1 AND org_id = $2 ORDER BY created_at ASC",
        (session_id, org_id),
        read_only=True,
        max_rows=2000,
    )
    rows: list[dict] = list(res.rows)
    for r in rows:
        for key in ("tool_calls", "validation_failures", "validation_scores"):
            if isinstance(r.get(key), str):
                r[key] = json.loads(r[key])
    return rows


async def get_validation_summary(*, hours: int = 24) -> dict:
    """Validation pass/fail rates and most common failure types per agent."""
    org_id = get_org_id()
    since_expr = f"org_id = $1 AND created_at::timestamptz >= NOW() - INTERVAL '{hours} hours' AND validation_passed IS NOT NULL"

    res_ba = await sql_execute(
        "SELECT agent_name,"
        " COUNT(*) as runs,"
        " SUM(CASE WHEN validation_passed THEN 1 ELSE 0 END) as passed,"
        " SUM(CASE WHEN NOT validation_passed THEN 1 ELSE 0 END) as failed"
        " FROM agent_runs WHERE "
        + since_expr
        + " GROUP BY agent_name ORDER BY failed DESC",
        [org_id],
        read_only=True,
        max_rows=500,
    )
    by_agent = list(res_ba.rows)
    for r in by_agent:
        total = r["runs"] or 1
        r["pass_rate"] = round(r["passed"] / total, 3)

    res_fail = await sql_execute(
        "SELECT validation_failures FROM agent_runs"
        " WHERE " + since_expr + " AND validation_passed = FALSE",
        [org_id],
        read_only=True,
        max_rows=5000,
    )
    failure_counts: dict[str, int] = {}
    for row in res_fail.rows:
        raw = row["validation_failures"]
        try:
            failures = json.loads(raw) if isinstance(raw, str) else (raw or [])
            for f in failures:
                key = f.split(":")[0]
                failure_counts[key] = failure_counts.get(key, 0) + 1
        except Exception as _e:
            logger.debug("Could not parse validation_failures row: %s", _e)

    return {
        "period_hours": hours,
        "by_agent": by_agent,
        "failure_type_counts": dict(
            sorted(failure_counts.items(), key=lambda x: -x[1])
        ),
    }


async def get_cost_breakdown(
    *, days: int = 7, group_by: str = "agent"
) -> list[dict]:
    org_id = get_org_id()
    since_expr = f"org_id = $1 AND created_at::timestamptz >= NOW() - INTERVAL '{days} days'"
    day_expr = "(created_at::timestamptz)::date"

    col = {"agent": "agent_name", "model": "model", "org": "org_id"}.get(
        group_by, "agent_name"
    )
    query = "SELECT "
    query += col
    query += " as group_key, "
    query += day_expr
    query += (
        " as day,"
        " COUNT(*) as runs,"
        " SUM(input_tokens) as input_tokens,"
        " SUM(output_tokens) as output_tokens,"
        " SUM(cost_usd) as cost"
        " FROM agent_runs"
        " WHERE "
    )
    query += since_expr
    query += " GROUP BY "
    query += col
    query += ", "
    query += day_expr
    query += " ORDER BY day DESC, cost DESC"
    res = await sql_execute(query, [org_id], read_only=True, max_rows=5000)
    return list(res.rows)
