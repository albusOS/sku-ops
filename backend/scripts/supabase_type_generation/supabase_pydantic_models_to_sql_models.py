"""Step 3: Generate SQLModel classes from parsed Pydantic models + relationship metadata.

Produces one {schema}_sql_model_models.py file per schema with:
- SQLModel table classes with proper Field() definitions
- Foreign key declarations via Field(foreign_key="table.column")
- Relationship() attributes with back_populates
- M2M relationships via link_model=
- Topological ordering (parents before children)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.scripts.supabase_type_generation.pydantic_to_sql_model_type_mapping import (
    map_pydantic_type,
)

if TYPE_CHECKING:
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
    base = fk_column.removesuffix("_id")
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
        if fk.source_table in model_map and fk.target_table in model_map and fk.source_table != fk.target_table:
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

    non_link = [n for n in sorted_names if n not in link_tables and n in model_map]
    link_list = [n for n in sorted_names if n in link_tables and n in model_map]

    result = link_list + non_link
    remaining_names = [m.table_name for m in models if m.table_name not in set(result)]
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

    models_with_pks = [m for m in parsed_models if pk_map.get((schema, m.table_name))]
    sorted_models = _topological_sort(models_with_pks, fks, link_tables)
    table_names = {m.table_name for m in sorted_models}
    table_columns = {model.table_name: {field.name for field in model.fields} for model in sorted_models}
    relationship_plan = _plan_relationships(
        fk_by_source=fk_by_source,
        fk_by_target=fk_by_target,
        link_tables=link_tables,
        table_names=table_names,
        table_columns=table_columns,
    )
    sa_imports: set[str] = set()
    needs_relationship = False
    m2m_name_map: dict[tuple[str, str, str], str] = {}

    class_blocks: list[str] = []

    for model in sorted_models:
        table = model.table_name
        class_name = _table_to_class(table)
        pks = pk_map.get((schema, table), [])
        table_fks = {
            col: fk for fk in fk_by_source.get(table, []) for col in fk.source_columns if len(fk.source_columns) == 1
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
            relationship_plan,
            field_names,
            m2m_name_map,
        )
        if rel_lines:
            needs_relationship = True
            lines.append("")
            lines.extend(f"    {rl}" for rl in rel_lines)

        class_blocks.append("\n".join(lines))

    header = _generate_header(schema, sa_imports, needs_relationship)
    return header + "\n\n\n" + "\n\n\n".join(class_blocks) + "\n"


def _generate_field_line(
    field_info: ParsedField,
    pks: list[str],
    table_fks: dict[str, ForeignKeyInfo],
    sa_imports: set[str],
) -> str:
    mapped = map_pydantic_type(field_info.type_annotation, field_info.is_optional)
    if mapped.needs_import:
        sa_imports.update(mapped.needs_import)

    is_pk = field_info.name in pks
    fk = table_fks.get(field_info.name)

    field_args: list[str] = []

    if is_pk:
        field_args.append("primary_key=True")

    if fk:
        target_column = fk.target_columns[0] if fk.target_columns else "id"
        target = f"{fk.target_table}.{target_column}"
        target_schema = fk.target_schema or fk.schema
        if target_schema:
            target = f"{target_schema}.{target}"
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


def _collection_annotation(class_name: str) -> str:
    """Render SQLModel collection annotations as quoted forward refs."""
    return f'list["{class_name}"]'


def _optional_relationship_annotation(class_name: str) -> str:
    """Render scalar SQLModel relationship annotations as forward refs."""
    return f'Optional["{class_name}"]'


@dataclass(frozen=True)
class RelationshipPlan:
    source_name_by_constraint: dict[str, str]
    target_name_by_constraint: dict[str, str]
    explicit_foreign_keys: set[str]
    self_referential_constraints: set[str]


def _plan_relationships(
    fk_by_source: dict[str, list[ForeignKeyInfo]],
    fk_by_target: dict[str, list[ForeignKeyInfo]],
    link_tables: set[str],
    table_names: set[str],
    table_columns: dict[str, set[str]],
) -> RelationshipPlan:
    source_name_by_constraint: dict[str, str] = {}
    target_name_by_constraint: dict[str, str] = {}

    relevant_fks = [
        fk
        for table in sorted(table_names)
        for fk in fk_by_source.get(table, [])
        if len(fk.source_columns) == 1
        and fk.source_table in table_names
        and fk.target_table in table_names
        and fk.source_table not in link_tables
        and fk.target_table not in link_tables
    ]
    relevant_keys = {fk.constraint_name for fk in relevant_fks}

    for table in sorted(table_names):
        used_names: set[str] = set()
        column_names = table_columns.get(table, set())
        for fk in fk_by_source.get(table, []):
            if fk.constraint_name not in relevant_keys:
                continue
            base_name = _fk_col_to_rel_name(fk.source_columns[0])
            source_name_by_constraint[fk.constraint_name] = _dedupe_name(base_name, used_names, column_names)

    for table in sorted(table_names):
        used_names: set[str] = set()
        column_names = table_columns.get(table, set())
        for fk in fk_by_target.get(table, []):
            if fk.constraint_name not in relevant_keys:
                continue
            base_name = _pluralize(fk.source_table)
            fk_hint = _fk_col_to_rel_name(fk.source_columns[0])
            if base_name in used_names or base_name in column_names:
                base_name = f"{fk_hint}_{base_name}"
            target_name_by_constraint[fk.constraint_name] = _dedupe_name(base_name, used_names, column_names)

    pair_counts = Counter((fk.source_table, fk.target_table) for fk in relevant_fks)
    explicit_foreign_keys = {
        fk.constraint_name for fk in relevant_fks if pair_counts[(fk.source_table, fk.target_table)] > 1
    }
    self_referential_constraints = {fk.constraint_name for fk in relevant_fks if fk.source_table == fk.target_table}

    return RelationshipPlan(
        source_name_by_constraint=source_name_by_constraint,
        target_name_by_constraint=target_name_by_constraint,
        explicit_foreign_keys=explicit_foreign_keys,
        self_referential_constraints=self_referential_constraints,
    )


def _relationship_call(
    *,
    back_populates: str,
    link_model: str | None = None,
    foreign_keys: str | None = None,
    remote_side: str | None = None,
) -> str:
    args = [f'back_populates="{back_populates}"']
    if link_model is not None:
        args.append(f"link_model={link_model}")

    sa_kwargs: list[str] = []
    if foreign_keys is not None:
        sa_kwargs.append(f'"foreign_keys": "{foreign_keys}"')
    if remote_side is not None:
        sa_kwargs.append(f'"remote_side": "{remote_side}"')
    if sa_kwargs:
        args.append(f"sa_relationship_kwargs={{{', '.join(sa_kwargs)}}}")

    return f"Relationship({', '.join(args)})"


def _generate_relationships(
    table: str,
    class_name: str,
    fk_by_source: dict[str, list[ForeignKeyInfo]],
    fk_by_target: dict[str, list[ForeignKeyInfo]],
    link_tables: set[str],
    all_tables: set[str],
    schema: str,
    relationship_plan: RelationshipPlan,
    column_names: set[str] | None = None,
    m2m_name_map: dict[tuple[str, str, str], str] | None = None,
) -> list[str]:
    """Generate Relationship() lines for a model."""
    lines: list[str] = []
    if column_names is None:
        column_names = set()
    if m2m_name_map is None:
        m2m_name_map = {}

    if table in link_tables:
        return lines

    for fk in fk_by_source.get(table, []):
        if len(fk.source_columns) != 1:
            continue
        if fk.target_table not in all_tables:
            continue
        if fk.target_table in link_tables:
            continue

        target_class = _table_to_class(fk.target_table)
        rel_name = relationship_plan.source_name_by_constraint[fk.constraint_name]
        back_name = relationship_plan.target_name_by_constraint[fk.constraint_name]
        foreign_keys = None
        remote_side = None
        if fk.constraint_name in relationship_plan.explicit_foreign_keys:
            foreign_keys = f"{class_name}.{fk.source_columns[0]}"
        if fk.constraint_name in relationship_plan.self_referential_constraints:
            foreign_keys = f"{class_name}.{fk.source_columns[0]}"
            remote_side = f"{target_class}.{fk.target_columns[0]}"

        lines.append(
            f"{rel_name}: {_optional_relationship_annotation(target_class)} = "
            f"{_relationship_call(back_populates=back_name, foreign_keys=foreign_keys, remote_side=remote_side)}"
        )

    used_names: set[str] = set()
    for fk in fk_by_target.get(table, []):
        if fk.constraint_name in relationship_plan.target_name_by_constraint:
            used_names.add(relationship_plan.target_name_by_constraint[fk.constraint_name])
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
                m2m_name_map,
            )
            continue

        rel_name = relationship_plan.target_name_by_constraint[fk.constraint_name]
        back_name = relationship_plan.source_name_by_constraint[fk.constraint_name]
        foreign_keys = None
        if fk.constraint_name in relationship_plan.explicit_foreign_keys:
            foreign_keys = f"{source_class}.{fk.source_columns[0]}"

        if fk.is_one_to_one:
            lines.append(
                f"{rel_name}: {_optional_relationship_annotation(source_class)} = "
                f"{_relationship_call(back_populates=back_name, foreign_keys=foreign_keys)}"
            )
        else:
            lines.append(
                f"{rel_name}: {_collection_annotation(source_class)} = "
                f"{_relationship_call(back_populates=back_name, foreign_keys=foreign_keys)}"
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
    m2m_name_map: dict[tuple[str, str, str], str] | None = None,
) -> None:
    """Add M2M relationship through a link table."""
    if used_names is None:
        used_names = set()
    if column_names is None:
        column_names = set()
    if m2m_name_map is None:
        m2m_name_map = {}

    link_table = fk.source_table
    link_class = _table_to_class(link_table)

    link_fks = fk_by_source.get(link_table, [])
    other_fks = [f for f in link_fks if f.target_table != table]

    for other_fk in other_fks:
        other_table = other_fk.target_table
        if other_table not in all_tables or other_table in link_tables:
            continue
        other_class = _table_to_class(other_table)
        rel_name = _dedupe_name(_pluralize(other_table), used_names, column_names)
        m2m_name_map[(link_table, table, other_table)] = rel_name
        back_name = m2m_name_map.get((link_table, other_table, table), _pluralize(table))

        lines.append(
            f"{rel_name}: {_collection_annotation(other_class)} = Relationship("
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
        "import datetime",
        "import uuid",
        "",
    ]

    sa_from_main: list[str] = []
    sa_from_pg: list[str] = []

    for imp in sorted(sa_imports):
        if imp in ("JSONB", "PG_UUID"):
            if imp == "JSONB":
                sa_from_pg.append("from sqlalchemy.dialects.postgresql import JSONB")
            elif imp == "PG_UUID":
                sa_from_pg.append("from sqlalchemy.dialects.postgresql import UUID as PG_UUID")
        else:
            sa_from_main.append(imp)

    if sa_from_main:
        lines.append(f"from sqlalchemy import {', '.join(sorted(sa_from_main))}")
    lines.extend(sa_from_pg)

    if sa_from_main or sa_from_pg:
        lines.append("")

    if needs_relationship:
        lines.append("from typing import Optional")
        lines.append("")

    sqlmodel_imports = ["Field", "SQLModel"]
    if needs_relationship:
        sqlmodel_imports.append("Relationship")
    lines.append(f"from sqlmodel import {', '.join(sorted(sqlmodel_imports))}")

    return "\n".join(lines)
