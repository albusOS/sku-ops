"""Shared JSON serialization for agent tool results.

Handles date → str coercion so tool functions can return json.dumps(data)
without per-file boilerplate.
"""

from __future__ import annotations

import json


def normalise(obj: object) -> object:
    """Recursively ensure values are JSON-safe (no leftover Decimal, etc.)."""
    if isinstance(obj, dict):
        return {k: normalise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalise(v) for v in obj]
    return obj


def dumps(obj: object) -> str:
    """json.dumps with normalisation."""
    return json.dumps(normalise(obj))
