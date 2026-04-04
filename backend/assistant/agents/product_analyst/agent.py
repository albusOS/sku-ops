"""Product analyst agent — ReAct agent for product decomposition and catalog matching.

Given raw product lines from receipts/quotes, the agent researches each product
against the existing catalog, decomposes it structurally, and produces typed
ProductAnalysis results via tool calls.

Agent construction is deferred to first use so missing API keys don't crash imports.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext

from assistant.agents.core.config import load_agent_config
from catalog.application.product_intelligence import _ensure_rules_partial
from assistant.agents.core.contracts import UsageInfo
from assistant.agents.core.model_registry import (
    calc_cost,
    get_model,
    get_model_name,
)
from assistant.agents.core.tokens import budget_tool_result
from assistant.agents.tools.models import (
    CatalogSearchResult,
    DepartmentCodesResult,
    FamilySkusResult,
    VendorItemMatch,
)
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


def _db_catalog():
    return get_database_manager().catalog


_SYSTEM_PROMPT: str | None = None


def _get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _ensure_rules_partial()
        _SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")
    return _SYSTEM_PROMPT


@dataclass
class ProductAnalystDeps:
    """Dependencies for product analyst tool calls."""

    vendor_id: str | None = None
    vendor_name: str | None = None
    collected_analyses: list[dict[str, Any]] = field(default_factory=list)


_agent: Agent[ProductAnalystDeps, str] | None = None


def _get_agent() -> Agent[ProductAnalystDeps, str]:
    global _agent
    if _agent is not None:
        return _agent

    cfg = load_agent_config("product_analyst")
    _agent = Agent(
        get_model("agent:product_analyst"),
        deps_type=ProductAnalystDeps,
        system_prompt=_get_system_prompt(),
        model_settings={
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_output_tokens,
        },
    )

    @_agent.tool
    async def search_catalog(
        ctx: RunContext[ProductAnalystDeps],
        query: str,
        department: str = "",
    ) -> str:
        """Search existing SKUs and product families by name, type, or brand.

        Use this to check if a product already exists before classifying.
        Returns matching SKUs and families with their details.
        """
        sku_items: list[dict[str, Any]] = []
        family_items: list[dict[str, Any]] = []

        try:
            skus = await _db_catalog().list_skus(get_org_id(), search=query, limit=5)
            sku_items = [
                {
                    "id": s.id,
                    "sku": s.sku,
                    "name": s.name,
                    "category_name": s.category_name,
                    "product_family_id": s.product_family_id,
                    "base_unit": s.base_unit,
                    "sell_uom": s.sell_uom,
                    "pack_qty": s.pack_qty,
                    "variant_label": s.variant_label,
                    "cost": float(s.cost) if s.cost else None,
                }
                for s in skus
            ]
        except Exception as e:
            logger.warning("Catalog SKU search failed: %s", e)

        try:
            families = await _db_catalog().list_product_families(
                get_org_id(), search=query, limit=5
            )
            family_items = [
                {
                    "id": f.id,
                    "name": f.name,
                    "category_name": f.category_name,
                    "sku_count": f.sku_count,
                }
                for f in families
            ]
        except Exception as e:
            logger.warning("Catalog family search failed: %s", e)

        return budget_tool_result(
            CatalogSearchResult(skus=sku_items, families=family_items).serialize()
        )

    @_agent.tool
    async def get_family_skus(
        ctx: RunContext[ProductAnalystDeps],
        family_id: str,
    ) -> str:
        """List all SKU variants in a product family.

        Use this after finding a family match to see what variants exist,
        so you can determine if the new product is a new variant.
        """
        try:
            skus = await _db_catalog().list_skus(
                get_org_id(), product_family_id=family_id, limit=20
            )
            items = [
                {
                    "sku": s.sku,
                    "name": s.name,
                    "variant_label": s.variant_label,
                    "base_unit": s.base_unit,
                    "sell_uom": s.sell_uom,
                    "pack_qty": s.pack_qty,
                    "spec": s.spec,
                    "grade": s.grade,
                }
                for s in skus
            ]
            return budget_tool_result(FamilySkusResult(skus=items).serialize())
        except Exception as e:
            logger.warning("Family SKU lookup failed: %s", e)
            return FamilySkusResult(skus=[]).serialize()

    @_agent.tool
    async def lookup_vendor_item(
        ctx: RunContext[ProductAnalystDeps],
        vendor_sku: str,
    ) -> str:
        """Look up a product by vendor's model/SKU number.

        Use this when a receipt line has an original_sku or model number
        to check if we already track this vendor's product.
        """
        vendor_id = ctx.deps.vendor_id
        if not vendor_id:
            return VendorItemMatch(match=None, reason="no vendor_id provided").serialize()
        try:
            vi = await _db_catalog().find_vendor_item_by_vendor_and_sku(
                get_org_id(), vendor_id, vendor_sku
            )
            if vi:
                return VendorItemMatch(
                    match={
                        "vendor_item_id": vi.id,
                        "sku_id": vi.sku_id,
                        "vendor_sku": vi.vendor_sku,
                        "cost": float(vi.cost) if vi.cost else None,
                        "purchase_uom": vi.purchase_uom,
                    }
                ).serialize()
            return VendorItemMatch(match=None).serialize()
        except Exception as e:
            logger.warning("Vendor item lookup failed: %s", e)
            return VendorItemMatch(match=None, error=str(e)).serialize()

    @_agent.tool
    async def get_departments(ctx: RunContext[ProductAnalystDeps]) -> str:
        """Get all valid department codes for classification."""
        try:
            depts = await _db_catalog().list_departments(get_org_id())
            return DepartmentCodesResult(
                departments=[{"code": d.code, "name": d.name, "id": d.id} for d in depts]
            ).serialize()
        except Exception as e:
            logger.warning("Department lookup failed: %s", e)
            return DepartmentCodesResult(departments=[], error=str(e)).serialize()

    @_agent.tool
    async def submit_analysis(
        ctx: RunContext[ProductAnalystDeps],
        raw_text: str,
        clean_name: str,
        base_unit: str,
        sell_uom: str,
        pack_qty: int,
        suggested_department: str,
        confidence: float,
        brand: str = "",
        product_type: str = "",
        specifications: str = "{}",
        purchase_uom: str = "",
        purchase_pack_qty: int = 1,
        variant_label: str = "",
        variant_attrs: str = "{}",
        original_sku: str = "",
        matched_family_id: str = "",
        matched_family_name: str = "",
        matched_sku_id: str = "",
        matched_vendor_item_id: str = "",
        recommendation: str = "",
        recommendation_reason: str = "",
        warnings: str = "[]",
    ) -> str:
        """Submit structured analysis for one product.

        Call this once per product after researching.
        recommendation must be one of: link_existing, add_variant, create_new.
        recommendation_reason is a short human-readable explanation.
        specifications, variant_attrs, and warnings should be JSON strings.
        """

        def _safe_json_parse(s: str, default: Any) -> Any:
            if not s:
                return default
            try:
                return json.loads(s)
            except (json.JSONDecodeError, TypeError):
                return default

        analysis = {
            "raw_text": raw_text,
            "clean_name": clean_name,
            "brand": brand or None,
            "product_type": product_type,
            "specifications": _safe_json_parse(specifications, {}),
            "base_unit": base_unit,
            "sell_uom": sell_uom,
            "pack_qty": pack_qty,
            "purchase_uom": purchase_uom or base_unit,
            "purchase_pack_qty": purchase_pack_qty,
            "suggested_department": suggested_department.upper().strip(),
            "variant_label": variant_label,
            "variant_attrs": _safe_json_parse(variant_attrs, {}),
            "original_sku": original_sku or None,
            "confidence": min(1.0, max(0.0, confidence)),
            "matched_family_id": matched_family_id or None,
            "matched_family_name": matched_family_name or None,
            "matched_sku_id": matched_sku_id or None,
            "matched_vendor_item_id": matched_vendor_item_id or None,
            "recommendation": recommendation,
            "recommendation_reason": recommendation_reason,
            "warnings": _safe_json_parse(warnings, []),
        }
        ctx.deps.collected_analyses.append(analysis)
        return f"Analysis submitted for: {clean_name}"

    return _agent


async def run(
    items: list[dict],
    *,
    vendor_id: str | None = None,
    vendor_name: str | None = None,
) -> tuple[list[dict], UsageInfo]:
    """Run the product analyst agent on a batch of items.

    Returns (list of analysis dicts, usage info).
    """
    agent = _get_agent()
    deps = ProductAnalystDeps(
        vendor_id=vendor_id,
        vendor_name=vendor_name,
    )

    items_text = "\n".join(
        f"{i + 1}. {item.get('name', 'Unknown')} "
        f"(original_sku: {item.get('original_sku') or 'none'}, "
        f"price: {item.get('price') or item.get('unit_price') or '?'}, "
        f"cost: {item.get('cost') or '?'}, "
        f"qty: {item.get('quantity') or item.get('ordered_qty') or '?'})"
        for i, item in enumerate(items)
    )

    vendor_ctx = ""
    if vendor_name:
        vendor_ctx = f"\nVendor: {vendor_name}"
        if vendor_id:
            vendor_ctx += f" (id: {vendor_id})"

    user_message = (
        f"Analyze these {len(items)} product lines from a hardware store receipt."
        f"{vendor_ctx}\n\n{items_text}\n\n"
        f"For each product: search the catalog, determine if it exists or is a variant "
        f"of an existing family, classify UOM and department, then submit_analysis."
    )

    try:
        result = await agent.run(user_message, deps=deps)
        model_name = get_model_name("agent:product_analyst")
        usage = result.usage()
        return deps.collected_analyses, UsageInfo(
            cost_usd=calc_cost(model_name, usage),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=model_name,
        )
    except Exception:
        logger.exception("product_analyst agent failed")
        return [], UsageInfo()
