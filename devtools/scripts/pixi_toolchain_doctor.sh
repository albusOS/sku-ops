#!/usr/bin/env bash
# Fail if core dev tools do not resolve from the active pixi environment (CONDA_PREFIX).
# Run: pixi run doctor
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

FAIL=0
PIXI_PREFIX="${CONDA_PREFIX:-}"

if [[ -z "$PIXI_PREFIX" ]]; then
  echo "FAIL: CONDA_PREFIX is empty (run via: pixi run doctor)"
  exit 1
fi

check_cmd() {
  local cmd=$1
  local path
  path=$(command -v "$cmd" 2>/dev/null || true)
  if [[ -z "$path" ]]; then
    echo "FAIL: $cmd not found on PATH"
    FAIL=1
  elif [[ "$path" != "$PIXI_PREFIX"/* ]]; then
    echo "FAIL: $cmd -> $path (expected under $PIXI_PREFIX)"
    FAIL=1
  else
    echo "  OK: $cmd -> $path"
  fi
}

echo "=== Pixi toolchain doctor ==="
echo "CONDA_PREFIX=$PIXI_PREFIX"
echo ""

check_cmd python
check_cmd uv
check_cmd node
check_cmd pnpm

echo ""
echo "=== uv Python resolution ==="
UV_PY=$(uv python find 2>/dev/null || true)
if [[ -z "$UV_PY" ]]; then
  echo "FAIL: uv python find returned nothing"
  FAIL=1
elif [[ "$UV_PY" != "$PIXI_PREFIX"/* ]]; then
  echo "FAIL: uv python find -> $UV_PY (expected under $PIXI_PREFIX)"
  FAIL=1
else
  echo "  OK: uv python find -> $UV_PY"
fi

if [[ -f backend/.venv/bin/python ]]; then
  echo ""
  echo "=== backend/.venv check ==="
  VENV_PY=$(UV_PYTHON= "$PIXI_PREFIX/bin/python" -c "import os; print(os.path.realpath('$ROOT/backend/.venv/bin/python'))")
  if [[ "$VENV_PY" == "$PIXI_PREFIX"/* ]]; then
    echo "  OK: backend/.venv/bin/python resolves -> $VENV_PY"
  else
    echo "FAIL: backend/.venv/bin/python resolves -> $VENV_PY (expected under $PIXI_PREFIX; run: pixi run uv sync --dev --directory backend)"
    FAIL=1
  fi
else
  echo ""
  echo "=== backend/.venv check ==="
  echo "  SKIP: backend/.venv not present yet (run: pixi run uv sync --dev --directory backend)"
fi

echo ""
if [[ $FAIL -ne 0 ]]; then
  echo "FAILED: toolchain checks did not pass. Run: pixi install"
  exit 1
fi
echo "ALL OK: python, uv, node, and pnpm resolve from pixi; uv uses pixi Python"
