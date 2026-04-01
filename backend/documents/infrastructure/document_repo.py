"""Document repository — delegates to DocumentsDatabaseService."""

from documents.domain.document import Document
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def insert(doc: Document) -> None:
    db = get_database_manager()
    await db.documents.insert_document(doc)


async def get_by_id(doc_id: str) -> Document | None:
    db = get_database_manager()
    return await db.documents.get_document_by_id(doc_id, get_org_id())


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


async def update_status(
    doc_id: str, status: str, po_id: str | None = None
) -> None:
    db = get_database_manager()
    await db.documents.update_document_status(
        doc_id, get_org_id(), status, po_id=po_id
    )


class DocumentRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_documents = staticmethod(list_documents)
    update_status = staticmethod(update_status)


document_repo = DocumentRepo()
