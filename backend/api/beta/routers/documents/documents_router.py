"""Document parse routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from documents.application.parse_service import parse_document_with_ai
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/parse")
async def parse_document(
    file: Annotated[UploadFile, File(...)],
    current_user: AdminDep,
    use_ai: bool = False,
):
    """Parse image or PDF. use_ai=true uses Claude (requires ANTHROPIC_API_KEY); default uses free OCR."""
    contents = await file.read()
    content_type = (file.content_type or "").lower()
    filename = file.filename or ""

    if not use_ai:
        raise HTTPException(
            status_code=501,
            detail="OCR parsing is not available. Use use_ai=true with an Anthropic API key.",
        )

    try:
        return await parse_document_with_ai(
            contents,
            content_type,
            filename,
            current_user,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        detail = str(e)
        if "no content" in detail.lower():
            raise HTTPException(status_code=500, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e
    except Exception as e:
        logger.exception("Document parse error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("")
async def list_documents(
    current_user: AdminDep,
    status: str | None = None,
    vendor_name: str | None = None,
    po_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """List uploaded/parsed documents."""
    return await get_database_manager().documents.list_documents(
        get_org_id(),
        status=status,
        vendor_name=vendor_name,
        po_id=po_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{doc_id}")
async def get_document(doc_id: str, current_user: AdminDep):
    doc = await get_database_manager().documents.get_document_by_id(
        doc_id, get_org_id()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
