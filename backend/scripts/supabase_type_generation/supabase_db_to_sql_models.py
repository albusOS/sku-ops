"""Orchestrator: Generate schema-prefixed SQLModel files from Supabase.

Chains all pipeline steps:
1. Run supabase gen types (Python + TypeScript)
2. Parse Pydantic models per schema
3. Parse TS relationships per schema
4. Extract primary keys from SQL migrations
5. Generate {schema}_sql_model_models.py per schema
6. Format with ruff
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from backend.scripts.supabase_type_generation.schema_config import (
    SCHEMA_CLASS_PREFIX,
    SCHEMAS,
)
from backend.scripts.supabase_type_generation.supabase_pydantic_models_to_sql_models import (
    generate_sqlmodel_code,
)
from backend.scripts.supabase_type_generation.supabase_sql_migration_pk_parser import (
    extract_primary_keys,
)
from backend.scripts.supabase_type_generation.supabase_ts_relationship_parser import (
    parse_ts_relationships,
)
from backend.scripts.supabase_type_generation.supabase_types_to_pydantic_models import (
    parse_pydantic_types,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
TYPES_DIR = BACKEND_ROOT / "shared" / "infrastructure" / "types"
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"


def _strip_cli_noise(content: str) -> str:
    import re

    lines = content.split("\n")
    return "\n".join(line for line in lines if not re.match(r"^Connecting to db \d+", line))


def run_supabase_gen_types(lang: str, local: bool = True) -> str:
    cmd = ["supabase", "gen", "types", f"--lang={lang}"]
    if local:
        cmd.append("--local")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=str(PROJECT_ROOT),
    )
    return _strip_cli_noise(result.stdout)


def main(
    local: bool = True,
    schemas: list[str] | None = None,
    types_dir: Path | None = None,
    skip_cli: bool = False,
) -> None:
    if schemas is None:
        schemas = list(SCHEMAS)
    if types_dir is None:
        types_dir = TYPES_DIR

    types_dir.mkdir(parents=True, exist_ok=True)
    init_file = types_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    if skip_cli:
        print("Skipping supabase CLI - reading existing type files...")
        full_py = ""
        full_ts = ""
        for schema in schemas:
            py_path = types_dir / f"{schema}_database_types.py"
            ts_path = types_dir / f"{schema}_database_types.ts"
            if py_path.exists():
                full_py = py_path.read_text()
            if ts_path.exists():
                full_ts = ts_path.read_text()
    else:
        print("Generating Python types from supabase...")
        full_py = run_supabase_gen_types(lang="python", local=local)
        print("Generating TypeScript types from supabase...")
        full_ts = run_supabase_gen_types(lang="typescript", local=local)

        for schema in schemas:
            py_path = types_dir / f"{schema}_database_types.py"
            ts_path = types_dir / f"{schema}_database_types.ts"
            py_path.write_text(full_py)
            ts_path.write_text(full_ts)
            print(f"  Wrote {py_path.name} and {ts_path.name}")

    print("Extracting primary keys from SQL migrations...")
    pk_map = extract_primary_keys(MIGRATIONS_DIR)
    print(f"  Found PKs for {len(pk_map)} tables")

    for schema in schemas:
        prefix = SCHEMA_CLASS_PREFIX.get(schema, schema.capitalize())
        print(f"\nProcessing schema: {schema} (prefix={prefix})")

        print("  Parsing Pydantic models...")
        parsed_models = parse_pydantic_types(full_py, schema, prefix)
        print(f"  Found {len(parsed_models)} models")

        print("  Parsing TS relationships...")
        rel_metadata = parse_ts_relationships(full_ts, schema, schemas)
        print(
            f"  Found {len(rel_metadata.foreign_keys)} FKs, {len(rel_metadata.link_tables)} link tables"
        )

        print("  Generating SQLModel code...")
        code = generate_sqlmodel_code(schema, parsed_models, rel_metadata, pk_map)

        output_path = types_dir / f"{schema}_sql_model_models.py"
        output_path.write_text(code)
        print(f"  Wrote {output_path.name} ({len(code)} bytes)")

    print("\nFormatting with ruff...")
    _format_with_ruff(types_dir, schemas)
    print("Done!")


def _format_with_ruff(types_dir: Path, schemas: list[str]) -> None:
    files_to_format = []
    for schema in schemas:
        model_file = types_dir / f"{schema}_sql_model_models.py"
        if model_file.exists():
            files_to_format.append(str(model_file))

    if not files_to_format:
        return

    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "format", *files_to_format],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            print(f"  Warning: ruff format failed: {result.stderr.strip()}")
    except FileNotFoundError:
        try:
            result = subprocess.run(
                ["ruff", "format", *files_to_format],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  Warning: ruff format failed: {result.stderr.strip()}")
        except FileNotFoundError:
            print("  Warning: ruff not found, skipping formatting")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate SQLModel classes from Supabase schema",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        default=True,
        help="Use local Supabase instance (default)",
    )
    parser.add_argument(
        "--schemas",
        type=str,
        default=None,
        help="Comma-separated schemas to process (default: from schema_config)",
    )
    parser.add_argument(
        "--types-dir",
        type=str,
        default=None,
        help="Output directory for generated types",
    )
    parser.add_argument(
        "--skip-cli",
        action="store_true",
        default=False,
        help="Skip supabase CLI and use existing type files",
    )
    args = parser.parse_args()

    schema_list = args.schemas.split(",") if args.schemas else None
    types_path = Path(args.types_dir) if args.types_dir else None

    main(
        local=args.local,
        schemas=schema_list,
        types_dir=types_path,
        skip_cli=args.skip_cli,
    )
