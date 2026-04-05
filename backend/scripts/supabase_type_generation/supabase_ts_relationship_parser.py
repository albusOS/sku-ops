"""Step 2: Parse TypeScript Relationships arrays from supabase gen types --lang=typescript.

Extracts FK metadata (source/target table, columns, isOneToOne) per schema,
identifies M2M link tables, and builds a relationship graph.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ForeignKeyInfo:
    schema: str
    source_table: str
    source_columns: list[str]
    target_schema: str
    target_table: str
    target_columns: list[str]
    is_one_to_one: bool
    constraint_name: str


@dataclass
class RelationshipMetadata:
    schema: str
    foreign_keys: list[ForeignKeyInfo]
    link_tables: set[str] = field(default_factory=set)


def _find_matching(content: str, start_idx: int, open_char: str, close_char: str) -> int:
    depth = 0
    for idx in range(start_idx, len(content)):
        c = content[idx]
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                return idx
    return -1


def _strip_cli_noise(content: str) -> str:
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        if re.match(r"^Connecting to db \d+", line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _extract_table_row_fields(table_block: str) -> set[str]:
    """Extract field names from the Row: { ... } block of a table."""
    row_match = re.search(r"Row\s*:\s*\{", table_block)
    if not row_match:
        return set()
    start = row_match.end() - 1
    end = _find_matching(table_block, start, "{", "}")
    if end == -1:
        return set()
    row_block = table_block[start + 1 : end]
    return set(re.findall(r"(\w+)\s*:", row_block))


def parse_ts_relationships(
    content: str,
    schema_name: str,
    all_schemas: list[str] | None = None,
) -> RelationshipMetadata:
    """Parse Relationships arrays from TS type output for a specific schema."""
    content = _strip_cli_noise(content)

    if all_schemas is None:
        all_schemas = [schema_name]

    tables_in_schemas: dict[str, set[str]] = {}
    for s in all_schemas:
        schema_match = re.search(rf"(?<!\w){re.escape(s)}\s*:\s*\{{", content)
        if not schema_match:
            continue
        s_start = schema_match.end() - 1
        s_end = _find_matching(content, s_start, "{", "}")
        if s_end == -1:
            continue
        schema_block = content[s_start + 1 : s_end]
        tables_match = re.search(r"Tables\s*:\s*\{", schema_block)
        if not tables_match:
            continue
        t_start = tables_match.end() - 1
        t_end = _find_matching(schema_block, t_start, "{", "}")
        if t_end == -1:
            continue
        tables_block = schema_block[t_start + 1 : t_end]
        table_names = set()
        for tbl in re.finditer(r"(\w+)\s*:\s*\{", tables_block):
            table_names.add(tbl.group(1))
        tables_in_schemas[s] = table_names

    schema_match = re.search(rf"(?<!\w){re.escape(schema_name)}\s*:\s*\{{", content)
    if not schema_match:
        return RelationshipMetadata(schema=schema_name, foreign_keys=[])

    s_start = schema_match.end() - 1
    s_end = _find_matching(content, s_start, "{", "}")
    if s_end == -1:
        return RelationshipMetadata(schema=schema_name, foreign_keys=[])

    schema_block = content[s_start + 1 : s_end]
    tables_match = re.search(r"Tables\s*:\s*\{", schema_block)
    if not tables_match:
        return RelationshipMetadata(schema=schema_name, foreign_keys=[])

    t_start = tables_match.end() - 1
    t_end = _find_matching(schema_block, t_start, "{", "}")
    if t_end == -1:
        return RelationshipMetadata(schema=schema_name, foreign_keys=[])

    tables_block = schema_block[t_start + 1 : t_end]
    foreign_keys: list[ForeignKeyInfo] = []
    table_fk_columns: dict[str, set[str]] = {}
    table_row_fields: dict[str, set[str]] = {}

    table_pattern = re.compile(r"(\w+)\s*:\s*\{")
    for tbl in table_pattern.finditer(tables_block):
        ts_name = tbl.group(1)
        tb_start = tbl.end() - 1
        tb_end = _find_matching(tables_block, tb_start, "{", "}")
        if tb_end == -1:
            continue
        tbl_block = tables_block[tb_start + 1 : tb_end]

        row_fields = _extract_table_row_fields(tbl_block)
        table_row_fields[ts_name] = row_fields

        rel_start = re.search(r"Relationships\s*:\s*\[", tbl_block)
        if not rel_start:
            continue
        r_begin = rel_start.end() - 1
        r_end = _find_matching(tbl_block, r_begin, "[", "]")
        if r_end == -1:
            continue
        rels_block = tbl_block[r_begin + 1 : r_end]

        fk_cols_for_table: set[str] = set()
        i = 0
        while i < len(rels_block):
            if rels_block[i] != "{":
                i += 1
                continue
            obj_start = i
            obj_end = _find_matching(rels_block, obj_start, "{", "}")
            if obj_end == -1:
                break
            rel_obj = rels_block[obj_start : obj_end + 1]

            fk_name_match = re.search(r'foreignKeyName\s*:\s*"([^"]+)"', rel_obj)
            ref_rel_match = re.search(r'referencedRelation\s*:\s*"([^"]+)"', rel_obj)
            one_to_one_match = re.search(r"isOneToOne\s*:\s*(true|false)", rel_obj)
            cols_match = re.search(r"columns\s*:\s*\[", rel_obj)
            ref_cols_match = re.search(r"referencedColumns\s*:\s*\[", rel_obj)

            if not ref_rel_match or not cols_match or not ref_cols_match:
                i = obj_end + 1
                continue

            fk_name = fk_name_match.group(1) if fk_name_match else ""
            ref_table = ref_rel_match.group(1)
            is_one_to_one = (
                one_to_one_match.group(1).lower() == "true" if one_to_one_match else False
            )

            cols_begin = cols_match.end() - 1
            cols_end = _find_matching(rel_obj, cols_begin, "[", "]")
            ref_cols_begin = ref_cols_match.end() - 1
            ref_cols_end = _find_matching(rel_obj, ref_cols_begin, "[", "]")

            cols = re.findall(r'"([^"]+)"', rel_obj[cols_begin + 1 : cols_end])
            ref_cols = re.findall(r'"([^"]+)"', rel_obj[ref_cols_begin + 1 : ref_cols_end])

            fk_cols_for_table.update(cols)

            target_schema = schema_name
            current_tables = tables_in_schemas.get(schema_name, set())
            if ref_table not in current_tables:
                for other_schema in all_schemas:
                    if other_schema == schema_name:
                        continue
                    if ref_table in tables_in_schemas.get(other_schema, set()):
                        target_schema = other_schema
                        break

            foreign_keys.append(
                ForeignKeyInfo(
                    schema=schema_name,
                    source_table=ts_name,
                    source_columns=cols,
                    target_schema=target_schema,
                    target_table=ref_table,
                    target_columns=ref_cols,
                    is_one_to_one=is_one_to_one,
                    constraint_name=fk_name,
                )
            )

            i = obj_end + 1

        table_fk_columns[ts_name] = fk_cols_for_table

    link_tables: set[str] = set()
    for table_name, fk_cols in table_fk_columns.items():
        row_fields = table_row_fields.get(table_name, set())
        if not row_fields:
            continue
        if row_fields == fk_cols:
            link_tables.add(table_name)

    return RelationshipMetadata(
        schema=schema_name,
        foreign_keys=foreign_keys,
        link_tables=link_tables,
    )


def parse_from_file(
    path: Path,
    schema_name: str = "public",
    all_schemas: list[str] | None = None,
) -> RelationshipMetadata:
    content = path.read_text()
    return parse_ts_relationships(content, schema_name, all_schemas)
