"""Context assembly pipeline — builds rich context for agents before dispatch.

Combines four sources into a single structured context block:
  1. Vector search — what entities match the user's query
  2. Entity graph — what's connected to those entities
  3. Semantic memory — relevant facts from prior sessions
  4. Session state — active entities and topic from current session

The assembled context is injected as a system message before the agent runs,
giving it structural awareness without needing discovery tool calls.

Used by both the unified agent and specialist agents.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import numpy as np

from assistant.application.entity_graph import GraphContext, multi_neighbors
from assistant.application.session_state import EntityRef, SessionState
from assistant.infrastructure.embedding_store import (
    embed_query,
    is_pgvector_available,
)
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _db_assistant():
    return get_database_manager().assistant


@dataclass
class AssembledContext:
    """Rich context assembled from multiple sources."""

    entity_hits: list[dict] = field(default_factory=list)
    graph_contexts: list[GraphContext] = field(default_factory=list)
    memory_context: str = ""
    active_entities: list[EntityRef] = field(default_factory=list)
    last_topic: str | None = None

    def format_for_agent(self) -> str | None:
        """Format as a concise context block for system prompt injection.

        Returns None if no meaningful context was assembled.
        """
        sections: list[str] = []

        # Graph context (entity + connections)
        if self.graph_contexts:
            entity_lines = []
            for gc in self.graph_contexts[:5]:
                entity_lines.append(gc.format_for_agent(max_neighbors=5))
            sections.append("[Relevant entities]\n" + "\n\n".join(entity_lines))

        # Semantic entity hits without graph (fallback)
        elif self.entity_hits:
            hit_lines = []
            for h in self.entity_hits[:5]:
                hit_lines.append(
                    f"- [{h['entity_type']}] {h.get('content', h['entity_id'])} "
                    f"(relevance: {h.get('similarity', 0):.2f})"
                )
            sections.append("[Potentially relevant entities]\n" + "\n".join(hit_lines))

        # Memory context
        if self.memory_context:
            sections.append(self.memory_context)

        # Active session entities
        if self.active_entities:
            active_lines = [f"- {e.type}: {e.label} ({e.id[:8]})" for e in self.active_entities[:5]]
            sections.append("[Active in this session]\n" + "\n".join(active_lines))

        # Last topic
        if self.last_topic:
            sections.append(f"[Current topic]: {self.last_topic}")

        if not sections:
            return None
        return "\n\n".join(sections)


async def assemble_context(
    query: str,
    user_id: str,
    session_state: SessionState | None = None,
    include_graph: bool = True,
    include_memory: bool = True,
    max_entity_hits: int = 5,
    max_memory_items: int = 8,
    query_embedding: np.ndarray | None = None,
) -> AssembledContext:
    """Build rich context for an agent call.

    Runs embedding, vector search, graph traversal, and memory recall
    concurrently where possible.  Each source is independent — failures
    in one don't affect the others.

    When *query_embedding* is provided it's reused; otherwise the embedding
    is computed inside this function so the caller doesn't have to block on
    it before kicking off context assembly.
    """
    ctx = AssembledContext()

    if session_state:
        ctx.active_entities = session_state.entities[:5]
        ctx.last_topic = session_state.last_topic

    # Compute embedding inline when not pre-supplied, so the caller can
    # fire context assembly as a task immediately (no serial await).
    if query_embedding is None and (max_entity_hits > 0 or include_memory):
        query_embedding = await _get_query_embedding(query)

    tasks = {}

    if max_entity_hits > 0:
        tasks["vector"] = asyncio.create_task(
            _vector_search(query, max_entity_hits, query_embedding=query_embedding)
        )

    if include_memory:
        tasks["memory"] = asyncio.create_task(
            _recall_memory(
                user_id,
                query,
                max_memory_items,
                query_embedding=query_embedding,
            )
        )

    entity_hits = await tasks["vector"] if "vector" in tasks else []
    ctx.entity_hits = entity_hits

    if include_graph and (entity_hits or ctx.active_entities):
        graph_entities: list[tuple[str, str]] = []
        for h in entity_hits[:3]:
            graph_entities.append((h["entity_type"], h["entity_id"]))
        for e in ctx.active_entities[:2]:
            pair = (e.type, e.id)
            if pair not in graph_entities:
                graph_entities.append(pair)

        if graph_entities:
            try:
                ctx.graph_contexts = await multi_neighbors(graph_entities)
            except Exception as e:
                logger.debug("Graph traversal failed (non-critical): %s", e)

    if "memory" in tasks:
        try:
            ctx.memory_context = await tasks["memory"]
        except Exception as e:
            logger.debug("Memory recall failed (non-critical): %s", e)

    return ctx


async def _get_query_embedding(query: str):
    """Compute a single embedding vector for the user query.

    Returns None if embedding service is unavailable.
    """
    if not query or not query.strip():
        return None
    try:
        return await embed_query(query)
    except Exception as e:
        logger.debug("Query embedding failed (non-critical): %s", e)
        return None


async def _vector_search(
    query: str,
    limit: int,
    query_embedding: np.ndarray | None = None,
) -> list[dict]:
    """Search embeddings for relevant entities. Returns empty list on failure."""
    try:
        if not await is_pgvector_available():
            return []

        qvec = query_embedding if query_embedding is not None else await embed_query(query)
        if qvec is None:
            return []

        org_id = get_org_id()
        hits = await _db_assistant().embedding_search(
            org_id,
            qvec,
            entity_types=["sku", "vendor", "purchase_order", "job"],
            limit=limit,
        )
        return [h for h in hits if h.get("similarity", 0) > 0.25]
    except Exception as e:
        logger.debug("Vector search failed (non-critical): %s", e)
        return []


async def _recall_memory(
    user_id: str,
    query: str,
    limit: int,
    query_embedding: np.ndarray | None = None,
) -> str:
    """Recall semantic memory. Returns empty string on failure."""
    try:
        return await _db_assistant().memory_recall(
            get_org_id(),
            user_id,
            query=query,
            limit=limit,
            query_embedding=query_embedding,
        )
    except Exception as e:
        logger.debug("Memory recall failed (non-critical): %s", e)
        return ""
