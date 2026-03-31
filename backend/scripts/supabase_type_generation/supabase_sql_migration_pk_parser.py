"""Step 2b: Extract primary key info from SQL migration files.

Lightweight regex parser that identifies PK columns per table.
Does NOT parse FKs, types, or constraints - the TS file handles those.
"""

from __future__ import annotations

import re
from pathlib import Path


def extract_primary_keys(
    migrations_dir: Path,
) -> dict[tuple[str, str], list[str]]:
    """Parse SQL migrations and return PK columns keyed by (schema, table).

    Handles:
    - Inline PKs: `id TEXT PRIMARY KEY`
    - Composite PKs: `PRIMARY KEY (col_a, col_b)`
    - Schema-qualified tables: `CREATE TABLE schema.table`
    - Default schema is 'public' for unqualified table names
    """
    pk_map: dict[tuple[str, str], list[str]] = {}

    sql_files = sorted(migrations_dir.glob("*.sql"))
    for sql_file in sql_files:
        content = sql_file.read_text()
        _parse_sql_content(content, pk_map)

    return pk_map


def _parse_sql_content(
    content: str,
    pk_map: dict[tuple[str, str], list[str]],
) -> None:
    create_table_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:(\w+)\.)?(\w+)\s*\(",
        re.IGNORECASE,
    )

    for match in create_table_pattern.finditer(content):
        schema = (match.group(1) or "public").lower()
        table_name = match.group(2).lower()
        table_start = match.end() - 1

        paren_end = _find_closing_paren(content, table_start)
        if paren_end == -1:
            continue

        table_body = content[table_start + 1 : paren_end]
        pk_columns = _extract_pks_from_body(table_body)

        if pk_columns:
            pk_map[(schema, table_name)] = pk_columns


def _find_closing_paren(content: str, start: int) -> int:
    depth = 0
    for i in range(start, len(content)):
        if content[i] == "(":
            depth += 1
        elif content[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _extract_pks_from_body(body: str) -> list[str]:
    """Extract PK columns from a CREATE TABLE body."""
    pk_columns: list[str] = []

    composite_pk = re.search(
        r"PRIMARY\s+KEY\s*\(([^)]+)\)",
        body,
        re.IGNORECASE,
    )
    if composite_pk:
        cols = composite_pk.group(1)
        return [c.strip().lower() for c in cols.split(",")]

    for line in body.split("\n"):
        line = line.strip().rstrip(",")
        if not line or line.startswith("--"):
            continue
        if re.search(r"\bPRIMARY\s+KEY\b", line, re.IGNORECASE):
            col_match = re.match(r"(\w+)\s+", line)
            if col_match:
                pk_columns.append(col_match.group(1).lower())

    return pk_columns
