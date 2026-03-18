"""Document parse service: AI-powered vendor bill/receipt parsing.

Single LLM call extracts AND classifies products. A lightweight DB pass
matches vendor SKUs against the existing catalog.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from assistant.application.llm import generate_with_image, generate_with_pdf
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
    from shared.kernel.types import CurrentUser

logger = logging.getLogger(__name__)

_PARSE_MAX_RETRIES = 2
_PARSE_RETRY_DELAYS = (5, 15)

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
) -> dict:
    """Parse a document (image or PDF) using Claude AI.

    Single LLM call handles both extraction and product classification.
    A lightweight DB pass then matches vendor SKUs against the catalog.

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
                    "Extract all product and vendor information. Classify each product with UOM, department, and variant info. Return only valid JSON.",
                    temp_path,
                    system_instruction=system_prompt,
                )
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        else:
            return generate_with_image(
                "Extract all product and vendor information. Classify each product with UOM, department, and variant info. Return only valid JSON.",
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

    products = extracted.get("products", [])
    for p in products:
        qty = p.get("quantity", 1)
        p.setdefault("ordered_qty", qty)
        p.setdefault("delivered_qty", qty)
        if p["ordered_qty"] is None:
            p["ordered_qty"] = qty
        if p["delivered_qty"] is None:
            p["delivered_qty"] = qty
        p["_ai_parsed"] = True
        if "confidence" in p:
            p["_confidence"] = p.pop("confidence")
        _add_warnings(p)

    if products:
        await _match_vendor_skus(products, extracted.get("vendor_name"))

    return await persist_parsed_document(
        extracted, filename, content_type, len(contents), current_user
    )


_KNOWN_DEPTS = {"PLU", "ELE", "PNT", "LUM", "TOL", "HDW", "GDN", "APP"}


def _add_warnings(product: dict) -> None:
    """Add lightweight validation warnings based on LLM output."""
    warnings: list[str] = []
    confidence = product.get("_confidence", 0)
    if confidence and confidence < 0.7:
        warnings.append("Low confidence classification — verify department and UOM")
    dept = product.get("suggested_department", "")
    if dept and dept.upper() not in _KNOWN_DEPTS:
        warnings.append(f"Unknown department '{dept}' — defaulting to HDW")
    if warnings:
        product["_warnings"] = warnings


async def _match_vendor_skus(products: list[dict], vendor_name: str | None) -> None:
    """Lightweight DB pass: match products against vendor catalog and product families.

    Mutates product dicts in-place, adding _recommendation, _recommendation_reason,
    sku_id, _matched_vendor_item_id, and _family_candidates where applicable.
    """
    vendor_id = None
    if vendor_name:
        try:
            vendor = await find_vendor_by_name(vendor_name)
            if vendor:
                vendor_id = vendor.id
        except Exception as e:
            logger.debug("Vendor lookup during parse failed: %s", e)

    tasks = [_match_single_product(p, vendor_id) for p in products]
    await asyncio.gather(*tasks)


async def _match_single_product(product: dict, vendor_id: str | None) -> None:
    """Try to match a single product against vendor items and product families."""
    sku_id = None
    vendor_item_id = None
    family_candidates: list[dict] = []

    if vendor_id:
        original_sku = product.get("original_sku")
        if original_sku:
            try:
                vi = await find_vendor_item_by_vendor_and_sku_code(vendor_id, original_sku)
                if vi:
                    sku_id = vi.sku_id
                    vendor_item_id = vi.id
            except Exception as e:
                logger.debug("Vendor SKU match failed: %s", e)

        if not sku_id:
            clean_name = product.get("name", "")
            if clean_name:
                try:
                    sku = await find_product_by_name_and_vendor(clean_name, vendor_id)
                    if sku:
                        sku_id = sku.id
                except Exception as e:
                    logger.debug("Name+vendor match failed: %s", e)

    if not sku_id:
        query = product.get("name", "")
        brand = product.get("brand")
        if brand:
            query = f"{brand} {query}"
        if query:
            try:
                families = await list_product_families(search=query, limit=3)
                family_candidates = [
                    {
                        "family_id": f.id,
                        "family_name": f.name,
                        "similarity": 0.5,
                    }
                    for f in families
                ]
            except Exception as e:
                logger.debug("Family search during parse failed: %s", e)

    if sku_id:
        product["sku_id"] = sku_id
        if vendor_item_id:
            product["_matched_vendor_item_id"] = vendor_item_id
            product["_recommendation"] = "link_existing"
            product["_recommendation_reason"] = (
                f"Matched existing SKU via vendor item lookup for '{product.get('name', '')}'."
            )
        else:
            product["_recommendation"] = "link_existing"
            product["_recommendation_reason"] = (
                f"Found existing SKU matching '{product.get('name', '')}'."
            )
    elif family_candidates:
        product["_family_candidates"] = family_candidates
        best = family_candidates[0]
        product["_recommendation"] = "add_variant"
        product["_recommendation_reason"] = (
            f"Found '{best['family_name']}' product family. Consider adding as a new variant."
        )
    else:
        product["_recommendation"] = "create_new"
        product["_recommendation_reason"] = (
            f"No existing match found for '{product.get('name', '')}'. "
            f"Will create as a new product."
        )
