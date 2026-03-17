"""Query router — route messages to unified agent or specialist.

Uses embedding-based routing: example queries per agent, pick nearest.
Falls back to unified when embeddings unavailable or confidence low.
"""

from __future__ import annotations

import logging

import numpy as np

from shared.infrastructure.config import EMBEDDING_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

AgentRoute = str  # "unified" | "procurement" | "trend" | "health" | "analyst"

_ROUTE_EXAMPLES: dict[str, list[str]] = {
    "analyst": [
        "Run a custom query on withdrawals",
        "Analyze the correlation between order size and payment delays",
        "What patterns exist in contractor spending across departments",
        "Compare product margins across different job types",
        "Show me a breakdown I haven't seen before",
        "Dig into the data on vendor pricing trends",
        "Cross-reference invoices with withdrawal patterns",
        "Which products have the widest margin variance by contractor",
        "Deep dive into seasonal purchasing patterns",
        "Ad hoc analysis of payment timing vs invoice size",
    ],
    "procurement": [
        "Which vendor for SKU X?",
        "Reorder plan for low stock",
        "Optimize purchasing",
        "Vendor performance comparison",
        "What should we order next?",
        "Which vendor supplies this product?",
        "Create a procurement plan",
        "Reorder with vendor context",
        "Compare vendor prices for this SKU",
        "Build a purchase order for low stock items",
    ],
    "trend": [
        "Compare revenue to last month",
        "Trend in revenue this quarter",
        "Any anomalies in sales this week?",
        "What's the growth rate?",
        "What changed compared to last week?",
        "Revenue over time by week",
        "Period over period comparison",
        "Time series of withdrawals",
        "Are sales trending up or down?",
        "How did this month compare to the previous month?",
    ],
    "health": [
        "Full business health check",
        "Quarterly business review",
        "Holistic assessment of operations",
        "Give me a comprehensive store review",
        "Overall business health report",
        "Complete store assessment with recommendations",
    ],
    "unified": [
        "Product lookup",
        "Finance summary",
        "Invoice status",
        "Search for product",
        "Low stock list",
        "Revenue and P&L",
        "Who is contractor X?",
        "Show me outstanding balances",
        "How many SKUs do we carry?",
        "What's the margin on plumbing?",
        "Department activity this week",
        "Pending material requests",
        "What should I focus on today?",
        "How's business?",
        "What needs attention?",
        "Good morning, any updates?",
        "Give me a quick overview",
        "Anything urgent?",
        "Weekly summary",
        "Store overview",
    ],
}

_agent_texts: list[str] = []
_agent_labels: list[str] = []
_embeddings: np.ndarray | None = None
_bm25 = None


def _tokenize(text: str) -> list[str]:
    import re

    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1]


async def _embed_batch(texts: list[str], api_key: str) -> np.ndarray | None:
    if not texts:
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        all_vectors: list[list[float]] = []
        batch_size = 256
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = await client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            all_vectors.extend(item.embedding for item in resp.data)
        mat = np.array(all_vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return mat / norms
    except (ValueError, RuntimeError, OSError, TypeError) as e:
        logger.warning("Router embedding batch failed: %s", e)
        return None


async def _embed_query(query: str, api_key: str) -> np.ndarray | None:
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        resp = await client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
        qvec = np.array(resp.data[0].embedding, dtype=np.float32)
        norm = np.linalg.norm(qvec)
        if norm > 0:
            qvec /= norm
        return qvec
    except (ValueError, RuntimeError, OSError, TypeError) as e:
        logger.warning("Router query embedding failed: %s", e)
        return None


def _build_router_index() -> None:
    """Build static index from route examples."""
    global _agent_texts, _agent_labels, _bm25
    _agent_texts = []
    _agent_labels = []
    for agent, examples in _ROUTE_EXAMPLES.items():
        for ex in examples:
            _agent_texts.append(ex)
            _agent_labels.append(agent)
    if not _agent_texts:
        return
    try:
        from rank_bm25 import BM25Okapi

        corpus = [_tokenize(t) for t in _agent_texts]
        _bm25 = BM25Okapi(corpus)
    except ImportError:
        _bm25 = None


async def _ensure_router_index() -> None:
    """Build embeddings if we have API key and haven't yet."""
    global _embeddings
    if _agent_texts and _embeddings is not None:
        return
    if _agent_texts and OPENAI_API_KEY:
        _embeddings = await _embed_batch(_agent_texts, OPENAI_API_KEY)


async def init_router_index() -> None:
    """Pre-build the router index at startup so the first request isn't penalized."""
    if not _agent_texts:
        _build_router_index()
    await _ensure_router_index()
    logger.info(
        "Router index ready: %d examples, embeddings=%s", len(_agent_texts), _embeddings is not None
    )


_GENERIC_GREETINGS = frozenset({"hello", "hi", "hey", "howdy", "yo", "sup", "morning", "afternoon"})

# Minimum cosine similarity to route to a specialist (vs. falling back to unified).
# Unified agent can delegate to specialists via tool calls anyway, so false negatives
# are recovered gracefully — false positives (wrong specialist) are much worse.
_EMBEDDING_THRESHOLD = 0.72
_BM25_THRESHOLD = 3.0


async def route_query(
    user_message: str,
    history: list[dict] | None = None,
    query_embedding: np.ndarray | None = None,
) -> AgentRoute:
    """Route user message to unified or specialist agent. Returns agent label.

    Conservative routing: only routes to a specialist when confidence is high.
    The unified agent can always delegate to specialists via tool calls, so
    defaulting to unified is safe — it just adds one extra LLM turn.

    When *query_embedding* is provided, reuses it for cosine routing instead
    of making a separate OpenAI embedding call.
    """
    query = (user_message or "").strip()
    if not query:
        return "unified"

    q_lower = query.lower()
    if len(query) < 15 or q_lower in _GENERIC_GREETINGS:
        return "unified"

    if history and len(history) >= 2:
        return "unified"

    if not _agent_texts:
        _build_router_index()
    if not _agent_texts:
        return "unified"

    await _ensure_router_index()

    if _embeddings is not None and OPENAI_API_KEY:
        qvec = (
            query_embedding
            if query_embedding is not None
            else await _embed_query(query, OPENAI_API_KEY)
        )
        if qvec is not None:
            scores = np.dot(_embeddings, qvec)
            best_idx = int(np.argmax(scores))
            best_score = float(scores[best_idx])
            route = _agent_labels[best_idx]

            # Only route to specialist if confidence is above threshold
            if route != "unified" and best_score < _EMBEDDING_THRESHOLD:
                logger.debug(
                    "Router: embedded route=%s score=%.3f below threshold, using unified for query=%s",
                    route,
                    best_score,
                    query[:50],
                )
                return "unified"

            logger.debug(
                "Router: embedded route=%s score=%.3f for query=%s",
                route,
                best_score,
                query[:50],
            )
            return route

    if _bm25 is not None:
        tok_q = _tokenize(query)
        if tok_q:
            scores = _bm25.get_scores(tok_q)
            best_idx = int(np.argmax(scores))
            best_score = float(scores[best_idx])
            route = _agent_labels[best_idx]

            if route != "unified" and best_score < _BM25_THRESHOLD:
                logger.debug(
                    "Router: BM25 route=%s score=%.2f below threshold, using unified for query=%s",
                    route,
                    best_score,
                    query[:50],
                )
                return "unified"

            logger.debug(
                "Router: BM25 route=%s score=%.2f for query=%s",
                route,
                best_score,
                query[:50],
            )
            return route

    return "unified"
