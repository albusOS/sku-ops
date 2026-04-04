#!/usr/bin/env bash
# Start local Supabase if not already running (used by pixi tasks; avoids unsupported shell redirects in pixi.toml).
set -euo pipefail
if supabase status -o env >/dev/null 2>&1; then
  exit 0
fi
exec supabase start
