"""Document parse routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from documents.application.parse_service import parse_document_with_ai
from documents.application.queries import get_document_by_id
from documents.application.queries import list_documents as query_list_documents
from shared.api.deps import AdminDep

logger = logging.getLogger(__name__)


def _build_run_agent(vendor_id=None, vendor_name=None):
    """Build an agent callable with vendor context captured in closure.

    Returns None if the LLM provider isn't ready, so analyze_products
    skips the agent path cleanly.
    """
    try:
        from assistant.infrastructure.llm import get_provider

        provider = get_provider()
        if not provider.available or provider.provider_name == "stub":
            return None
    except (RuntimeError, ImportError):
        return None

    async def _run(items):
        from assistant.agents.product_analyst.agent import run as agent_run
        from catalog.application.product_intelligence import _run_agent_from_dicts

        analyses_dicts, _usage = await agent_run(
            items,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
        )
        if not analyses_dicts:
            return None
        return await _run_agent_from_dicts(items, analyses_dicts)

    return _run


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
            build_run_agent=_build_run_agent,
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
    return await query_list_documents(
        status=status,
        vendor_name=vendor_name,
        po_id=po_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{doc_id}")
async def get_document(doc_id: str, current_user: AdminDep):
    doc = await get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
