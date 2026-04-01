"""Document application queries — safe for cross-context import.

API and other bounded contexts import from here, never from documents.infrastructure directly.
Thin delegation layer that decouples consumers from infrastructure details.
"""

from documents.domain.document import Document
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def list_documents(
    status: str | None = None,
    vendor_name: str | None = None,
    po_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Document]:
    db = get_database_manager()
    return await db.documents.list_documents(
        get_org_id(),
        status=status,
        vendor_name=vendor_name,
        po_id=po_id,
        limit=limit,
        offset=offset,
    )


async def get_document_by_id(doc_id: str) -> Document | None:
    db = get_database_manager()
    return await db.documents.get_document_by_id(doc_id, get_org_id())
