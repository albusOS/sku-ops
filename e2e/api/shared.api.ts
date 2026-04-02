import { type APIRequestContext, expect } from "@playwright/test";
import { API_BASE_URL } from "@support/api-client";

/** Shared routes that do not require a Bearer token (e.g. liveness). */
export class SharedApi {
  constructor(private readonly request: APIRequestContext) {}

  async health(): Promise<{ status: string }> {
    const resp = await this.request.get(`${API_BASE_URL}/api/beta/shared/health`);
    expect(resp.ok(), `Health failed: ${resp.status()}`).toBeTruthy();
    return resp.json() as Promise<{ status: string }>;
  }
}
