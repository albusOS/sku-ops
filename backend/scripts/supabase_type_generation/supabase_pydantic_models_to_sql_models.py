"""Step 3: Generate SQLModel classes from parsed Pydantic models + relationship metadata.

Produces one {schema}_sql_model_models.py file per schema with:
- SQLModel table classes with proper Field() definitions
- Foreign key declarations via Field(foreign_key="table.column")
- Relationship() attributes with back_populates
- M2M relationships via link_model=
- Topological ordering (parents before children)
"""

from __future__ import annotations

from collections import defaultdict

from backend.scripts.supabase_type_generation.pydantic_to_sql_model_type_mapping import (
    map_pydantic_type,
)
from backend.scripts.supabase_type_generation.supabase_ts_relationship_parser import (
    ForeignKeyInfo,
    RelationshipMetadata,
)
from backend.scripts.supabase_type_generation.supabase_types_to_pydantic_models import (
    ParsedField,
    ParsedModel,
)


def _table_to_class(table_name: str) -> str:
    """Convert snake_case table name to PascalCase class name."""
    return "".join(word.capitalize() for word in table_name.split("_"))


PYTHON_RESERVED = frozenset(
    {
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }
)


def _safe_attr_name(name: str) -> str:
    """Append underscore if name collides with a Python keyword."""
    if name in PYTHON_RESERVED:
        return f"{name}_ref"
    return name


def _fk_col_to_rel_name(fk_column: str) -> str:
    """Derive relationship attr name from FK column: category_id -> category."""
    if fk_column.endswith("_id"):
        base = fk_column[:-3]
    else:
        base = fk_column
    return _safe_attr_name(base)


def _pluralize(name: str) -> str:
    if name.endswith("s"):
        return _safe_attr_name(name)
    if name.endswith("y") and not name.endswith(("ay", "ey", "oy", "uy")):
        return _safe_attr_name(name[:-1] + "ies")
    return _safe_attr_name(name + "s")


def _topological_sort(
    models: list[ParsedModel],
    fks: list[ForeignKeyInfo],
    link_tables: set[str],
) -> list[ParsedModel]:
    """Sort models so parents come before children. Link tables go last."""
    model_map = {m.table_name: m for m in models}
    deps: dict[str, set[str]] = defaultdict(set)

    for fk in fks:
        if fk.source_table in model_map and fk.target_table in model_map:
            if fk.source_table != fk.target_table:
                deps[fk.source_table].add(fk.target_table)

    sorted_names: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            visited.add(name)
            return
        visiting.add(name)
        for dep in deps.get(name, set()):
            visit(dep)
        visiting.discard(name)
        visited.add(name)
        sorted_names.append(name)

    for m in models:
        visit(m.table_name)

    non_link = [
        n for n in sorted_names if n not in link_tables and n in model_map
    ]
    link_list = [n for n in sorted_names if n in link_tables and n in model_map]

    result = link_list + non_link
    remaining_names = [
        m.table_name for m in models if m.table_name not in set(result)
    ]
    return [model_map[n] for n in result + remaining_names if n in model_map]


def generate_sqlmodel_code(
    schema: str,
    parsed_models: list[ParsedModel],
    relationship_metadata: RelationshipMetadata,
    pk_map: dict[tuple[str, str], list[str]],
) -> str:
    """Generate a complete Python module with SQLModel table classes."""
    fks = relationship_metadata.foreign_keys
    link_tables = relationship_metadata.link_tables

    fk_by_source: dict[str, list[ForeignKeyInfo]] = defaultdict(list)
    fk_by_target: dict[str, list[ForeignKeyInfo]] = defaultdict(list)
    for fk in fks:
        fk_by_source[fk.source_table].append(fk)
        fk_by_target[fk.target_table].append(fk)

    models_with_pks = [
        m for m in parsed_models if pk_map.get((schema, m.table_name))
    ]
    sorted_models = _topological_sort(models_with_pks, fks, link_tables)
    table_names = {m.table_name for m in sorted_models}
    sa_imports: set[str] = set()
    needs_relationship = False

    class_blocks: list[str] = []

    for model in sorted_models:
        table = model.table_name
        class_name = _table_to_class(table)
        pks = pk_map.get((schema, table), [])
        table_fks = {
            col: fk
            for fk in fk_by_source.get(table, [])
            for col in fk.source_columns
            if len(fk.source_columns) == 1
        }

        lines = [
            f"class {class_name}(SQLModel, table=True):",
            f'    __tablename__ = "{table}"',
            f'    __table_args__ = {{"schema": "{schema}", "extend_existing": True}}',
            "",
        ]

        for field_info in model.fields:
            line = _generate_field_line(field_info, pks, table_fks, sa_imports)
            lines.append(f"    {line}")

        field_names = {f.name for f in model.fields}
        rel_lines = _generate_relationships(
            table,
            class_name,
            fk_by_source,
            fk_by_target,
            link_tables,
            table_names,
            schema,
            field_names,
        )
        if rel_lines:
            needs_relationship = True
            lines.append("")
            for rl in rel_lines:
                lines.append(f"    {rl}")

        class_blocks.append("\n".join(lines))

    header = _generate_header(schema, sa_imports, needs_relationship)
    return header + "\n\n\n" + "\n\n\n".join(class_blocks) + "\n"


def _generate_field_line(
    field_info: ParsedField,
    pks: list[str],
    table_fks: dict[str, ForeignKeyInfo],
    sa_imports: set[str],
) -> str:
    mapped = map_pydantic_type(
        field_info.type_annotation, field_info.is_optional
    )
    if mapped.needs_import:
        sa_imports.update(mapped.needs_import)

    is_pk = field_info.name in pks
    fk = table_fks.get(field_info.name)

    field_args: list[str] = []

    if is_pk:
        field_args.append("primary_key=True")

    if fk:
        target = (
            f"{fk.target_table}.{fk.target_columns[0]}"
            if fk.target_columns
            else f"{fk.target_table}.id"
        )
        if fk.target_schema != fk.schema:
            target = f"{fk.target_schema}.{target}"
        field_args.append(f'foreign_key="{target}"')

    if field_info.is_optional and not is_pk:
        field_args.append("default=None")

    if mapped.sa_type:
        field_args.append(f"sa_type={mapped.sa_type}")

    python_type = mapped.python_type
    if not field_args:
        return f"{field_info.name}: {python_type}"

    return f"{field_info.name}: {python_type} = Field({', '.join(field_args)})"


def _dedupe_name(name: str, used: set[str], column_names: set[str]) -> str:
    """Ensure name doesn't collide with existing column names or already-used relationship names."""
    candidate = name
    if candidate in column_names or candidate in used:
        candidate = f"{candidate}_rel"
    suffix = 2
    while candidate in used:
        candidate = f"{name}_rel{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _generate_relationships(
    table: str,
    class_name: str,
    fk_by_source: dict[str, list[ForeignKeyInfo]],
    fk_by_target: dict[str, list[ForeignKeyInfo]],
    link_tables: set[str],
    all_tables: set[str],
    schema: str,
    column_names: set[str] | None = None,
) -> list[str]:
    """Generate Relationship() lines for a model."""
    lines: list[str] = []
    if column_names is None:
        column_names = set()

    if table in link_tables:
        return lines

    used_names: set[str] = set()

    for fk in fk_by_source.get(table, []):
        if len(fk.source_columns) != 1:
            continue
        if fk.target_table not in all_tables:
            continue
        if fk.target_table in link_tables:
            continue

        target_class = _table_to_class(fk.target_table)
        rel_name = _fk_col_to_rel_name(fk.source_columns[0])
        back_name = _pluralize(table)

        rel_name = _dedupe_name(rel_name, used_names, column_names)
        back_name = _dedupe_name(back_name, set(), set())

        lines.append(
            f'{rel_name}: {target_class} | None = Relationship(back_populates="{back_name}")'
        )

    for fk in fk_by_target.get(table, []):
        if len(fk.source_columns) != 1:
            continue
        if fk.source_table not in all_tables:
            continue

        source_class = _table_to_class(fk.source_table)

        if fk.source_table in link_tables:
            _add_m2m_relationship(
                lines,
                table,
                class_name,
                fk,
                fk_by_source,
                link_tables,
                all_tables,
                used_names,
                column_names,
            )
            continue

        back_name = _fk_col_to_rel_name(fk.source_columns[0])
        base_rel_name = _pluralize(fk.source_table)
        fk_hint = _fk_col_to_rel_name(fk.source_columns[0])
        if base_rel_name in used_names or base_rel_name in column_names:
            base_rel_name = f"{fk_hint}_{base_rel_name}"

        rel_name = _dedupe_name(base_rel_name, used_names, column_names)

        if fk.is_one_to_one:
            lines.append(
                f'{rel_name}: {source_class} | None = Relationship(back_populates="{back_name}")'
            )
        else:
            lines.append(
                f'{rel_name}: list[{source_class}] = Relationship(back_populates="{back_name}")'
            )

    return lines


def _add_m2m_relationship(
    lines: list[str],
    table: str,
    class_name: str,
    fk: ForeignKeyInfo,
    fk_by_source: dict[str, list[ForeignKeyInfo]],
    link_tables: set[str],
    all_tables: set[str],
    used_names: set[str] | None = None,
    column_names: set[str] | None = None,
) -> None:
    """Add M2M relationship through a link table."""
    if used_names is None:
        used_names = set()
    if column_names is None:
        column_names = set()

    link_table = fk.source_table
    link_class = _table_to_class(link_table)

    link_fks = fk_by_source.get(link_table, [])
    other_fks = [f for f in link_fks if f.target_table != table]

    for other_fk in other_fks:
        other_table = other_fk.target_table
        if other_table not in all_tables or other_table in link_tables:
            continue
        other_class = _table_to_class(other_table)
        rel_name = _dedupe_name(
            _pluralize(other_table), used_names, column_names
        )
        back_name = _pluralize(table)

        lines.append(
            f"{rel_name}: list[{other_class}] = Relationship("
            f'back_populates="{back_name}", link_model={link_class})'
        )


def _generate_header(
    schema: str,
    sa_imports: set[str],
    needs_relationship: bool,
) -> str:
    lines = [
        '"""',
        f'Auto-generated SQLModel models for schema "{schema}".',
        "",
        "DO NOT EDIT - regenerate with:",
        "  python -m backend.scripts.supabase_type_generation.supabase_db_to_sql_models",
        '"""',
        "from __future__ import annotations",
        "",
        "import datetime",
        "import uuid",
        "",
    ]

    sa_from_main: list[str] = []
    sa_from_pg: list[str] = []

    for imp in sorted(sa_imports):
        if imp in ("JSONB", "PG_UUID"):
            if imp == "JSONB":
                sa_from_pg.append(
                    "from sqlalchemy.dialects.postgresql import JSONB"
                )
            elif imp == "PG_UUID":
                sa_from_pg.append(
                    "from sqlalchemy.dialects.postgresql import UUID as PG_UUID"
                )
        else:
            sa_from_main.append(imp)

    if sa_from_main:
        lines.append(
            f"from sqlalchemy import {', '.join(sorted(sa_from_main))}"
        )
    for pg_line in sa_from_pg:
        lines.append(pg_line)

    if sa_from_main or sa_from_pg:
        lines.append("")

    sqlmodel_imports = ["Field", "SQLModel"]
    if needs_relationship:
        sqlmodel_imports.append("Relationship")
    lines.append(f"from sqlmodel import {', '.join(sorted(sqlmodel_imports))}")

    return "\n".join(lines)
