"""Shared helpers for finance DB services (UUID / row mapping)."""

from __future__ import annotations

import uuid
from typing import Any


def uuids_to_str(d: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out
