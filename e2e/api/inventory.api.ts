import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiPost } from "@support/api-client";

export class InventoryApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async adjustStock(productId: string, data: { quantity_delta: number; reason: string }) {
    return apiPost(
      this.request,
      this.token,
      `/api/beta/inventory/stock/${productId}/adjust`,
      data,
    );
  }

  async getStockHistory(productId: string) {
    return apiGet(this.request, this.token, `/api/beta/inventory/stock/${productId}/history`);
  }
}
