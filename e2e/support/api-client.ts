import { type APIRequestContext, expect } from "@playwright/test";

export const API_BASE_URL = "http://localhost:8000";

const E2E_ADMIN_EMAIL = "dev@supply-yard.local";
const E2E_ADMIN_PASSWORD = "dev123";

/**
 * Obtains a Supabase access_token (backend verifies JWKS in dev). Run via `./bin/dev test:e2e`
 * so SUPABASE_URL and PUBLIC_SUPABASE_PUBLISHABLE_KEY are exported from `supabase status`.
 */
export async function getAdminToken(request: APIRequestContext): Promise<string> {
  const supabaseUrl = (process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL ?? "").replace(/\/$/, "");
  const anonKey =
    process.env.PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? process.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? "";
  if (!supabaseUrl || !anonKey) {
    throw new Error(
      "E2E auth: set SUPABASE_URL and PUBLIC_SUPABASE_PUBLISHABLE_KEY (e.g. run ./bin/dev test:e2e after ./bin/dev db)",
    );
  }
  const tokenUrl = `${supabaseUrl}/auth/v1/token?grant_type=password`;
  const resp = await request.post(tokenUrl, {
    headers: {
      apikey: anonKey,
      Authorization: `Bearer ${anonKey}`,
      "Content-Type": "application/json",
    },
    data: { email: E2E_ADMIN_EMAIL, password: E2E_ADMIN_PASSWORD },
  });
  expect(resp.ok(), `Supabase password grant failed: ${resp.status()} — ${await resp.text()}`).toBeTruthy();
  const body = (await resp.json()) as { access_token: string };
  return body.access_token;
}

export function authHeader(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function apiGet(request: APIRequestContext, token: string, path: string) {
  const resp = await request.get(`${API_BASE_URL}${path}`, { headers: authHeader(token) });
  expect(resp.ok(), `GET ${path} → ${resp.status()}`).toBeTruthy();
  return resp.json();
}

export async function apiPost(
  request: APIRequestContext,
  token: string,
  path: string,
  data: unknown,
) {
  const resp = await request.post(`${API_BASE_URL}${path}`, {
    headers: { ...authHeader(token), "Content-Type": "application/json" },
    data,
  });
  expect(resp.ok(), `POST ${path} → ${resp.status()} — ${await resp.text()}`).toBeTruthy();
  return resp.json();
}

export async function apiPut(
  request: APIRequestContext,
  token: string,
  path: string,
  data?: unknown,
) {
  const resp = await request.put(`${API_BASE_URL}${path}`, {
    headers: { ...authHeader(token), "Content-Type": "application/json" },
    data: data ?? {},
  });
  expect(resp.ok(), `PUT ${path} → ${resp.status()}`).toBeTruthy();
  return resp.json();
}

export interface SeedContext {
  token: string;
  categoryIds: Record<string, string>;
  contractorId: string;
}

/** Assumes provisioned DB (dev users, departments, contractors). */
export async function freshSeed(request: APIRequestContext): Promise<SeedContext> {
  const token = await getAdminToken(request);
  const categories = await apiGet(request, token, "/api/beta/catalog/departments");
  const categoryIds: Record<string, string> = {};
  for (const c of categories as Array<{ code: string; id: string }>) {
    categoryIds[c.code] = c.id;
  }
  const contractors = (await apiGet(request, token, "/api/beta/operations/contractors")) as Array<{
    id: string;
  }>;
  return { token, categoryIds, contractorId: contractors[0].id };
}
