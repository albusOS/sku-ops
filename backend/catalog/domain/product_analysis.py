"""Typed output contracts for the product intelligence pipeline.

These represent the structured decomposition of raw receipt/quote text
into catalog-ready product data. Used by PO creation and document import.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnalyzedProduct:
    """Structured decomposition of a raw product line.

    Phase 1 of the pipeline: a single LLM call decomposes messy text into
    brand, type, specifications, selling configuration, and classification.
    """

    raw_text: str
    clean_name: str
    brand: str | None = None
    product_type: str = ""
    specifications: dict[str, str] = field(default_factory=dict)
    base_unit: str = "each"
    sell_uom: str = "each"
    pack_qty: int = 1
    purchase_uom: str = "each"
    purchase_pack_qty: int = 1
    suggested_department: str = "HDW"
    variant_label: str = ""
    variant_attrs: dict[str, str] = field(default_factory=dict)
    original_sku: str | None = None
    confidence: float = 0.0


@dataclass(frozen=True)
class FamilyCandidate:
    """A potential product family match from semantic search."""

    family_id: str
    family_name: str
    similarity: float


@dataclass(frozen=True)
class ProductAnalysis:
    """Fully enriched result: decomposed product + catalog matching + validation.

    Phase 2 output. Ready for PO creation or catalog import.
    """

    product: AnalyzedProduct
    family_candidates: list[FamilyCandidate] = field(default_factory=list)
    matched_sku_id: str | None = None
    matched_vendor_item_id: str | None = None
    recommendation: str = ""
    recommendation_reason: str = ""
    warnings: list[str] = field(default_factory=list)
