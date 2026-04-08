#!/usr/bin/env python3
"""Scaffold a new database service and register it on DatabaseManager.

Usage (from repo root):
    pixi run uv run --directory backend python .cursor/skills/use-database/scripts/add_database_service.py <context>

Example:
    pixi run uv run --directory backend python .cursor/skills/use-database/scripts/add_database_service.py reports

Creates:
    backend/shared/infrastructure/db/services/<context>/
        __init__.py
        <context>.py

Updates:
    backend/shared/infrastructure/db/services/__init__.py  (re-export)
    backend/shared/infrastructure/db/base.py               (registration + TYPE_CHECKING stubs)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVICES_DIR = REPO_ROOT / "backend" / "shared" / "infrastructure" / "db" / "services"
BASE_PY = REPO_ROOT / "backend" / "shared" / "infrastructure" / "db" / "base.py"
SERVICES_INIT = SERVICES_DIR / "__init__.py"


def _to_pascal(name: str) -> str:
    return "".join(word.capitalize() for word in name.split("_"))


def _validate_context(name: str) -> None:
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        print(f"Error: context name must be lowercase alphanumeric/underscore, got '{name}'")
        sys.exit(1)

    if (SERVICES_DIR / name).exists():
        print(f"Error: service package already exists at {SERVICES_DIR / name}")
        sys.exit(1)


def _create_service_package(context: str, class_name: str) -> None:
    pkg_dir = SERVICES_DIR / context
    pkg_dir.mkdir(parents=True)

    init = pkg_dir / "__init__.py"
    init.write_text(
        f"from shared.infrastructure.db.services.{context}.{context} import (\n"
        f"    {class_name},\n"
        f")\n"
        f"\n"
        f'__all__ = ["{class_name}"]\n'
    )

    impl = pkg_dir / f"{context}.py"
    impl.write_text(
        f'"""Database service for the {context} bounded context."""\n'
        f"\n"
        f"from __future__ import annotations\n"
        f"\n"
        f"from typing import TYPE_CHECKING\n"
        f"\n"
        f"from shared.infrastructure.db.services._base import DomainDatabaseService\n"
        f"\n"
        f"if TYPE_CHECKING:\n"
        f"    pass\n"
        f"\n"
        f"\n"
        f"class {class_name}(DomainDatabaseService):\n"
        f'    """Persistence facade for {context}."""\n'
        f"\n"
        f"    pass\n"
    )

    print(f"  Created {pkg_dir.relative_to(REPO_ROOT)}/")


def _update_services_init(context: str, class_name: str) -> None:
    text = SERVICES_INIT.read_text()

    import_line = f"from shared.infrastructure.db.services.{context} import (\n    {class_name},\n)"
    if class_name in text:
        print(f"  services/__init__.py already has {class_name}, skipping")
        return

    last_import = text.rfind("\nfrom shared.infrastructure.db.services.")
    if last_import == -1:
        print("  Warning: could not find import block in services/__init__.py")
        return

    end_of_line = text.index("\n", text.index(")", last_import)) + 1
    text = text[:end_of_line] + import_line + "\n" + text[end_of_line:]

    all_match = re.search(r"__all__\s*=\s*\[([^\]]*)\]", text, re.DOTALL)
    if all_match:
        entries = re.findall(r'"(\w+)"', all_match.group(1))
        entries.append(class_name)
        entries.sort()
        new_all = "__all__ = [\n" + "".join(f'    "{e}",\n' for e in entries) + "]"
        text = text[: all_match.start()] + new_all + text[all_match.end() :]

    SERVICES_INIT.write_text(text)
    print("  Updated services/__init__.py")


def _update_base_py(context: str, class_name: str) -> None:
    text = BASE_PY.read_text()

    if f'"{context}"' in text and class_name in text:
        print(f"  base.py already has {context}/{class_name}, skipping")
        return

    tc_import = (
        f"    from shared.infrastructure.db.services.{context} import (\n"
        f"        {class_name},\n"
        f"    )"
    )
    marker = "if TYPE_CHECKING:"
    first_tc = text.index(marker)
    block_end = text.index("\n\n", first_tc)
    if class_name not in text[:block_end]:
        text = text[:block_end] + "\n" + tc_import + text[block_end:]

    service_path_entry = (
        f'            "{context}": "shared.infrastructure.db.services.{context}.{class_name}",'
    )
    anchor = '"sql": "shared.infrastructure.db.services.raw_sql.RawSQLService"'
    pos = text.index(anchor)
    line_start = text.rindex("\n", 0, pos) + 1
    text = text[:line_start] + service_path_entry + "\n" + text[line_start:]

    def _add_type_stub(text: str, class_header: str) -> str:
        idx = text.index(class_header)
        tc_block_start = text.index("if TYPE_CHECKING:", idx)
        tc_block_end = text.index("\n\n", tc_block_start)
        stub = f"        {context}: {class_name}"
        if stub not in text[tc_block_start:tc_block_end]:
            text = text[:tc_block_end] + "\n" + stub + text[tc_block_end:]
        return text

    text = _add_type_stub(text, "class TransactionScope:")
    text = _add_type_stub(text, "class DatabaseManager:")

    BASE_PY.write_text(text)
    print("  Updated base.py (service path + TYPE_CHECKING stubs)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new database service and register it on DatabaseManager",
    )
    parser.add_argument("context", help="Lowercase bounded-context key (e.g. reports)")
    args = parser.parse_args()

    context: str = args.context.lower().strip()
    class_name = f"{_to_pascal(context)}DatabaseService"

    print(f"Adding database service: {context} -> {class_name}")
    _validate_context(context)
    _create_service_package(context, class_name)
    _update_services_init(context, class_name)
    _update_base_py(context, class_name)
    print("\nDone. Run 'pixi run lint backend' to verify.")


if __name__ == "__main__":
    main()
