"""Document parse/import routes."""
import asyncio
import json
import logging
import os
import re
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import require_role
from config import GEMINI_AVAILABLE, LLM_SETUP_URL
from services.document_import_service import import_document as do_import_document

from .schemas import DocumentImportRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

_PARSE_MAX_RETRIES = 2
_PARSE_RETRY_DELAYS = (5, 15)  # seconds on rate limit

_DOCUMENT_PARSE_SYSTEM = """You are a document parser for a hardware store. Extract vendor name, date, total, and line items from receipts, invoices, or packing slips.

OUTPUT: return ONLY a single valid JSON object, no other text:
{"vendor_name": "...", "document_date": "YYYY-MM-DD", "total": 0.0, "products": [...]}

Per product:
{"name": "...", "quantity": 1, "ordered_qty": 1, "delivered_qty": 1, "price": 0.0, "cost": 0.0,
 "original_sku": null, "base_unit": "each", "sell_uom": "each", "pack_qty": 1, "suggested_department": "HDW"}

UOM RULES — do NOT default everything to "each":
Allowed: each, case, box, pack, bag, roll, kit, gallon, quart, pint, liter, pound, ounce, foot, meter, yard, sqft

Infer from explicit quantity+unit in name first, then from category keywords:
- "5 Gal Paint" → gallon/gallon/5 | PNT
- "2x4x8 Stud" → foot/foot/8 | LUM
- "1/2 PEX Pipe 100ft" → foot/foot/100 | PLU
- "Screw Box 100ct" → box/box/1 | HDW
- "Wire 12/2 250ft" → foot/foot/250 | ELE
- "Drywall 4x8 Sheet" → sqft/sqft/32 | LUM
- "Concrete 80lb Bag" → pound/pound/80 | HDW
- "Duct Tape Roll" → roll/roll/1 | HDW
- "Ball Valve 1/2" → each/each/1 | PLU
- "Caulk Tube" → each/each/1 | PNT
Use "each" only when no unit or quantity is inferable from the name.

Departments: PLU=plumbing, ELE=electrical, PNT=paint, LUM=lumber, TOL=tools, HDW=hardware, GDN=garden, APP=appliances.
Use effective price after discounts. When ordered/delivered qty unclear, set both equal to quantity."""


@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    _: dict = Depends(require_role("admin", "warehouse_manager")),
):
    """Parse image or PDF with Gemini. Requires LLM_API_KEY."""
    if not GEMINI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=f"AI not configured. Add LLM_API_KEY to backend/.env — get a free key at {LLM_SETUP_URL}",
        )

    try:
        contents = await file.read()
        content_type = (file.content_type or "").lower()
        filename = file.filename or ""
        is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

        def _do_parse():
            if is_pdf:
                from services.llm import generate_with_pdf
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
                    tf.write(contents)
                    temp_path = tf.name
                try:
                    return generate_with_pdf(
                        "Extract all product and vendor information. Return only valid JSON.",
                        temp_path,
                        system_instruction=_DOCUMENT_PARSE_SYSTEM,
                    )
                finally:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                from services.llm import generate_with_image
                return generate_with_image(
                    "Extract all product and vendor information. Return only valid JSON.",
                    contents,
                    system_instruction=_DOCUMENT_PARSE_SYSTEM,
                )

        response = None
        for attempt in range(_PARSE_MAX_RETRIES + 1):
            try:
                response = await asyncio.to_thread(_do_parse)
                break
            except ValueError as e:
                if "rate limit" in str(e).lower() and attempt < _PARSE_MAX_RETRIES:
                    delay = _PARSE_RETRY_DELAYS[attempt]
                    logger.info(f"Rate limit, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                else:
                    raise

        if not response or not str(response).strip():
            raise HTTPException(status_code=500, detail="Gemini returned no content. The document may be unreadable or blocked.")

        json_match = re.search(r"\{[\s\S]*\}", response)
        extracted = json.loads(json_match.group()) if json_match else json.loads(response)

        for p in extracted.get("products", []):
            qty = p.get("quantity", 1)
            if "ordered_qty" not in p or p["ordered_qty"] is None:
                p["ordered_qty"] = qty
            if "delivered_qty" not in p or p["delivered_qty"] is None:
                p["delivered_qty"] = qty

        return extracted
    except json.JSONDecodeError as e:
        logger.error(f"Document parse JSON error: {e}")
        raise HTTPException(status_code=422, detail="Could not parse document data")
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Document parse: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_document(
    data: DocumentImportRequest,
    current_user: dict = Depends(require_role("admin", "warehouse_manager")),
):
    """Import parsed products; create or match vendor."""
    return await do_import_document(
        vendor_name=data.vendor_name,
        products=data.products,
        department_id=data.department_id,
        create_vendor_if_missing=data.create_vendor_if_missing,
        current_user=current_user,
    )
