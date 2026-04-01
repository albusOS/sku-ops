"""Persistent embedding store — pgvector-backed with in-memory fallback.

Consolidates all embedding operations (previously duplicated in search.py,
query_router.py, tool_index.py) into a single module.  Embeddings are
persisted in the ``embeddings`` table when pgvector is available, eliminating
the costly startup rebuild.  Falls back to transient NumPy matrices otherwise.

Public API:
    embed_texts(texts)       — batch embed, return (N, 1536) ndarray
    embed_query(query)       — single query embed, return (1536,) ndarray
    upsert(org, type, id, content, vec) — persist to DB with content-hash diffing
    search(query_vec, org, types, limit)  — ANN search via pgvector
    is_pgvector_available()  — whether persistent storage is usable
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np

from shared.infrastructure.config import EMBEDDING_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536

# ── Module state ──────────────────────────────────────────────────────────────
_pgvector_ok: bool | None = None  # None = not yet checked


async def is_pgvector_available() -> bool:
    """Check (and cache) whether the embeddings table exists and is usable."""
    global _pgvector_ok
    if _pgvector_ok is not None:
        return _pgvector_ok
    try:
        from shared.infrastructure.db import sql_execute

        res = await sql_execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'embeddings' LIMIT 1",
            read_only=True,
            max_rows=1,
        )
        _pgvector_ok = len(res.rows) > 0
    except Exception:
        _pgvector_ok = False
    logger.info("pgvector available: %s", _pgvector_ok)
    return _pgvector_ok


def reset_pgvector_check() -> None:
    """Reset the cached pgvector check (useful for tests)."""
    global _pgvector_ok
    _pgvector_ok = None


# ── Embedding generation (OpenAI) ────────────────────────────────────────────


def _normalize(mat: np.ndarray) -> np.ndarray:
    """L2-normalize rows so dot product == cosine similarity."""
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return mat / norms


async def embed_texts(
    texts: list[str],
    api_key: str | None = None,
    batch_size: int = 500,
) -> np.ndarray | None:
    """Embed a list of texts via OpenAI. Returns (N, 1536) normalized ndarray."""
    key = api_key or OPENAI_API_KEY
    if not key or not texts:
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=key)
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = await client.embeddings.create(
                model=EMBEDDING_MODEL, input=batch
            )
            all_vectors.extend(item.embedding for item in resp.data)
        mat = np.array(all_vectors, dtype=np.float32)
        return _normalize(mat)
    except (ValueError, RuntimeError, OSError, TypeError) as e:
        logger.warning("embed_texts failed: %s", e)
        return None


async def embed_query(
    query: str,
    api_key: str | None = None,
) -> np.ndarray | None:
    """Embed a single query string. Returns (1536,) normalized vector."""
    key = api_key or OPENAI_API_KEY
    if not key or not query:
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=key)
        resp = await client.embeddings.create(
            model=EMBEDDING_MODEL, input=[query]
        )
        qvec = np.array(resp.data[0].embedding, dtype=np.float32)
        norm = np.linalg.norm(qvec)
        if norm > 0:
            qvec /= norm
        return qvec
    except (ValueError, RuntimeError, OSError, TypeError) as e:
        logger.warning("embed_query failed: %s", e)
        return None


# ── Content hashing ───────────────────────────────────────────────────────────


def content_hash(text: str) -> str:
    """SHA-256 hash of text content. Used to skip re-embedding unchanged content."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ── pgvector literal formatting (used by AssistantDatabaseService) ───────────


def _vec_to_pgvector(vec: np.ndarray) -> str:
    """Format a numpy vector as a pgvector literal string."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
