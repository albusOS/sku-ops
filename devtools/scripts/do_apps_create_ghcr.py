#!/usr/bin/env python3
"""Create a DigitalOcean App from the App Platform spec when GHCR image is private.

The committed ``.do/app.yaml`` is a **deploy template**: it contains ``$IMAGE_TAG``
and ``$PRIVATE_*`` placeholders for CI. For a one-off ``doctl apps create``, render
first (same ``envsubst`` variable list as ``.github/workflows/deploy.yml``) or
replace placeholders with literal values, then point ``--spec`` at the rendered file.

App Platform needs pull credentials on the image: ``username:token`` where
``token`` is a GitHub PAT with ``read:packages`` (classic) or fine-grained with
Packages read for the org/user that owns the GHCR package.

  export GHCR_REGISTRY_CREDS='your_github_username:ghp_xxxxxxxx'
  # from repo root; uv --directory backend uses backend/ as cwd, so use ../devtools/...
  pixi run uv run --directory backend python ../devtools/scripts/do_apps_create_ghcr.py

Or make the ``ghcr.io/<owner>/sku-ops-backend`` package public in GitHub
(Package settings) and run ``doctl apps create --spec .do/app.yaml`` with no
registry_credentials (still requires a renderable spec without ``$`` placeholders).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repo root (default: parent of devtools/)",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="App spec (default: <repo-root>/.do/app.yaml)",
    )
    args = parser.parse_args()
    root: Path = args.repo_root
    spec_path = args.spec or root / ".do/app.yaml"
    creds = os.environ.get("GHCR_REGISTRY_CREDS", "").strip()
    if not creds:
        raise SystemExit(
            "Set GHCR_REGISTRY_CREDS='github_username:pat_with_read_packages' "
            "(see script docstring)."
        )

    doc = yaml.safe_load(spec_path.read_text())
    doc["services"][0]["image"]["registry_credentials"] = creds

    text = yaml.safe_dump(doc, sort_keys=False)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    doctl = shutil.which("doctl")
    if not doctl:
        raise SystemExit("doctl not found in PATH")
    try:
        subprocess.run(  # noqa: S603
            [doctl, "apps", "create", "--spec", tmp_path],
            check=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
