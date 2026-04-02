import { type APIRequestContext } from "@playwright/test";
import { apiPost } from "@support/api-client";

export class JobsApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async createJob(data: { code: string }) {
    return apiPost(this.request, this.token, "/api/beta/jobs", data);
  }
}
