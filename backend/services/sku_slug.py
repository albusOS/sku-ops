"""
SKU slug generation from product names.
Produces short alphanumeric slugs for meaningful SKU prefixes (e.g. DEPT-SLUG-00001).
"""
import re


def slug_from_name(name: str, max_len: int = 6) -> str:
    """
    Derive a short alphanumeric slug from product name.
    Uppercase, alphanumeric only, truncate to max_len.
    """
    if not name or not str(name).strip():
        return "ITM"
    s = str(name).strip().upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    if not s:
        return "ITM"
    return s[:max_len] if len(s) > max_len else s
