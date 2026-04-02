"""Step 1: Parse supabase gen types --lang=python output into structured model data.

Parses the BaseModel (Row) classes from the generated Python types file,
filtering out Insert/Update TypedDict variants. Extracts field names, types,
and nullability for each table model.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedField:
    name: str
    type_annotation: str
    is_optional: bool
    has_default: bool
    raw_annotation_node: ast.expr | None = field(default=None, repr=False)


@dataclass
class ParsedModel:
    class_name: str
    table_name: str
    schema_name: str
    fields: list[ParsedField]


def _strip_cli_noise(content: str) -> str:
    """Remove supabase CLI debug lines like 'Connecting to db 5432'."""
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        if re.match(r"^Connecting to db \d+", line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _table_name_from_class(class_name: str, prefix: str) -> str:
    """Derive table name from class name by stripping schema prefix and converting to snake_case.

    PublicBillingEntities -> billing_entities
    """
    name = class_name
    name = name.removeprefix(prefix)
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return snake


def _is_optional_annotation(node: ast.expr) -> bool:
    """Check if an AST annotation represents an Optional type (X | None or Optional[X])."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        parts = []
        curr: ast.expr = node
        while isinstance(curr, ast.BinOp) and isinstance(curr.op, ast.BitOr):
            parts.append(curr.right)
            curr = curr.left
        parts.append(curr)
        return any(
            isinstance(p, ast.Constant) and p.value is None for p in parts
        )
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        if node.value.id == "Optional":
            return True
    return False


def _annotation_to_str(node: ast.expr) -> str:
    return ast.unparse(node)


def _has_default_value(node: ast.AnnAssign) -> bool:
    if node.value is None:
        return False
    src = ast.unparse(node.value)
    if "Field(" in src:
        return True
    return True


def parse_pydantic_types(
    content: str,
    schema_name: str,
    class_prefix: str,
) -> list[ParsedModel]:
    """Parse all BaseModel row classes for a given schema prefix."""
    content = _strip_cli_noise(content)
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    models: list[ParsedModel] = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.startswith(class_prefix):
            continue
        if node.name.endswith(("Insert", "Update")):
            continue
        bases = [ast.unparse(b) for b in node.bases]
        if "BaseModel" not in bases:
            continue

        table_name = _table_name_from_class(node.name, class_prefix)
        fields: list[ParsedField] = []

        for item in node.body:
            if not isinstance(item, ast.AnnAssign):
                continue
            if not isinstance(item.target, ast.Name):
                continue

            field_name = item.target.id
            type_str = _annotation_to_str(item.annotation)
            is_opt = _is_optional_annotation(item.annotation)
            has_def = _has_default_value(item)

            fields.append(
                ParsedField(
                    name=field_name,
                    type_annotation=type_str,
                    is_optional=is_opt,
                    has_default=has_def,
                    raw_annotation_node=item.annotation,
                )
            )

        models.append(
            ParsedModel(
                class_name=node.name,
                table_name=table_name,
                schema_name=schema_name,
                fields=fields,
            )
        )

    return models


def parse_from_file(
    path: Path,
    schema_name: str = "public",
    class_prefix: str = "Public",
) -> list[ParsedModel]:
    content = path.read_text()
    return parse_pydantic_types(content, schema_name, class_prefix)
