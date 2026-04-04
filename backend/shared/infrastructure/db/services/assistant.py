"""Assistant agent runs, embeddings, and memory artifacts."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import uuid as uuid_std
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from assistant.infrastructure.embedding_store import (
    _vec_to_pgvector,
    content_hash,
    embed_query,
    embed_texts,
    is_pgvector_available,
)
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.db.services._base import DomainDatabaseService

logger = logging.getLogger(__name__)

_DEFAULT_MEMORY_TTL_DAYS = 90
_MEMORY_TYPE_BOOST: dict[str, float] = {
    "user_preference": 0.10,
    "decision": 0.08,
    "entity_fact": 0.04,
    "insight": 0.04,
    "session_summary": 0.0,
}


def _embedding_entity_uuid(entity_type: str, entity_id: str) -> str:
    """Stable UUID for embeddings.id / entity_id (column is UUID)."""
    try:
        return str(uuid_std.UUID(entity_id))
    except ValueError:
        return str(uuid_std.uuid5(uuid_std.NAMESPACE_URL, f"{entity_type}:{entity_id}"))


def _decode_agent_run_json_fields(row: dict, keys: tuple[str, ...]) -> None:
    for key in keys:
        if isinstance(row.get(key), str):
            row[key] = json.loads(row[key])


def _memory_embed_done(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.warning("Background embed task failed: %s", exc, exc_info=exc)


class AssistantDatabaseService(DomainDatabaseService):
    async def log_agent_run(self, org_id: str, **kwargs: Any) -> str:
        session_id: str = kwargs["session_id"]
        user_id: str = kwargs.get("user_id", "")
        agent_name: str = kwargs["agent_name"]
        model: str = kwargs["model"]
        mode: str = kwargs.get("mode", "fast")
        user_message: str = kwargs.get("user_message", "")
        response_text: str = kwargs.get("response_text", "")
        tool_calls: list[dict] | None = kwargs.get("tool_calls")
        input_tokens: int = kwargs.get("input_tokens", 0)
        output_tokens: int = kwargs.get("output_tokens", 0)
        cost_usd: float = kwargs.get("cost_usd", 0.0)
        duration_ms: int = kwargs.get("duration_ms", 0)
        attempts: int = kwargs.get("attempts", 1)
        error: str | None = kwargs.get("error")
        error_kind: str | None = kwargs.get("error_kind")
        parent_run_id: str | None = kwargs.get("parent_run_id")
        handoff_from: str | None = kwargs.get("handoff_from")
        validation_passed: bool | None = kwargs.get("validation_passed")
        validation_failures: list[str] | None = kwargs.get("validation_failures")
        validation_scores: dict | None = kwargs.get("validation_scores")

        run_id = new_uuid7_str()
        now = datetime.now(UTC)
        stmt = text(
            """INSERT INTO agent_runs
               (id, session_id, org_id, user_id, agent_name, model, mode,
                user_message, response_text, tool_calls,
                input_tokens, output_tokens, cost_usd, duration_ms,
                attempts, error, error_kind, parent_run_id, handoff_from, created_at,
                validation_passed, validation_failures, validation_scores)
               VALUES
               (:id, :session_id, :org_id, :user_id, :agent_name, :model, :mode,
                :user_message, :response_text, :tool_calls,
                :input_tokens, :output_tokens, :cost_usd, :duration_ms,
                :attempts, :error, :error_kind, :parent_run_id, :handoff_from, :created_at,
                :validation_passed, :validation_failures, :validation_scores)"""
        )
        params = {
            "id": run_id,
            "session_id": session_id,
            "org_id": org_id,
            "user_id": user_id,
            "agent_name": agent_name,
            "model": model,
            "mode": mode,
            "user_message": (user_message or "")[:2000],
            "response_text": (response_text or "")[:4000],
            "tool_calls": json.dumps(tool_calls or []),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
            "duration_ms": duration_ms,
            "attempts": attempts,
            "error": error,
            "error_kind": error_kind,
            "parent_run_id": parent_run_id,
            "handoff_from": handoff_from,
            "created_at": now,
            "validation_passed": validation_passed,
            "validation_failures": json.dumps(validation_failures or []),
            "validation_scores": json.dumps(validation_scores or {}),
        }
        async with self.session() as session:
            await session.execute(stmt, params)
            await self.end_write_session(session)
        return run_id

    async def list_agent_runs(self, org_id: str, **kwargs: Any) -> list[dict]:
        agent_name: str | None = kwargs.get("agent_name")
        session_id_filter: str | None = kwargs.get("session_id")
        minutes: int = kwargs.get("minutes", 60)
        limit: int = kwargs.get("limit", 50)
        validation_failed_only: bool = kwargs.get("validation_failed_only", False)

        clauses = [
            f"created_at::timestamptz >= NOW() - INTERVAL '{minutes} minutes'",
            "org_id = :org_id",
        ]
        params: dict[str, Any] = {"org_id": org_id, "limit": limit}

        if agent_name:
            clauses.append("agent_name = :agent_name")
            params["agent_name"] = agent_name
        if session_id_filter:
            clauses.append("session_id = :session_id")
            params["session_id"] = session_id_filter
        if validation_failed_only:
            clauses.append("validation_passed = FALSE")

        query = "SELECT * FROM agent_runs WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT :limit"
        stmt = text(query)

        async with self.session() as session:
            result = await session.execute(stmt, params)
            rows = [dict(r) for r in result.mappings().all()]
        for r in rows:
            _decode_agent_run_json_fields(
                r, ("tool_calls", "validation_failures", "validation_scores")
            )
        return rows

    async def agent_run_stats(self, org_id: str, **kwargs: Any) -> dict:
        hours: int = kwargs.get("hours", 24)
        since_sql = (
            f"org_id = :org_id AND created_at::timestamptz >= NOW() - INTERVAL '{hours} hours'"
        )
        base_params = {"org_id": org_id}

        async with self.session() as session:
            res_agent = await session.execute(
                text(
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
                    " WHERE " + since_sql + " GROUP BY agent_name"
                    " ORDER BY runs DESC"
                ),
                base_params,
            )
            by_agent = [dict(r) for r in res_agent.mappings().all()]

            res_totals = await session.execute(
                text(
                    "SELECT"
                    " COUNT(*) as total_runs,"
                    " SUM(input_tokens) as total_input_tokens,"
                    " SUM(output_tokens) as total_output_tokens,"
                    " SUM(cost_usd) as total_cost,"
                    " AVG(duration_ms) as avg_duration_ms,"
                    " SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END)"
                    " as total_errors"
                    " FROM agent_runs"
                    " WHERE " + since_sql
                ),
                base_params,
            )
            totals_row = res_totals.mappings().first()
            totals = dict(totals_row) if totals_row else None

            res_model = await session.execute(
                text(
                    "SELECT model, COUNT(*) as runs, SUM(cost_usd) as cost"
                    " FROM agent_runs WHERE " + since_sql + " GROUP BY model ORDER BY cost DESC"
                ),
                base_params,
            )
            by_model = [dict(r) for r in res_model.mappings().all()]

        return {
            "period_hours": hours,
            "totals": totals,
            "by_agent": by_agent,
            "by_model": by_model,
        }

    async def agent_session_trace(self, org_id: str, session_id: str) -> list[dict]:
        stmt = text(
            "SELECT agt.* FROM agent_runs AS agt"
            " WHERE agt.session_id = :session_id AND agt.org_id = :org_id"
            " ORDER BY agt.created_at ASC"
        )
        async with self.session() as session:
            result = await session.execute(stmt, {"session_id": session_id, "org_id": org_id})
            rows = [dict(r) for r in result.mappings().all()]
        for r in rows:
            _decode_agent_run_json_fields(
                r, ("tool_calls", "validation_failures", "validation_scores")
            )
        return rows

    async def agent_validation_summary(self, org_id: str, **kwargs: Any) -> dict:
        hours: int = kwargs.get("hours", 24)
        since_sql = (
            "org_id = :org_id AND created_at::timestamptz >= "
            f"NOW() - INTERVAL '{hours} hours'"
            " AND validation_passed IS NOT NULL"
        )
        base_params = {"org_id": org_id}

        async with self.session() as session:
            res_ba = await session.execute(
                text(
                    "SELECT agent_name,"
                    " COUNT(*) as runs,"
                    " SUM(CASE WHEN validation_passed THEN 1 ELSE 0 END) as passed,"
                    " SUM(CASE WHEN NOT validation_passed THEN 1 ELSE 0 END) as failed"
                    " FROM agent_runs WHERE "
                    + since_sql
                    + " GROUP BY agent_name ORDER BY failed DESC"
                ),
                base_params,
            )
            by_agent = [dict(r) for r in res_ba.mappings().all()]

            res_fail = await session.execute(
                text(
                    "SELECT validation_failures FROM agent_runs"
                    " WHERE " + since_sql + " AND validation_passed = FALSE"
                ),
                base_params,
            )
            fail_rows = list(res_fail.mappings().all())

        for r in by_agent:
            total = r["runs"] or 1
            r["pass_rate"] = round(r["passed"] / total, 3)

        failure_counts: dict[str, int] = {}
        for row in fail_rows:
            raw = row["validation_failures"]
            try:
                failures = json.loads(raw) if isinstance(raw, str) else (raw or [])
                for f in failures:
                    key = f.split(":")[0]
                    failure_counts[key] = failure_counts.get(key, 0) + 1
            except Exception as e:
                logger.debug("Could not parse validation_failures row: %s", e)

        return {
            "period_hours": hours,
            "by_agent": by_agent,
            "failure_type_counts": dict(sorted(failure_counts.items(), key=lambda x: -x[1])),
        }

    async def agent_cost_breakdown(self, org_id: str, **kwargs: Any) -> list[dict]:
        days: int = kwargs.get("days", 7)
        group_by: str = kwargs.get("group_by", "agent")
        since_sql = (
            f"org_id = :org_id AND created_at::timestamptz >= NOW() - INTERVAL '{days} days'"
        )
        day_expr = "(created_at::timestamptz)::date"

        col = {"agent": "agent_name", "model": "model", "org": "org_id"}.get(group_by, "agent_name")
        query = (
            "SELECT " + col + " as group_key, " + day_expr + " as day,"
            " COUNT(*) as runs,"
            " SUM(input_tokens) as input_tokens,"
            " SUM(output_tokens) as output_tokens,"
            " SUM(cost_usd) as cost"
            " FROM agent_runs"
            " WHERE "
            + since_sql
            + " GROUP BY "
            + col
            + ", "
            + day_expr
            + " ORDER BY day DESC, cost DESC"
        )
        async with self.session() as session:
            result = await session.execute(text(query), {"org_id": org_id})
            return [dict(r) for r in result.mappings().all()]

    async def embedding_is_pgvector_available(self) -> bool:
        return await is_pgvector_available()

    async def embedding_embed_texts(self, texts: list[str]) -> Any:
        return await embed_texts(texts)

    async def embedding_embed_query(self, query: str) -> Any:
        return await embed_query(query)

    async def embedding_upsert(
        self,
        org_id: str,
        entity_type: str,
        entity_id: str,
        content: str,
        embedding: Any,
    ) -> bool:
        if not await is_pgvector_available():
            return False
        try:
            chash = content_hash(content)
            vec_str = _vec_to_pgvector(embedding)
            eid = _embedding_entity_uuid(entity_type, entity_id)
            row_pk = eid
            sel = text(
                "SELECT content_hash FROM embeddings "
                "WHERE org_id = :org_id AND entity_type = :entity_type "
                "AND entity_id = CAST(:entity_id AS uuid)"
            )
            now = datetime.now(UTC)
            async with self.session() as session:
                res = await session.execute(
                    sel,
                    {
                        "org_id": org_id,
                        "entity_type": entity_type,
                        "entity_id": eid,
                    },
                )
                row = res.mappings().first()
                existing = dict(row) if row else None
                if existing and existing.get("content_hash") == chash:
                    return False

                if existing:
                    upd = text(
                        "UPDATE embeddings SET content = :content, "
                        "content_hash = :content_hash, "
                        "embedding = CAST(:embedding AS vector), updated_at = :updated_at "
                        "WHERE org_id = :org_id AND entity_type = :entity_type "
                        "AND entity_id = CAST(:entity_id AS uuid)"
                    )
                    await session.execute(
                        upd,
                        {
                            "content": content,
                            "content_hash": chash,
                            "embedding": vec_str,
                            "updated_at": now,
                            "org_id": org_id,
                            "entity_type": entity_type,
                            "entity_id": eid,
                        },
                    )
                else:
                    ins = text(
                        "INSERT INTO embeddings (id, org_id, entity_type, entity_id, "
                        "content, content_hash, embedding, updated_at) "
                        "VALUES (CAST(:id AS uuid), :org_id, :entity_type, CAST(:entity_id AS uuid), "
                        ":content, :content_hash, CAST(:embedding AS vector), :updated_at)"
                    )
                    await session.execute(
                        ins,
                        {
                            "id": row_pk,
                            "org_id": org_id,
                            "entity_type": entity_type,
                            "entity_id": eid,
                            "content": content,
                            "content_hash": chash,
                            "embedding": vec_str,
                            "updated_at": now,
                        },
                    )
                await self.end_write_session(session)
            return True
        except Exception as e:
            logger.warning("embedding upsert failed: %s", e)
            return False

    async def embedding_upsert_batch(
        self,
        org_id: str,
        entity_type: str,
        items: list[tuple[str, str, Any]],
    ) -> int:
        if not await is_pgvector_available() or not items:
            return 0
        try:
            now = datetime.now(UTC)
            eids = [_embedding_entity_uuid(entity_type, raw_id) for raw_id, _, _ in items]
            existing_hashes: dict[str, str] = {}

            async with self.session() as session:
                for batch_start in range(0, len(eids), 200):
                    batch_eids = eids[batch_start : batch_start + 200]
                    params: dict[str, Any] = {
                        "org_id": org_id,
                        "entity_type": entity_type,
                    }
                    parts = []
                    for i, eid in enumerate(batch_eids):
                        k = f"id{i}"
                        params[k] = eid
                        parts.append(f"CAST(:{k} AS uuid)")
                    in_clause = ", ".join(parts)
                    q = text(
                        f"SELECT entity_id, content_hash FROM embeddings "
                        f"WHERE org_id = :org_id AND entity_type = :entity_type "
                        f"AND entity_id IN ({in_clause})"
                    )
                    res = await session.execute(q, params)
                    for r in res.mappings().all():
                        existing_hashes[str(r["entity_id"])] = r["content_hash"]

                rows_to_upsert: list[tuple[Any, ...]] = []
                for raw_eid, content_text, vec in items:
                    eid = _embedding_entity_uuid(entity_type, raw_eid)
                    chash = content_hash(content_text)
                    if existing_hashes.get(eid) == chash:
                        continue
                    row_pk = eid
                    vec_str = _vec_to_pgvector(vec)
                    rows_to_upsert.append(
                        (
                            row_pk,
                            org_id,
                            entity_type,
                            eid,
                            content_text,
                            chash,
                            vec_str,
                            now,
                        )
                    )

                stmt = text(
                    "INSERT INTO embeddings (id, org_id, entity_type, entity_id, "
                    "content, content_hash, embedding, updated_at) "
                    "VALUES (CAST(:id AS uuid), :org_id, :entity_type, CAST(:entity_id AS uuid), "
                    ":content, :content_hash, CAST(:embedding AS vector), :updated_at) "
                    "ON CONFLICT (org_id, entity_type, entity_id) DO UPDATE SET "
                    "content = EXCLUDED.content, content_hash = EXCLUDED.content_hash, "
                    "embedding = EXCLUDED.embedding, updated_at = EXCLUDED.updated_at"
                )
                for row in rows_to_upsert:
                    await session.execute(
                        stmt,
                        {
                            "id": row[0],
                            "org_id": row[1],
                            "entity_type": row[2],
                            "entity_id": row[3],
                            "content": row[4],
                            "content_hash": row[5],
                            "embedding": row[6],
                            "updated_at": row[7],
                        },
                    )
                if rows_to_upsert:
                    await self.end_write_session(session)
                written = len(rows_to_upsert)

            return written
        except Exception as e:
            logger.warning("embedding batch upsert failed: %s", e)
            return 0

    async def embedding_search(
        self,
        org_id: str,
        query_embedding: Any,
        entity_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        if not await is_pgvector_available():
            return []
        try:
            vec_str = _vec_to_pgvector(query_embedding)

            async with self.session() as session:
                if entity_types:
                    params: dict[str, Any] = {
                        "vec": vec_str,
                        "org_id": org_id,
                        "limit": limit,
                    }
                    parts = []
                    for i, et in enumerate(entity_types):
                        k = f"et{i}"
                        params[k] = et
                        parts.append(f":{k}")
                    in_clause = ", ".join(parts)
                    res = await session.execute(
                        text(
                            f"SELECT entity_type, entity_id, content, "
                            f"1 - (embedding <=> CAST(:vec AS vector)) AS similarity "
                            f"FROM embeddings "
                            f"WHERE org_id = :org_id AND entity_type IN ({in_clause}) "
                            f"ORDER BY embedding <=> CAST(:vec AS vector) "
                            f"LIMIT :limit"
                        ),
                        params,
                    )
                else:
                    res = await session.execute(
                        text(
                            "SELECT entity_type, entity_id, content, "
                            "1 - (embedding <=> CAST(:vec AS vector)) AS similarity "
                            "FROM embeddings "
                            "WHERE org_id = :org_id "
                            "ORDER BY embedding <=> CAST(:vec AS vector) "
                            "LIMIT :limit"
                        ),
                        {
                            "vec": vec_str,
                            "org_id": org_id,
                            "limit": limit,
                        },
                    )
                rows = list(res.mappings().all())

            return [
                {
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "content": r["content"],
                    "similarity": float(r["similarity"]),
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning("embedding search failed: %s", e)
            return []

    async def _memory_semantic_rows(
        self,
        org_id: str,
        user_id: str,
        query: str,
        now: datetime,
        limit: int,
        query_embedding: Any = None,
    ) -> list[dict] | None:
        try:
            if not await is_pgvector_available():
                return None

            qvec = query_embedding if query_embedding is not None else await embed_query(query)
            if qvec is None:
                return None

            vec_str = _vec_to_pgvector(qvec)

            async with self.session() as session:
                res = await session.execute(
                    text(
                        """SELECT m.type, m.subject, m.content, m.created_at,
                              1 - (e.embedding <=> CAST(:vec AS vector)) AS similarity
                           FROM memory_artifacts m
                           JOIN embeddings e ON e.entity_id = m.id
                             AND e.entity_type = 'memory'
                           WHERE m.org_id = :org_id AND m.user_id = :user_id
                             AND (m.expires_at IS NULL OR m.expires_at > :now)
                           ORDER BY similarity DESC
                           LIMIT :lim"""
                    ),
                    {
                        "vec": vec_str,
                        "org_id": org_id,
                        "user_id": user_id,
                        "now": now,
                        "lim": limit * 3,
                    },
                )
                candidates = list(res.mappings().all())

            if not candidates:
                return None

            scored = []
            for r in candidates:
                sim = float(r["similarity"])
                created = r["created_at"]
                try:
                    created_dt = (
                        datetime.fromisoformat(created) if isinstance(created, str) else created
                    )
                    days_old = max(0, (now - created_dt).total_seconds() / 86400)
                except (ValueError, TypeError):
                    days_old = 30
                recency = math.exp(-0.02 * days_old)
                type_boost = _MEMORY_TYPE_BOOST.get(r["type"], 0.0)
                hybrid_score = 0.6 * sim + 0.3 * recency + type_boost
                scored.append((hybrid_score, dict(r)))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [r for _, r in scored[:limit]]
        except Exception as e:
            logger.debug("Semantic recall unavailable, falling back: %s", e)
            return None

    async def memory_save(
        self, org_id: str, user_id: str, session_id: str, artifacts: list[dict]
    ) -> None:
        if not artifacts:
            return
        now = datetime.now(UTC)
        expires_at = datetime.now(UTC) + timedelta(days=_DEFAULT_MEMORY_TTL_DAYS)
        rows_params: list[dict[str, Any]] = []
        artifact_ids: list[str] = []
        artifact_contents: list[str] = []

        for a in artifacts:
            if not isinstance(a, dict) or not a.get("content"):
                continue
            aid = new_uuid7_str()
            content = (a.get("content") or "")[:1000]
            rows_params.append(
                {
                    "id": aid,
                    "org_id": org_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "atype": (a.get("type") or "entity_fact")[:32],
                    "subject": (a.get("subject") or "general")[:128],
                    "content": content,
                    "tags": json.dumps(a.get("tags") or []),
                    "created_at": now,
                    "expires_at": expires_at,
                }
            )
            artifact_ids.append(aid)
            subject = (a.get("subject") or "general")[:128]
            artifact_contents.append(f"{subject}: {content}")

        if not rows_params:
            return

        ins = text(
            """INSERT INTO memory_artifacts
                   (id, org_id, user_id, session_id, type, subject, content, tags,
                    created_at, expires_at)
               VALUES (:id, :org_id, :user_id, :session_id, :atype, :subject, :content,
                    :tags, :created_at, :expires_at)"""
        )
        async with self.session() as session:
            for rp in rows_params:
                await session.execute(ins, rp)
            await self.end_write_session(session)

        logger.info("Memory: saved %d artifacts for user=%s", len(rows_params), user_id)

        async def _embed() -> None:
            try:
                mgr = get_database_manager()
                if not await mgr.assistant.embedding_is_pgvector_available():
                    return
                vecs = await embed_texts(artifact_contents)
                if vecs is None:
                    return
                items = [
                    (aid, content, vec)
                    for aid, content, vec in zip(
                        artifact_ids, artifact_contents, vecs, strict=False
                    )
                ]
                written = await mgr.assistant.embedding_upsert_batch(org_id, "memory", items)
                if written:
                    logger.debug("Memory embeddings: wrote %d vectors", written)
            except Exception as e:
                logger.warning("Memory embedding failed (non-critical): %s", e)

        t = asyncio.create_task(_embed())
        t.add_done_callback(_memory_embed_done)

    async def memory_recall(
        self,
        org_id: str,
        user_id: str,
        query: str | None = None,
        limit: int = 10,
        query_embedding: Any = None,
    ) -> str:
        now = datetime.now(UTC)

        if query:
            rows = await self._memory_semantic_rows(
                org_id,
                user_id,
                query,
                now,
                limit,
                query_embedding=query_embedding,
            )
            if rows:
                return self._format_memory_rows(rows)

        async with self.session() as session:
            res = await session.execute(
                text(
                    """SELECT type, subject, content, created_at
                       FROM memory_artifacts
                       WHERE org_id = :org_id AND user_id = :user_id
                         AND (expires_at IS NULL OR expires_at > :now)
                       ORDER BY created_at DESC
                       LIMIT :lim"""
                ),
                {
                    "org_id": org_id,
                    "user_id": user_id,
                    "now": now,
                    "lim": limit,
                },
            )
            rows_fb = list(res.mappings().all())

        if not rows_fb:
            return ""
        return self._format_memory_rows([dict(r) for r in rows_fb])

    @staticmethod
    def _format_memory_rows(rows: list[dict]) -> str:
        lines = ["[Memory from previous sessions — background context only, not ground truth]"]
        for r in rows:
            date = (str(r.get("created_at") or ""))[:10]
            lines.append(f"- [{r['type']}] {r['subject']}: {r['content']} ({date})")
        return "\n".join(lines)
