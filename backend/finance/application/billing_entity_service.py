"""Billing entity application service — safe for cross-context import.

Other bounded contexts import from here, never from finance.infrastructure directly.
"""

import logging

from finance.domain.billing_entity import BillingEntity, BillingEntityUpdate
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _finance():
    return get_database_manager().finance


async def ensure_billing_entity(name: str):
    """Get existing billing entity by name, or auto-create a minimal one."""
    return await _finance().billing_entity_ensure(get_org_id(), name)


async def get_by_name(name: str) -> BillingEntity | None:
    return await _finance().billing_entity_get_by_name(get_org_id(), name)


async def create_billing_entity(entity: BillingEntity) -> None:
    async with transaction():
        await _finance().billing_entity_insert(get_org_id(), entity)
    logger.info(
        "billing_entity.created",
        extra={
            "org_id": get_org_id(),
            "entity_id": entity.id,
            "entity_name": entity.name,
        },
    )


async def update_billing_entity(
    entity_id: str, updates: BillingEntityUpdate
) -> BillingEntity | None:
    async with transaction():
        result = await _finance().billing_entity_update(
            get_org_id(),
            entity_id,
            updates.model_dump(exclude_none=True),
        )
    logger.info(
        "billing_entity.updated",
        extra={"org_id": get_org_id(), "entity_id": entity_id},
    )
    return result
