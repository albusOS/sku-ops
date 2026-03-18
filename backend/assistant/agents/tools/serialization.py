"""Shared JSON serialization for agent tool results.

Handles Decimal → float, date → str coercion so tool functions
can return json.dumps(data) without per-file boilerplate.
"""

from __future__ import annotations

import json
from decimal import Decimal


def to_float(v: object) -> object:
    if isinstance(v, Decimal):
        return float(v)
    return v


def normalise(obj: object) -> object:
    """Recursively convert Decimal values in dicts/lists to float."""
    if isinstance(obj, dict):
        return {k: normalise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalise(v) for v in obj]
    return to_float(obj)


def dumps(obj: object) -> str:
    """json.dumps with Decimal → float conversion."""
    return json.dumps(normalise(obj))
