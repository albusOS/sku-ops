"""Document parse service: AI-powered vendor bill/receipt parsing and persistence."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from assistant.application.llm import generate_with_image, generate_with_pdf
from assistant.application.llm_facade import get_generate_text
from catalog.application.product_intelligence import analyze_products
from catalog.application.queries import (
    find_product_by_name_and_vendor,
    find_vendor_by_name,
    find_vendor_item_by_vendor_and_sku_code,
    list_product_families,
)
from documents.domain.document import Document
from documents.infrastructure.document_repo import document_repo
from shared.infrastructure.config import ANTHROPIC_AVAILABLE, LLM_SETUP_URL
from shared.infrastructure.db import get_org_id, transaction

if TYPE_CHECKING:
    from catalog.domain.product_analysis import ProductAnalysis
    from shared.kernel.types import CurrentUser

logger = logging.getLogger(__name__)

_PARSE_MAX_RETRIES = 2
_PARSE_RETRY_DELAYS = (5, 15)


async def _search_families(query: str) -> list[dict]:
    """Adapter: search product families by name for the batch enrichment path."""
    try:
        families = await list_product_families(search=query, limit=3)
        return [{"id": f.id, "name": f.name, "similarity": 0.5} for f in families]
    except Exception as e:
        logger.warning("Family search during parse failed: %s", e)
        return []


_PROMPT_DIR = Path(__file__).resolve().parent.parent / "api"
_DOCUMENT_PARSE_SYSTEM: str | None = None


def _get_parse_system_prompt() -> str:
    global _DOCUMENT_PARSE_SYSTEM
    if _DOCUMENT_PARSE_SYSTEM is None:
        _DOCUMENT_PARSE_SYSTEM = (_PROMPT_DIR / "document_parse_prompt.md").read_text(
            encoding="utf-8"
        )
    return _DOCUMENT_PARSE_SYSTEM


async def persist_parsed_document(
    extracted: dict,
    filename: str,
    content_type: str,
    file_size: int,
    current_user: CurrentUser,
) -> dict:
    """Save parsed document to the archive and return the extracted data with document_id."""
    doc = Document(
        filename=filename,
        document_type="other",
        vendor_name=extracted.get("vendor_name"),
        file_hash=hashlib.sha256(filename.encode()).hexdigest()[:16],
        file_size=file_size,
        mime_type=content_type,
        parsed_data=json.dumps(extracted),
        status="parsed",
        uploaded_by_id=current_user.id,
        organization_id=get_org_id(),
    )
    async with transaction():
        await document_repo.insert(doc)
    extracted["document_id"] = doc.id
    logger.info(
        "document.parsed_and_persisted",
        extra={"org_id": get_org_id(), "document_id": doc.id, "doc_filename": filename},
    )
    return extracted


async def parse_document_with_ai(
    contents: bytes,
    content_type: str,
    filename: str,
    current_user: CurrentUser,
    *,
    build_run_agent=None,
) -> dict:
    """Parse a document (image or PDF) using Claude AI.

    Returns the extracted structured data with a document_id after persisting.
    Raises ValueError on rate limit exhaustion or parse failure.
    Raises RuntimeError if AI is not configured.
    """
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError(
            f"AI not configured. Add ANTHROPIC_API_KEY to backend/.env — get a key at {LLM_SETUP_URL}"
        )

    system_prompt = _get_parse_system_prompt()
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

    def _do_parse():
        if is_pdf:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
                tf.write(contents)
                temp_path = tf.name
            try:
                return generate_with_pdf(
                    "Extract all product and vendor information. Return only valid JSON.",
                    temp_path,
                    system_instruction=system_prompt,
                )
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        else:
            return generate_with_image(
                "Extract all product and vendor information. Return only valid JSON.",
                contents,
                system_instruction=system_prompt,
            )

    response = None
    for attempt in range(_PARSE_MAX_RETRIES + 1):
        try:
            response = await asyncio.to_thread(_do_parse)
            break
        except ValueError as e:
            err_lower = str(e).lower()
            if (
                "rate limit" in err_lower or "overloaded" in err_lower
            ) and attempt < _PARSE_MAX_RETRIES:
                delay = _PARSE_RETRY_DELAYS[attempt]
                logger.info("Rate limit, retrying in %ss (attempt %d)", delay, attempt + 1)
                await asyncio.sleep(delay)
            else:
                raise

    if not response or not str(response).strip():
        raise ValueError("Claude returned no content. The document may be unreadable or blocked.")

    json_match = re.search(r"\{[\s\S]*\}", response)
    try:
        extracted = json.loads(json_match.group()) if json_match else json.loads(response)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(
            "Failed to parse Claude response as JSON: %s\nResponse preview: %.200s", e, response
        )
        raise ValueError(
            "Could not extract structured data from the document. "
            "The file may be too complex, low quality, or not a recognized vendor bill format."
        ) from e

    for p in extracted.get("products", []):
        qty = p.get("quantity", 1)
        p.setdefault("ordered_qty", qty)
        p.setdefault("delivered_qty", qty)
        if p["ordered_qty"] is None:
            p["ordered_qty"] = qty
        if p["delivered_qty"] is None:
            p["delivered_qty"] = qty
        p["_ai_parsed"] = True

    # Run product intelligence pipeline to enrich raw extraction.
    # Resolve vendor context so the agent/batch path can match against existing catalog.
    products = extracted.get("products", [])
    if products:
        vendor_name = extracted.get("vendor_name")
        vendor_id = None
        if vendor_name:
            try:
                vendor = await find_vendor_by_name(vendor_name)
                if vendor:
                    vendor_id = vendor.id
            except Exception as e:
                logger.debug("Vendor lookup during parse failed: %s", e)

        run_agent = None
        if build_run_agent:
            run_agent = build_run_agent(vendor_id, vendor_name)

        try:
            analyses = await analyze_products(
                products,
                generate_text=get_generate_text(),
                vendor_id=vendor_id,
                search_families=_search_families,
                find_by_vendor_sku=find_vendor_item_by_vendor_and_sku_code if vendor_id else None,
                find_by_name_and_vendor=find_product_by_name_and_vendor if vendor_id else None,
                run_agent=run_agent,
            )
            _apply_analyses_to_products(products, analyses)
        except Exception as e:
            logger.warning(
                "Product intelligence enrichment failed (%s: %s) — returning raw extraction",
                type(e).__name__,
                e,
            )

    return await persist_parsed_document(
        extracted, filename, content_type, len(contents), current_user
    )


def _apply_analyses_to_products(products: list[dict], analyses: list[ProductAnalysis]) -> None:
    """Merge ProductAnalysis results back into the raw product dicts."""
    for p, analysis in zip(products, analyses, strict=False):
        ap = analysis.product
        p["name"] = ap.clean_name
        p["base_unit"] = ap.base_unit
        p["sell_uom"] = ap.sell_uom
        p["pack_qty"] = ap.pack_qty
        p["purchase_uom"] = ap.purchase_uom
        p["purchase_pack_qty"] = ap.purchase_pack_qty
        p["suggested_department"] = ap.suggested_department
        if ap.original_sku:
            p["original_sku"] = ap.original_sku
        if ap.brand:
            p["brand"] = ap.brand
        if ap.variant_label:
            p["variant_label"] = ap.variant_label
        if ap.variant_attrs:
            p["variant_attrs"] = ap.variant_attrs
        if ap.specifications:
            p["specifications"] = ap.specifications
        p["_confidence"] = ap.confidence
        p["_recommendation"] = analysis.recommendation
        p["_recommendation_reason"] = analysis.recommendation_reason

        if analysis.family_candidates:
            p["_family_candidates"] = [asdict(fc) for fc in analysis.family_candidates]
        if analysis.matched_sku_id:
            p["sku_id"] = analysis.matched_sku_id
        if analysis.matched_vendor_item_id:
            p["_matched_vendor_item_id"] = analysis.matched_vendor_item_id
        if analysis.warnings:
            p["_warnings"] = analysis.warnings
