import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiPost } from "@support/api-client";

export class CatalogApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async listDepartments() {
    return apiGet(this.request, this.token, "/api/beta/catalog/departments");
  }

  async listSkus() {
    return apiGet(this.request, this.token, "/api/beta/catalog/skus");
  }

  async createSku(data: Record<string, unknown>) {
    return apiPost(this.request, this.token, "/api/beta/catalog/skus", data);
  }

  async listUnits() {
    return apiGet(this.request, this.token, "/api/beta/catalog/units");
  }

  async createUnit(data: { code: string; name: string; family: string }) {
    return apiPost(this.request, this.token, "/api/beta/catalog/units", data);
  }

  async listVendors() {
    return apiGet(this.request, this.token, "/api/beta/catalog/vendors");
  }
}
