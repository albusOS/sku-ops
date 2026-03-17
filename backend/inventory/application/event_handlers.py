"""Inventory domain event handlers.

Reacts to stock-level changes and emits LowStockDetected when a product
drops to or below its reorder point (min_stock). This is the trigger
point for future automated reorder / purchasing agent flows.
"""

from __future__ import annotations

import logging

from catalog.application.queries import get_sku_by_id
from shared.infrastructure.domain_events import dispatch, on
from shared.kernel.domain_events import InventoryChanged, LowStockDetected

logger = logging.getLogger(__name__)


@on(InventoryChanged)
async def check_reorder_points(event: InventoryChanged) -> None:
    """Evaluate reorder points for every product affected by a stock change."""
    for sku_id in event.sku_ids:
        try:
            product = await get_sku_by_id(sku_id)
            if not product:
                continue
            if product.quantity <= product.min_stock:
                await dispatch(
                    LowStockDetected(
                        org_id=event.org_id,
                        sku_id=sku_id,
                        product_name=product.name,
                        sku=product.sku,
                        current_qty=product.quantity,
                        min_stock=product.min_stock,
                    )
                )
        except (RuntimeError, OSError, ValueError):
            logger.warning("Reorder check failed for sku %s", sku_id, exc_info=True)


@on(LowStockDetected)
async def log_low_stock(event: LowStockDetected) -> None:
    """Log low-stock detections. Future: feed into purchasing agent / dashboard alerts."""
    logger.info(
        "LOW STOCK: %s (%s) — qty=%.1f, min=%.1f, org=%s",
        event.product_name,
        event.sku,
        event.current_qty,
        event.min_stock,
        event.org_id,
    )
