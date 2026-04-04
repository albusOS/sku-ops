"""
Domain search index. Uses OpenAI text-embedding-3-small for semantic search when
OPENAI_API_KEY is set; falls back to BM25 keyword search otherwise.

Indexes multiple entity types: SKUs, vendors, purchase orders, and jobs.
Each type has its own embedding matrix for filtered search, plus a unified
cross-entity search mode.

The index is rebuilt automatically via domain event handlers registered on
``InventoryChanged``, ``CatalogUpdated``, etc. No background task is required.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from purchasing.application.queries import list_pos
from shared.infrastructure.config import EMBEDDING_MODEL, OPENAI_API_KEY
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.logging_config import org_id_var

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small; adjust if switching to larger model


class SkuLike(Protocol):
    name: str
    description: str
    category_name: str
    sku: str
    organization_id: str


@dataclass
class SearchResult:
    entity_type: str
    entity_id: str
    text: str
    score: float
    data: dict = field(default_factory=dict)


_indexes: dict[str, "DomainSearchIndex"] = {}


def _tokenize(text: str) -> list[str]:
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1]


def _sku_text(p: SkuLike) -> str:
    parts = [
        p.name or "",
        p.description or "",
        p.category_name or "",
        p.sku or "",
    ]
    return " ".join(filter(None, parts))


async def _embed_batch(texts: list[str], api_key: str) -> np.ndarray | None:
    """Embed a list of texts and return normalized vectors."""
    if not texts:
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        all_vectors: list[list[float]] = []
        batch_size = 500
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = await client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            all_vectors.extend(item.embedding for item in resp.data)
        mat = np.array(all_vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return mat / norms
    except (ValueError, RuntimeError, OSError, TypeError) as e:
        logger.warning("Embedding batch failed: %s", e)
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
        logger.warning("Query embedding failed: %s", e)
        return None


@dataclass
class _EntitySlice:
    """One entity type's portion of the index."""

    entity_type: str
    ids: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    data: list[dict] = field(default_factory=list)
    embeddings: np.ndarray | None = None
    bm25: object | None = None


class DomainSearchIndex:
    def __init__(self):
        self._skus: list[SkuLike] = []
        self._sku_embeddings: np.ndarray | None = None
        self._sku_bm25 = None
        self._slices: dict[str, _EntitySlice] = {}

    async def rebuild(self) -> None:
        """Rebuild all entity indexes."""
        await self._rebuild_skus()
        await self._rebuild_vendors()
        await self._rebuild_pos()
        await self._rebuild_jobs()

    # ── SKUs (primary, backward-compatible) ───────────────────────────────

    async def _rebuild_skus(self) -> None:
        skus = await get_database_manager().catalog.list_skus(get_org_id(), limit=10000)
        if not skus:
            self._skus = []
            self._sku_embeddings = None
            self._sku_bm25 = None
            return

        self._skus = skus
        texts = [_sku_text(s) for s in skus]

        if OPENAI_API_KEY:
            self._sku_embeddings = await _embed_batch(texts, OPENAI_API_KEY)
            if self._sku_embeddings is None:
                self._build_sku_bm25(skus)
            else:
                self._sku_bm25 = None
        else:
            self._build_sku_bm25(skus)

        s = _EntitySlice(
            entity_type="sku",
            ids=[sk.sku for sk in skus],
            texts=texts,
            data=[{"sku": sk.sku, "name": sk.name, "department": sk.category_name} for sk in skus],
            embeddings=self._sku_embeddings,
        )
        self._slices["sku"] = s
        self._slices["product"] = s  # backward compat for entity_graph "product" alias
        logger.info("SKU index: %d items", len(skus))

    def _build_sku_bm25(self, skus: list[SkuLike]) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank-bm25 not installed — keyword search unavailable")
            return
        corpus = [_tokenize(_sku_text(s)) or ["_"] for s in skus]
        self._sku_bm25 = BM25Okapi(corpus)

    # ── Vendors ───────────────────────────────────────────────────────────

    async def _rebuild_vendors(self) -> None:
        try:
            vendors = await get_database_manager().catalog.list_vendors(get_org_id())
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning("Vendor index build failed: %s", e)
            return

        if not vendors:
            return

        texts = [
            f"{v.name} {v.contact_name} {v.email} {v.phone} {v.address}".strip() for v in vendors
        ]
        embeddings = await _embed_batch(texts, OPENAI_API_KEY) if OPENAI_API_KEY else None

        self._slices["vendor"] = _EntitySlice(
            entity_type="vendor",
            ids=[v.id for v in vendors],
            texts=texts,
            data=[{"id": v.id, "name": v.name, "contact": v.contact_name} for v in vendors],
            embeddings=embeddings,
        )
        logger.info("Vendor index: %d items", len(vendors))

    # ── Purchase orders ───────────────────────────────────────────────────

    async def _rebuild_pos(self) -> None:
        try:
            pos = await list_pos()
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning("PO index build failed: %s", e)
            return

        if not pos:
            return

        texts = []
        ids = []
        data_list = []
        for po in pos[:500]:
            doc_date = po.document_date or ""
            text = f"{po.vendor_name} PO {po.id[:8]} {doc_date} {po.notes or ''} status:{po.status}".strip()
            texts.append(text)
            ids.append(po.id)
            data_list.append(
                {
                    "id": po.id,
                    "vendor_name": po.vendor_name,
                    "date": po.document_date,
                    "total": po.total,
                    "status": po.status,
                }
            )

        embeddings = await _embed_batch(texts, OPENAI_API_KEY) if OPENAI_API_KEY else None

        self._slices["purchase_order"] = _EntitySlice(
            entity_type="purchase_order",
            ids=ids,
            texts=texts,
            data=data_list,
            embeddings=embeddings,
        )
        logger.info("PO index: %d items", len(texts))

    # ── Jobs (from withdrawals) ───────────────────────────────────────────

    async def _rebuild_jobs(self) -> None:
        try:
            from pydantic import ValidationError

            from shared.infrastructure.db import get_org_id
            from shared.infrastructure.db.base import get_database_manager

            withdrawals = await get_database_manager().operations.list_withdrawals(
                get_org_id(), limit=2000
            )
        except (RuntimeError, OSError, ValueError, Exception) as e:
            logger.warning("Job index build failed: %s", e)
            return

        job_map: dict[str, dict] = {}
        skipped = 0
        for w in withdrawals:
            try:
                jid = w.job_id or ""
                if not jid or jid in job_map:
                    continue
                item_names = ", ".join(i.name for i in (w.items or [])[:5])
                job_map[jid] = {
                    "job_id": jid,
                    "service_address": w.service_address or "",
                    "contractor": w.contractor_name or "",
                    "items_sample": item_names,
                }
            except (ValidationError, AttributeError, TypeError) as e:
                skipped += 1
                if skipped <= 3:
                    logger.warning("Skipping malformed withdrawal in job index: %s", e)
        if skipped:
            logger.warning("Job index: skipped %d malformed withdrawal(s)", skipped)

        if not job_map:
            return

        texts = []
        ids = []
        data_list = []
        for jid, jdata in list(job_map.items())[:500]:
            text = f"Job {jid} {jdata['service_address']} {jdata['contractor']} {jdata['items_sample']}".strip()
            texts.append(text)
            ids.append(jid)
            data_list.append(jdata)

        embeddings = await _embed_batch(texts, OPENAI_API_KEY) if OPENAI_API_KEY else None

        self._slices["job"] = _EntitySlice(
            entity_type="job",
            ids=ids,
            texts=texts,
            data=data_list,
            embeddings=embeddings,
        )
        logger.info("Job index: %d items", len(texts))

    # ── Search methods ────────────────────────────────────────────────────

    async def search_semantic(
        self, query: str, limit: int = 10, api_key: str = ""
    ) -> list[SkuLike]:
        """SKU semantic search."""
        if self._sku_embeddings is None or not self._skus:
            return self.search_bm25(query, limit)
        qvec = await _embed_query(query, api_key or OPENAI_API_KEY or "")
        if qvec is None:
            return self.search_bm25(query, limit)
        scores = self._sku_embeddings @ qvec
        top_idx = np.argsort(scores)[::-1][:limit]
        return [self._skus[i] for i in top_idx if scores[i] > 0.2]

    async def search_entity(
        self, query: str, entity_type: str, limit: int = 10
    ) -> list[SearchResult]:
        """Semantic search over a specific entity type."""
        s = self._slices.get(entity_type)
        if not s or not s.texts:
            return self._bm25_entity_search(query, entity_type, limit)
        if s.embeddings is None:
            return self._bm25_entity_search(query, entity_type, limit)

        qvec = await _embed_query(query, OPENAI_API_KEY or "")
        if qvec is None:
            return self._bm25_entity_search(query, entity_type, limit)

        scores = s.embeddings @ qvec
        top_idx = np.argsort(scores)[::-1][:limit]
        results = []
        for i in top_idx:
            if scores[i] < 0.15:
                break
            results.append(
                SearchResult(
                    entity_type=entity_type,
                    entity_id=s.ids[i],
                    text=s.texts[i],
                    score=float(scores[i]),
                    data=s.data[i],
                )
            )
        return results

    def _bm25_entity_search(self, query: str, entity_type: str, limit: int) -> list[SearchResult]:
        """BM25 fallback for entity search."""
        s = self._slices.get(entity_type)
        if not s or not s.texts:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            return []
        corpus = [_tokenize(t) or ["_"] for t in s.texts]
        bm25 = BM25Okapi(corpus)
        bm25_scores = bm25.get_scores(tokens)
        ranked = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked[:limit]:
            if score <= 0:
                break
            results.append(
                SearchResult(
                    entity_type=entity_type,
                    entity_id=s.ids[idx],
                    text=s.texts[idx],
                    score=float(score),
                    data=s.data[idx],
                )
            )
        return results

    def search_bm25(self, query: str, limit: int = 10) -> list[SkuLike]:
        if not self._sku_bm25 or not self._skus:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._sku_bm25.get_scores(tokens)
        ranked = sorted(
            ((score, s) for score, s in zip(scores, self._skus, strict=False) if score > 0),
            key=lambda x: x[0],
            reverse=True,
        )
        return [s for _, s in ranked[:limit]]

    def search(self, query: str, limit: int = 10) -> list[SkuLike]:
        """Sync BM25 search — keyword fallback."""
        return self.search_bm25(query, limit)

    def is_ready(self) -> bool:
        return bool(self._skus)


SkuSearchIndex = DomainSearchIndex
ProductSearchIndex = DomainSearchIndex  # backward-compatible alias


async def get_index() -> DomainSearchIndex:
    org_id = get_org_id()
    if org_id not in _indexes:
        index = DomainSearchIndex()
        _indexes[org_id] = index
        await index.rebuild()
    return _indexes[org_id]


async def refresh_index(org_id: str | None = None) -> None:
    oid = org_id or get_org_id()
    index = _indexes.get(oid)
    if index is None:
        index = DomainSearchIndex()
        _indexes[oid] = index
    await index.rebuild()


# ── Debounced rebuild ────────────────────────────────────────────────────────
# Multiple InventoryChanged / CatalogChanged events often fire in quick
# succession (e.g. a 5-item withdrawal emits 5 events). Without debouncing,
# each event triggers a full rebuild: 4 DB queries + 4 embedding batches.
# The debouncer coalesces events within a window so only one rebuild runs.

import asyncio

_DEBOUNCE_SECONDS = 5.0
_pending_rebuilds: dict[str, asyncio.Task] = {}


async def _debounced_rebuild(org_id: str, trigger: str) -> None:
    """Schedule a rebuild for org_id, debounced by _DEBOUNCE_SECONDS.

    If another event arrives for the same org before the timer fires,
    the previous timer is cancelled and a new one starts.
    """
    existing = _pending_rebuilds.get(org_id)
    if existing and not existing.done():
        existing.cancel()

    async def _do_rebuild() -> None:
        await asyncio.sleep(_DEBOUNCE_SECONDS)
        _pending_rebuilds.pop(org_id, None)
        try:
            org_id_var.set(org_id)
            await refresh_index(org_id)
            logger.info("Search index rebuilt for org=%s after %s", org_id, trigger)
        except (RuntimeError, OSError, ValueError) as exc:
            logger.warning("Search index rebuild failed for org=%s: %s", org_id, exc)

    _pending_rebuilds[org_id] = asyncio.create_task(_do_rebuild())


def _register_invalidation_handler() -> None:
    """Register search index invalidation as domain event handlers.

    Called once at module import time. Skipped in test environments.
    """
    from shared.infrastructure.config import is_test
    from shared.infrastructure.domain_events import on
    from shared.kernel.domain_events import CatalogChanged, InventoryChanged

    if is_test:
        return

    @on(InventoryChanged)
    async def _invalidate_on_inventory_changed(event: InventoryChanged) -> None:
        await _debounced_rebuild(event.org_id, "InventoryChanged")

    @on(CatalogChanged)
    async def _invalidate_on_catalog_changed(event: CatalogChanged) -> None:
        await _debounced_rebuild(event.org_id, "CatalogChanged")


_register_invalidation_handler()
