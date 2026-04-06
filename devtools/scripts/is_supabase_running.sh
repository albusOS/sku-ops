#!/usr/bin/env bash
# is_supabase_running.sh — exit 0 if local Supabase is up; otherwise start it (pixi internal task; no shell redirects in pixi.toml).
set -euo pipefail
if supabase status -o env >/dev/null 2>&1; then
  exit 0
fi
exec supabase start
