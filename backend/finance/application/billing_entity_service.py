"""Billing entity application service — safe for cross-context import.

Other bounded contexts import from here, never from finance.infrastructure directly.
"""

import logging

from finance.domain.billing_entity import BillingEntity, BillingEntityUpdate
from finance.infrastructure.billing_entity_repo import billing_entity_repo
from shared.infrastructure.db import get_org_id, transaction

logger = logging.getLogger(__name__)


async def ensure_billing_entity(name: str):
    """Get existing billing entity by name, or auto-create a minimal one."""
    return await billing_entity_repo.ensure_billing_entity(name)


async def get_by_name(name: str) -> BillingEntity | None:
    return await billing_entity_repo.get_by_name(name)


async def create_billing_entity(entity: BillingEntity) -> None:
    async with transaction():
        await billing_entity_repo.insert(entity)
    logger.info(
        "billing_entity.created",
        extra={"org_id": get_org_id(), "entity_id": entity.id, "entity_name": entity.name},
    )


async def update_billing_entity(
    entity_id: str, updates: BillingEntityUpdate
) -> BillingEntity | None:
    async with transaction():
        result = await billing_entity_repo.update(entity_id, updates.model_dump(exclude_none=True))
    logger.info(
        "billing_entity.updated",
        extra={"org_id": get_org_id(), "entity_id": entity_id},
    )
    return result
