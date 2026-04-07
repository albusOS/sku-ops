# Launch Checklist

Production readiness checklist for sku-ops. Work through each section before going live.

---

## Infrastructure

- [ ] Provision managed Postgres (Supabase direct connection, port 5432 — not pooler)
- [ ] Provision Redis (managed add-on or Upstash) and note the URL
- [ ] Set `PUBLIC_REDIS_URL` and `PUBLIC_WORKERS=2` (or more) in production environment
- [ ] Verify multi-worker startup succeeds with Redis (logs show Redis connected and safe fan-out)
- [ ] Configure automated Postgres backups (Supabase project backups or provider snapshots)
- [ ] Set up Sentry project and configure `PRIVATE_SENTRY_DSN`
- [ ] Set `PRIVATE_METRICS_TOKEN` and configure Prometheus scraping or platform metrics dashboard
- [ ] Configure uptime monitoring on `/api/health` and `/api/ready` (UptimeRobot, Better Stack, or similar)
- [ ] Point DNS for frontend and API to Vercel and your API host
- [ ] TLS is platform-managed (Vercel + API host); confirm HTTPS on both origins

## Security

- [ ] Set backend `PRIVATE_JWT_SECRET` to the **Supabase project JWT secret** (not a random hex string)
- [ ] Set `PUBLIC_CORS_ORIGINS` to exact production domain(s) — no wildcards
- [ ] Verify security headers with [securityheaders.com](https://securityheaders.com): `X-Frame-Options`, `CSP`, `HSTS`, `X-Content-Type-Options`
- [ ] Confirm API rate limiting strategy (platform WAF / edge rules / app config) matches your threat model
- [ ] Audit git history for committed secrets: `git log --all -p -- '*.env' '*.pem' '*.key'`
- [ ] Confirm no dev-only HTTP routes or data-mutation tooling are exposed in production
- [ ] Ensure `.env` files are in `.gitignore` and `.dockerignore`

## Data Integrity

- [ ] Run full seed and verify all CRUD workflows end-to-end:
  - [ ] Create product, set stock levels, verify inventory counts
  - [ ] Create withdrawal (POS), verify stock decremented
  - [ ] Create invoice from withdrawal, transition draft -> approved -> paid
  - [ ] Create and apply credit note
  - [ ] Xero sync: invoice syncs, reconciliation matches, COGS journal posts
- [ ] Test Xero OAuth flow end-to-end with real credentials (connect, sync, disconnect)
- [ ] Verify WebSocket events propagate to all connected clients (open 2+ browser tabs, create withdrawal, both should update)
- [ ] Test contractor flow: login -> search products -> add to cart -> submit material request -> staff processes -> verify withdrawal created
- [ ] Test admin flow: POS terminal -> scan/search items -> process withdrawal -> generate invoice -> record payment
- [ ] Verify document import: upload receipt PDF -> AI parses line items -> creates purchase order

## CI/CD

- [ ] Verify `.github/workflows/ci.yml` passes on `dev` and `main` (backend lint + format + test, frontend lint + format + build + test, Docker build)
- [ ] Create GitHub environment `production` with required reviewers if you use gated deploys
- [ ] Add branch protection for `main`: require PR, require status checks, require up-to-date
- [ ] Add branch protection for `dev`: require PR, require status checks
- [ ] Run `cz bump --dry-run` to verify commitizen config produces correct version tags (if using release automation)
- [ ] Install pre-commit hooks locally: `pixi run uv run --directory backend pre-commit install --install-hooks && pixi run uv run --directory backend pre-commit install --hook-type commit-msg`

## Testing

- [ ] All backend tests pass: `pixi run tests backend -- -- -v` (or `pixi run uv run --directory backend pytest -v`)
- [ ] All frontend tests pass: `pixi run tests frontend`
- [ ] Ruff lint clean: `pixi run lint backend`
- [ ] Ruff format clean: `pixi run uv run --directory backend ruff format --check .`
- [ ] ESLint clean: `pixi run lint frontend` (or `pixi run lint` for all)
- [ ] Prettier clean: `pixi run pnpm --dir frontend run format:check`
- [ ] Architecture tests pass (DDD boundary enforcement): `pixi run tests backend -- -- tests/unit/test_architecture.py -v`
- [ ] WebSocket edge case tests pass (fan-out, filtering, rapid reconnect)
- [ ] Integration workflow tests pass (authenticated CRUD flows)

## Observability

- [ ] Verify JSON structured logging in production: deploy with `PUBLIC_LOG_LEVEL=INFO`, check logs contain `request_id`, `user_id`, `org_id` fields
- [ ] Confirm `X-Request-ID` response header is present on all API responses
- [ ] Trigger a test error in Sentry and verify it arrives with `org_id` and `request_id` tags
- [ ] Set up log aggregation (platform logs or ship to Datadog/Loki/CloudWatch)
- [ ] Verify Prometheus metrics at `/metrics` (when protected): `http_requests_total`, `http_request_duration_seconds`

## Post-Launch (Not Blockers)

- [ ] Add database migration tooling (alembic or custom) before the first schema change with live data
- [ ] Expand frontend test coverage (currently 3 test files — add tests for critical pages and hooks)
- [ ] Add load testing with k6 or locust (target: 50 concurrent users, measure p95 latency)
- [ ] Add E2E browser tests (Playwright) for contractor and admin critical flows
- [ ] Set up a staging environment for pre-production validation
- [ ] Add Redis health check to `/api/ready` endpoint
- [ ] Configure alerting rules (error rate spikes, p95 latency > 2s, health check failures)
