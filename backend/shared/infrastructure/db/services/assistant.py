"""Assistant agent runs, embeddings, and memory artifacts."""

from __future__ import annotations

from typing import Any

from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services._org_scope import (
    run_with_org,
    scoped_org,
)


class AssistantDatabaseService(DomainDatabaseService):
    async def log_agent_run(self, org_id: str, **kwargs) -> str:
        from assistant.infrastructure import agent_run_repo

        return await run_with_org(
            org_id, agent_run_repo.log_agent_run, **kwargs
        )

    async def list_agent_runs(self, org_id: str, **kwargs) -> list[dict]:
        from assistant.infrastructure import agent_run_repo

        return await run_with_org(org_id, agent_run_repo.list_runs, **kwargs)

    async def agent_run_stats(self, org_id: str, **kwargs) -> dict:
        from assistant.infrastructure import agent_run_repo

        return await run_with_org(org_id, agent_run_repo.get_stats, **kwargs)

    async def agent_session_trace(
        self, org_id: str, session_id: str
    ) -> list[dict]:
        from assistant.infrastructure import agent_run_repo

        return await run_with_org(
            org_id, agent_run_repo.get_session_trace, session_id
        )

    async def agent_validation_summary(self, org_id: str, **kwargs) -> dict:
        from assistant.infrastructure import agent_run_repo

        return await run_with_org(
            org_id, agent_run_repo.get_validation_summary, **kwargs
        )

    async def agent_cost_breakdown(self, org_id: str, **kwargs) -> list[dict]:
        from assistant.infrastructure import agent_run_repo

        return await run_with_org(
            org_id, agent_run_repo.get_cost_breakdown, **kwargs
        )

    async def embedding_is_pgvector_available(self) -> bool:
        from assistant.infrastructure import embedding_store

        return await embedding_store.is_pgvector_available()

    async def embedding_embed_texts(self, texts: list[str]) -> Any:
        from assistant.infrastructure import embedding_store

        return await embedding_store.embed_texts(texts)

    async def embedding_embed_query(self, query: str) -> Any:
        from assistant.infrastructure import embedding_store

        return await embedding_store.embed_query(query)

    async def embedding_upsert(
        self,
        org_id: str,
        entity_type: str,
        entity_id: str,
        content: str,
        embedding: Any,
    ) -> bool:
        from assistant.infrastructure import embedding_store

        return await run_with_org(
            org_id,
            embedding_store.upsert,
            org_id,
            entity_type,
            entity_id,
            content,
            embedding,
        )

    async def embedding_upsert_batch(
        self,
        org_id: str,
        entity_type: str,
        items: list[tuple[str, str, Any]],
    ) -> int:
        from assistant.infrastructure import embedding_store

        return await run_with_org(
            org_id,
            embedding_store.upsert_batch,
            org_id,
            entity_type,
            items,
        )

    async def embedding_search(
        self,
        org_id: str,
        query_embedding: Any,
        entity_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        from assistant.infrastructure import embedding_store

        return await embedding_store.search(
            query_embedding, org_id, entity_types=entity_types, limit=limit
        )

    async def memory_save(
        self, org_id: str, user_id: str, session_id: str, artifacts: list[dict]
    ) -> None:
        from assistant.agents.memory import store as memory_store

        return await run_with_org(
            org_id, memory_store.save, user_id, session_id, artifacts
        )

    async def memory_recall(
        self,
        org_id: str,
        user_id: str,
        query: str | None = None,
        limit: int = 10,
        query_embedding: Any = None,
    ) -> str:
        from assistant.agents.memory import store as memory_store

        async with scoped_org(org_id):
            return await memory_store.recall(
                user_id,
                query=query,
                limit=limit,
                query_embedding=query_embedding,
            )
