/** Deterministic-enough unique labels for jobs/units so e2e can re-run against the same DB. */
export function uniqueJobCode(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Label unique per spec file load so generated SKU codes (derived from product name) do not collide on repeated runs. */
export function e2eSessionLabel(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Embed session in catalog product `name`.
 * Backend `slug_from_name` only uses the first 8 alphanumeric chars - suffix-only tokens would be truncated away,
 * so the unique session must be a PREFIX to avoid `idx_skus_sku` collisions on repeated e2e runs.
 */
export function e2eScopedProductName(base: string, session: string): string {
  return `${session} ${base}`;
}

/**
 * Multiple SKUs in one run share `session`; `index` varies the first characters so `slug_from_name` differs per SKU.
 */
export function e2eIndexedProductName(base: string, session: string, index: number): string {
  return `${index}-${session} ${base}`;
}

/**
 * Full UTC calendar day for dashboard / P&L filters (includes all org activity that day).
 */
export function utcTodayRange(): { startDate: string; endDate: string } {
  const d = new Date();
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return {
    startDate: `${y}-${m}-${day}T00:00:00.000Z`,
    endDate: `${y}-${m}-${day}T23:59:59.999Z`,
  };
}

/**
 * Isolate dashboard / P&L to withdrawals in this spec file: pass the ISO timestamp
 * captured at the start of `beforeAll` (before seed/mutations). End is always `now`.
 */
export function e2eSuiteDashboardRange(sinceIso: string): { startDate: string; endDate: string } {
  return { startDate: sinceIso, endDate: new Date().toISOString() };
}

/** Avoid barcode collisions when re-running e2e against a persistent local DB. */
export function uniqueE2eBarcode(): string {
  return `E2E-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
