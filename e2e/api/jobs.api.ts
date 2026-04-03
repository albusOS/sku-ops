import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiPost, apiPut } from "@support/api-client";

export class JobsApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async listJobs(params?: Record<string, string>) {
    const q = params ? `?${new URLSearchParams(params).toString()}` : "";
    return apiGet(this.request, this.token, `/api/beta/jobs${q}`);
  }

  async searchJobs(query: string) {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    return apiGet(this.request, this.token, `/api/beta/jobs/search${q}`);
  }

  async getJob(idOrCode: string) {
    return apiGet(this.request, this.token, `/api/beta/jobs/${encodeURIComponent(idOrCode)}`);
  }

  async createJob(data: { code: string; name?: string; service_address?: string; notes?: string | null }) {
    return apiPost(this.request, this.token, "/api/beta/jobs", data);
  }

  async updateJob(jobId: string, data: Record<string, unknown>) {
    return apiPut(this.request, this.token, `/api/beta/jobs/${jobId}`, data);
  }
}
