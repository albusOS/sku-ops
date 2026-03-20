"""Product intelligence pipeline: batch LLM decomposition + parallel DB matching.

Batch path: Single LLM call for decomposition + parallel DB matching.
Rule fallback: Pure regex/keyword inference when no LLM is available.

Agent utilities (_agent_dict_to_analysis, _run_agent_from_dicts) are kept
for the standalone product analyst agent but are not used in the document
parse flow.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from catalog.application.product_classification import infer_uom, suggest_department
from catalog.domain.product_analysis import (
    AnalyzedProduct,
    FamilyCandidate,
    ProductAnalysis,
)
from shared.infrastructure.prompt_loader import load_prompt, register_partial
from shared.kernel.units import ALLOWED_BASE_UNITS, normalize_pack_qty, normalize_unit

logger = logging.getLogger(__name__)

GenerateTextFn = Callable[[str, str | None], str | None] | None

_SYSTEM_PROMPT: str | None = None
_RULES_REGISTERED = False


def _ensure_rules_partial() -> None:
    """Register the shared product rules partial once for prompt expansion."""
    global _RULES_REGISTERED
    if not _RULES_REGISTERED:
        rules = load_prompt(__file__, "product_rules_partial.md")
        register_partial("PRODUCT_RULES", rules)
        _RULES_REGISTERED = True


def _get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _ensure_rules_partial()
        _SYSTEM_PROMPT = load_prompt(__file__, "product_decomposition_prompt.md")
    return _SYSTEM_PROMPT


_normalize_unit = normalize_unit
_normalize_pack_qty = normalize_pack_qty


def _parse_llm_products(response: str) -> list[dict]:
    """Extract JSON array from LLM response."""
    json_match = re.search(r"\[[\s\S]*\]", response)
    if not json_match:
        return []
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.warning("Product intelligence: invalid JSON from LLM — %s", e)
        return []


def _dict_to_analyzed_product(
    raw: dict,
    raw_text: str,
    known_units: frozenset[str] | None = None,
) -> AnalyzedProduct:
    """Convert LLM or agent JSON output to typed AnalyzedProduct."""
    specs = raw.get("specifications") or {}
    if not isinstance(specs, dict):
        specs = {}
    vattrs = raw.get("variant_attrs") or {}
    if not isinstance(vattrs, dict):
        vattrs = {}

    return AnalyzedProduct(
        raw_text=raw.get("raw_text") or raw_text,
        clean_name=raw.get("clean_name") or raw.get("name") or raw_text[:120],
        brand=raw.get("brand") or None,
        product_type=raw.get("product_type") or "",
        specifications={str(k): str(v) for k, v in specs.items()},
        base_unit=_normalize_unit(raw.get("base_unit"), known_units),
        sell_uom=_normalize_unit(raw.get("sell_uom", raw.get("base_unit")), known_units),
        pack_qty=_normalize_pack_qty(raw.get("pack_qty")),
        purchase_uom=_normalize_unit(raw.get("purchase_uom", raw.get("base_unit")), known_units),
        purchase_pack_qty=_normalize_pack_qty(raw.get("purchase_pack_qty")),
        suggested_department=(raw.get("suggested_department") or "HDW").upper().strip(),
        variant_label=raw.get("variant_label") or "",
        variant_attrs={str(k): str(v) for k, v in vattrs.items()},
        original_sku=raw.get("original_sku") or None,
        confidence=min(1.0, max(0.0, float(raw.get("confidence") or 0.0))),
    )


def _rule_fallback(item: dict) -> AnalyzedProduct:
    """Build AnalyzedProduct from rule-based inference when LLM is unavailable."""
    name = item.get("name") or ""
    bu, su, pq = infer_uom(name)
    dept_code = suggest_department(name, _FALLBACK_DEPTS) or "HDW"

    return AnalyzedProduct(
        raw_text=name,
        clean_name=name,
        brand=None,
        product_type="",
        base_unit=bu,
        sell_uom=su,
        pack_qty=pq,
        purchase_uom=bu,
        purchase_pack_qty=pq,
        suggested_department=dept_code.upper(),
        original_sku=item.get("original_sku"),
        confidence=0.3,
    )


_FALLBACK_DEPTS = dict.fromkeys(("PLU", "ELE", "PNT", "LUM", "TOL", "HDW", "GDN", "APP"), True)


# ── Agent utilities ──────────────────────────────────────────────────────────
# Used by assistant/agents/product_analyst when run standalone.


def _agent_dict_to_analysis(
    raw: dict,
    source_item: dict,
    known_units: frozenset[str] | None = None,
) -> ProductAnalysis:
    """Convert an agent-submitted analysis dict to typed ProductAnalysis."""
    raw_text = source_item.get("name") or ""
    product = _dict_to_analyzed_product(raw, raw_text, known_units)

    family_candidates: list[FamilyCandidate] = []
    if raw.get("matched_family_id"):
        family_candidates.append(
            FamilyCandidate(
                family_id=raw["matched_family_id"],
                family_name=raw.get("matched_family_name") or "",
                similarity=1.0,
            )
        )

    return ProductAnalysis(
        product=product,
        family_candidates=family_candidates,
        matched_sku_id=raw.get("matched_sku_id"),
        matched_vendor_item_id=raw.get("matched_vendor_item_id"),
        recommendation=raw.get("recommendation") or "",
        recommendation_reason=raw.get("recommendation_reason") or "",
        warnings=raw.get("warnings") or [],
    )


async def _run_agent_from_dicts(
    items: list[dict],
    analyses_dicts: list[dict],
    known_units: frozenset[str] | None = None,
) -> list[ProductAnalysis]:
    """Convert raw agent output dicts to typed ProductAnalysis list."""
    results: list[ProductAnalysis] = []
    for i, item in enumerate(items):
        if i < len(analyses_dicts):
            results.append(_agent_dict_to_analysis(analyses_dicts[i], item, known_units))
        else:
            ap = _rule_fallback(item)
            results.append(
                ProductAnalysis(
                    product=ap,
                    warnings=["Agent did not return analysis for this item"],
                )
            )
    return results


# ── Batch LLM path (fast) ───────────────────────────────────────────────────


async def _decompose_products(
    items: list[dict],
    generate_text: GenerateTextFn,
    known_units: frozenset[str] | None = None,
) -> list[AnalyzedProduct]:
    """Batch LLM decomposition — single call for all items."""
    if not items:
        return []

    if not generate_text:
        return [_rule_fallback(item) for item in items]

    items_text = "\n".join(
        f"{i + 1}. {item.get('name', '')} "
        f"(original_sku: {item.get('original_sku') or 'none'}, "
        f"price: {item.get('price') or item.get('unit_price') or '?'}, "
        f"qty: {item.get('quantity') or item.get('ordered_qty') or '?'})"
        for i, item in enumerate(items)
    )
    prompt = f"""Analyze these {len(items)} product line items from a hardware store receipt/quote.

{items_text}

Decompose each into structured product data following the system instructions."""

    try:
        response = await asyncio.to_thread(generate_text, prompt, _get_system_prompt())
        if not response:
            logger.warning("Product intelligence: LLM returned empty response")
            return [_rule_fallback(item) for item in items]

        parsed = _parse_llm_products(response)
        if not parsed:
            return [_rule_fallback(item) for item in items]

        results: list[AnalyzedProduct] = []
        for i, item in enumerate(items):
            raw_text = item.get("name") or ""
            if i < len(parsed) and isinstance(parsed[i], dict):
                results.append(_dict_to_analyzed_product(parsed[i], raw_text, known_units))
            else:
                results.append(_rule_fallback(item))
        return results

    except Exception as e:
        logger.warning(
            "Batch LLM failed (%s: %s) — falling back to rules",
            type(e).__name__,
            e,
        )
        return [_rule_fallback(item) for item in items]


# ── Phase 2: Match and Validate (used by batch path only) ───────────────────


SearchFamiliesFn = Callable[..., Awaitable[list[dict[str, Any]]]]
FindByVendorSkuFn = Callable[..., Awaitable[Any]]
FindByNameVendorFn = Callable[..., Awaitable[Any]]


async def _find_family_candidates(
    product: AnalyzedProduct,
    search_families: SearchFamiliesFn | None,
) -> list[FamilyCandidate]:
    if not search_families:
        return []
    query = product.clean_name
    if product.brand:
        query = f"{product.brand} {query}"
    try:
        families = await search_families(query)
        return [
            FamilyCandidate(
                family_id=f.get("id") or f.get("family_id", ""),
                family_name=f.get("name") or f.get("family_name", ""),
                similarity=float(f.get("similarity", f.get("score", 0.0))),
            )
            for f in families[:3]
        ]
    except Exception as e:
        logger.warning("Family search failed: %s", e)
        return []


async def _find_vendor_match(
    product: AnalyzedProduct,
    vendor_id: str | None,
    find_by_vendor_sku: FindByVendorSkuFn | None,
    find_by_name_and_vendor: FindByNameVendorFn | None,
) -> tuple[str | None, str | None]:
    if not vendor_id:
        return None, None
    if product.original_sku and find_by_vendor_sku:
        try:
            vi = await find_by_vendor_sku(vendor_id, product.original_sku)
            if vi:
                return vi.sku_id, vi.id
        except Exception as e:
            logger.warning("Vendor SKU lookup failed: %s", e)
    if find_by_name_and_vendor:
        try:
            sku = await find_by_name_and_vendor(product.clean_name, vendor_id)
            if sku:
                return sku.id, None
        except Exception as e:
            logger.warning("Name+vendor lookup failed: %s", e)
    return None, None


def _validate_product(
    product: AnalyzedProduct,
    valid_dept_codes: set[str],
    known_units: frozenset[str] | None = None,
) -> list[str]:
    valid = known_units if known_units is not None else ALLOWED_BASE_UNITS
    warnings: list[str] = []
    if product.base_unit not in valid:
        warnings.append(f"Unknown base_unit '{product.base_unit}' — defaulting to 'each'")
    if product.sell_uom not in valid:
        warnings.append(f"Unknown sell_uom '{product.sell_uom}' — defaulting to 'each'")
    if product.suggested_department not in valid_dept_codes:
        warnings.append(
            f"Unknown department '{product.suggested_department}' — defaulting to 'HDW'"
        )
    if product.confidence < 0.7:
        warnings.append("Low confidence classification — verify department and UOM")
    if not product.clean_name or product.clean_name == product.raw_text:
        warnings.append("Name may need manual cleanup")
    return warnings


def _derive_recommendation(
    product: AnalyzedProduct,
    sku_id: str | None,
    vendor_item_id: str | None,
    families: list[FamilyCandidate],
) -> tuple[str, str]:
    """Derive recommendation type and reason from matching results."""
    if sku_id:
        if vendor_item_id:
            return (
                "link_existing",
                f"Matched existing SKU via vendor item lookup for '{product.clean_name}'.",
            )
        return "link_existing", f"Found existing SKU matching '{product.clean_name}'."

    if families:
        best = families[0]
        return "add_variant", (
            f"Found '{best.family_name}' product family (similarity: {best.similarity:.0%}). "
            f"Consider adding as a new variant."
        )

    return (
        "create_new",
        f"No existing match found for '{product.clean_name}'. Will create as a new product.",
    )


async def _enrich_single(
    product: AnalyzedProduct,
    vendor_id: str | None,
    valid_dept_codes: set[str],
    search_families: SearchFamiliesFn | None,
    find_by_vendor_sku: FindByVendorSkuFn | None,
    find_by_name_and_vendor: FindByNameVendorFn | None,
    known_units: frozenset[str] | None = None,
) -> ProductAnalysis:
    family_task = _find_family_candidates(product, search_families)
    vendor_task = _find_vendor_match(
        product, vendor_id, find_by_vendor_sku, find_by_name_and_vendor
    )
    families, (sku_id, vi_id) = await asyncio.gather(family_task, vendor_task)
    warnings = _validate_product(product, valid_dept_codes, known_units)

    recommendation, reason = _derive_recommendation(product, sku_id, vi_id, families)

    return ProductAnalysis(
        product=product,
        family_candidates=families,
        matched_sku_id=sku_id,
        matched_vendor_item_id=vi_id,
        recommendation=recommendation,
        recommendation_reason=reason,
        warnings=warnings,
    )


# ── Public API ───────────────────────────────────────────────────────────────


async def analyze_products(
    items: list[dict],
    *,
    generate_text: GenerateTextFn = None,
    vendor_id: str | None = None,
    dept_codes: list[str] | None = None,
    known_units: frozenset[str] | None = None,
    search_families: SearchFamiliesFn | None = None,
    find_by_vendor_sku: FindByVendorSkuFn | None = None,
    find_by_name_and_vendor: FindByNameVendorFn | None = None,
) -> list[ProductAnalysis]:
    """Batch product intelligence: single LLM call for decomposition + parallel DB matching.

    Pass ``known_units`` (from ``catalog_queries.get_known_unit_codes()``) to enable
    org-custom units in LLM prompts and validation.

    Strategy:
    1. Batch LLM — single call for decomposition when generate_text is provided.
    2. Rule fallback — regex/keyword inference when no LLM is available.

    Returns list of ProductAnalysis, one per input item, in the same order.
    """
    if not items:
        return []

    valid_depts = set(dept_codes or []) | set(_FALLBACK_DEPTS.keys())
    analyzed = await _decompose_products(items, generate_text, known_units)

    tasks = [
        _enrich_single(
            product=ap,
            vendor_id=vendor_id,
            valid_dept_codes=valid_depts,
            search_families=search_families,
            find_by_vendor_sku=find_by_vendor_sku,
            find_by_name_and_vendor=find_by_name_and_vendor,
            known_units=known_units,
        )
        for ap in analyzed
    ]

    return list(await asyncio.gather(*tasks))
