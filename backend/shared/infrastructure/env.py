"""Layered dotenv loading for backend processes.

File merge order (later files override earlier **for keys not set by the process**):

1. Repo root ``.env`` (optional)
2. ``backend/.env``
3. ``backend/.env.development`` or ``backend/.env.production``
   (which file is chosen from process ``PUBLIC_ENV`` in ``config`` before the first dotenv merge)
4. ``backend/.env.local``

Keys already present in ``os.environ`` when this module is first imported (platform,
shell, CI, Docker, ``pixi``) are never overwritten by dotenv files.

``PUBLIC_ENV=test`` uses the same filename bundle as development (``.env.development``)
so CI ``os.environ`` wins when set before import.

See ``docs/environment.md`` in the repo root.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Final

from dotenv import dotenv_values

_DEV_RELOAD_DEBOUNCE_S: Final[float] = 2.0

# Snapshot before any SKU-Ops dotenv runs: host / platform / CI always wins forever.
PROCESS_ENV_KEYS: Final[frozenset[str]] = frozenset(os.environ.keys())

_last_dev_reload_monotonic: float = 0.0


def find_backend_root() -> Path:
    """Locate ``backend/`` by finding the directory containing ``main.py``."""
    d = Path(__file__).resolve().parent
    for _ in range(10):
        if (d / "main.py").exists():
            return d
        d = d.parent
    return Path.cwd()


def dotenv_profile_for_runtime_env(env_name: str) -> str:
    """Return ``development`` or ``production`` for picking ``.env.<profile>``."""
    if env_name == "production":
        return "production"
    return "development"


def _merge_dotenv_paths(paths: list[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for p in paths:
        if not p.exists():
            continue
        layer = {k: v for k, v in dotenv_values(p).items() if v is not None}
        merged.update(layer)
    return merged


def _apply_merged_to_environ(merged: dict[str, str]) -> None:
    for k, v in merged.items():
        if k not in PROCESS_ENV_KEYS:
            os.environ[k] = v


def load_backend_dotenv_initial(backend_root: Path, *, env_name: str) -> None:
    """Merge layered env files; never overwrite keys set before ``import env``."""
    profile = dotenv_profile_for_runtime_env(env_name)
    paths = [
        backend_root.parent / ".env",
        backend_root / ".env",
        backend_root / f".env.{profile}",
        backend_root / ".env.local",
    ]
    _apply_merged_to_environ(_merge_dotenv_paths(paths))


def maybe_reload_backend_dotenv_development(backend_root: Path) -> None:
    """Debounced reload for ``PUBLIC_ENV=development``; same precedence rules as initial load."""
    global _last_dev_reload_monotonic
    now = time.monotonic()
    if now - _last_dev_reload_monotonic < _DEV_RELOAD_DEBOUNCE_S:
        return
    _last_dev_reload_monotonic = now
    paths = [
        backend_root / ".env",
        backend_root / ".env.development",
        backend_root / ".env.local",
    ]
    _apply_merged_to_environ(_merge_dotenv_paths(paths))
