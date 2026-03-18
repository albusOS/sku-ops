"""Document import helpers: CSV parsing and dollar parsing.

UOM inference, department suggestion, and UOM resolution have moved to
catalog.application.product_classification. Re-exports are provided for
backward compatibility with existing callers.
"""

import contextlib
import csv
import io

# Re-export from canonical location for backward compatibility
from catalog.application.product_classification import (  # noqa: F401
    infer_uom,
    resolve_uom,
    suggest_department,
)


def parse_dollar(val: str) -> float:
    """Parse '$2.73' or '2.73' to float."""
    if not val or not str(val).strip():
        return 0.0
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return round(float(s), 2)
    except (ValueError, TypeError):
        return 0.0


def parse_csv_products(content: bytes) -> list:
    """
    Parse Supply Yard inventory CSV format.
    Columns: Product, SKU, Barcode, On hand, Reorder qty, Reorder point,
             Unit cost, Total cost, Retail price, Retail (Ex. Tax), Retail (Inc. Tax), Department/Category
    """
    decoded = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(decoded))

    header = None
    header_idx = -1
    for i, row in enumerate(reader):
        if row and str(row[0]).strip().lower() == "product":
            header = [c.strip() for c in row]
            header_idx = i
            break

    if not header:
        raise ValueError("CSV must have a header row with 'Product' in first column")

    col_map = {}
    for idx, name in enumerate(header):
        n = name.lower()
        if "product" in n:
            col_map["name"] = idx
        elif "sku" in n and "barcode" not in n:
            col_map["sku"] = idx
        elif "on hand" in n or "quantity" in n:
            col_map["quantity"] = idx
        elif "reorder point" in n:
            col_map["min_stock"] = idx
        elif "unit cost" in n or ("cost" in n and "total" not in n and "cost" not in col_map):
            col_map["cost"] = idx
        elif "retail price" in n and "ex" not in n and "inc" not in n:
            col_map["price"] = idx
        elif "department" in n or "category" in n:
            col_map["department"] = idx
        elif "barcode" in n:
            col_map["barcode"] = idx

    if "name" not in col_map:
        raise ValueError("CSV must have a Product/name column")

    decoded2 = content.decode("utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(decoded2)))

    products = []
    for i, row in enumerate(rows):
        if i <= header_idx or len(row) <= col_map["name"]:
            continue
        name = (row[col_map["name"]] or "").strip()
        if not name:
            continue
        if name.lower().startswith("current inventory") or name.lower().startswith(
            "for the period"
        ):
            continue

        qty = 0.0
        with contextlib.suppress(ValueError, TypeError, IndexError):
            qty = float((row[col_map.get("quantity", 3)] or "0").replace(",", ""))

        cost = parse_dollar(
            row[col_map.get("cost", 6)] if col_map.get("cost", 6) < len(row) else "0"
        )
        price = parse_dollar(
            row[col_map.get("price", 8)] if col_map.get("price", 8) < len(row) else "0"
        )
        if price <= 0 and cost > 0:
            price = round(cost * 1.4, 2)
        elif cost <= 0 and price > 0:
            cost = round(price * 0.7, 2)

        min_stock = 5
        with contextlib.suppress(ValueError, TypeError, IndexError):
            min_stock = max(
                0, int(float((row[col_map.get("min_stock", 5)] or "0").replace(",", "")))
            )
        if min_stock == 0:
            min_stock = 5

        products.append(
            {
                "name": name,
                "quantity": qty,
                "cost": cost,
                "price": price,
                "min_stock": min_stock,
                "original_sku": (row[col_map["sku"]] or "").strip() or None
                if col_map.get("sku") is not None and col_map["sku"] < len(row)
                else None,
                "barcode": (row[col_map["barcode"]] or "").strip() or None
                if col_map.get("barcode") is not None and col_map["barcode"] < len(row)
                else None,
                "department": (row[col_map["department"]] or "").strip() or None
                if col_map.get("department") is not None and col_map["department"] < len(row)
                else None,
            }
        )

    return products
