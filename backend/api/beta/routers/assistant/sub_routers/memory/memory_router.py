"""Memory feedback endpoint for product intelligence corrections."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from shared.api.deps import CurrentUserDep
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _db_assistant():
    return get_database_manager().assistant


router = APIRouter(prefix="/memory", tags=["assistant-memory"])


class ProductCorrection(BaseModel):
    item_name: str
    field: str
    original_value: str | None = None
    corrected_value: str | None = None


class CorrectionPayload(BaseModel):
    corrections: list[ProductCorrection]
    vendor_name: str | None = None


@router.post("/corrections")
async def save_corrections(body: CorrectionPayload, user: CurrentUserDep) -> dict:
    """Save user corrections to agent recommendations as memory artifacts.

    Called by the frontend when the user overrides agent-proposed fields
    during PO creation (department, UOM, match rejection, etc.).
    """
    if not body.corrections:
        return {"saved": 0}

    session_id = new_uuid7_str()
    artifacts = []
    for c in body.corrections:
        subject = f"product:{c.item_name[:80]}"
        if c.original_value and c.corrected_value:
            content = (
                f"User corrected {c.field} from '{c.original_value}' to '{c.corrected_value}' "
                f"on product '{c.item_name}'"
            )
        elif c.corrected_value:
            content = f"User set {c.field} to '{c.corrected_value}' on product '{c.item_name}'"
        else:
            content = f"User rejected {c.field} suggestion on product '{c.item_name}'"

        if body.vendor_name:
            content += f" (vendor: {body.vendor_name})"

        artifacts.append(
            {
                "type": "entity_fact",
                "subject": subject,
                "content": content,
                "tags": ["product_correction", c.field],
            }
        )

    await _db_assistant().memory_save(get_org_id(), user.id, session_id, artifacts)
    logger.info("Saved %d product corrections for user=%s", len(artifacts), user.id)
    return {"saved": len(artifacts)}
