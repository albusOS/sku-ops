"""Step 4: Pydantic-to-SQLModel type mappings.

Maps Supabase-generated Pydantic type annotations to SQLModel field types
and optional SQLAlchemy column type overrides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MappedType:
    python_type: str
    sa_type: str | None = None
    needs_import: set[str] | None = None


def map_pydantic_type(annotation: str, is_optional: bool) -> MappedType:
    """Map a Pydantic type annotation string to a SQLModel-compatible type."""
    clean = _strip_optional(annotation)

    if clean == "str":
        return MappedType(python_type=_wrap_optional("str", is_optional))

    if clean == "int":
        return MappedType(python_type=_wrap_optional("int", is_optional))

    if clean == "float":
        return MappedType(
            python_type=_wrap_optional("float", is_optional),
            sa_type="Float",
            needs_import={"Float"},
        )

    if clean == "bool":
        return MappedType(python_type=_wrap_optional("bool", is_optional))

    if clean == "datetime.datetime":
        return MappedType(
            python_type=_wrap_optional("datetime.datetime", is_optional),
            sa_type="DateTime(timezone=True)",
            needs_import={"DateTime"},
        )

    if clean == "datetime.date":
        return MappedType(
            python_type=_wrap_optional("datetime.date", is_optional),
            sa_type="Date",
            needs_import={"Date"},
        )

    if re.match(r"Json\[.*\]|Json", clean):
        return MappedType(
            python_type=_wrap_optional("dict | None", False),
            sa_type="JSONB",
            needs_import={"JSONB"},
        )

    if clean == "uuid.UUID":
        return MappedType(
            python_type=_wrap_optional("uuid.UUID", is_optional),
            sa_type="PG_UUID(as_uuid=True)",
            needs_import={"PG_UUID"},
        )

    if re.match(r"list\[.*\]|List\[.*\]", clean):
        return MappedType(
            python_type=_wrap_optional("list", is_optional),
            sa_type="JSONB",
            needs_import={"JSONB"},
        )

    return MappedType(python_type=_wrap_optional("str", is_optional))


def _strip_optional(annotation: str) -> str:
    """Strip Optional wrapper and | None from type annotation."""
    annotation = annotation.strip()
    m = re.match(r"Optional\[(.+)\]$", annotation)
    if m:
        return m.group(1).strip()
    parts = [p.strip() for p in annotation.split("|")]
    non_none = [p for p in parts if p != "None"]
    if non_none:
        return non_none[0]
    return "str"


def _wrap_optional(base: str, is_optional: bool) -> str:
    if is_optional:
        return f"{base} | None"
    return base
