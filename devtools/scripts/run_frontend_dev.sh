#!/usr/bin/env bash
# Load Supabase local URLs into VITE_* (same mapping as legacy bin/dev) then start Vite.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

_load_supabase_env() {
  while IFS='=' read -r key raw_value; do
    value="${raw_value%\"}"
    value="${value#\"}"
    case "$key" in
      API_URL)
        export SUPABASE_URL="${SUPABASE_URL:-$value}"
        export VITE_SUPABASE_URL="${VITE_SUPABASE_URL:-$value}"
        ;;
      DB_URL)
        export DATABASE_URL="${DATABASE_URL:-$value}"
        ;;
      PUBLISHABLE_KEY)
        export PUBLIC_SUPABASE_PUBLISHABLE_KEY="${PUBLIC_SUPABASE_PUBLISHABLE_KEY:-$value}"
        export VITE_SUPABASE_PUBLISHABLE_KEY="${VITE_SUPABASE_PUBLISHABLE_KEY:-$value}"
        ;;
      SECRET_KEY)
        export SUPABASE_SECRET_KEY="${SUPABASE_SECRET_KEY:-$value}"
        ;;
      JWT_SECRET)
        export JWT_SECRET="${JWT_SECRET:-$value}"
        ;;
    esac
  done < <(supabase status -o env)
}

if supabase status -o env >/dev/null 2>&1; then
  _load_supabase_env
fi

exec pnpm --dir frontend run dev
