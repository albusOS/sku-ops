import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiPost } from "@support/api-client";

export class PurchasingApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async getPurchaseOrder(poId: string) {
    return apiGet(this.request, this.token, `/api/beta/purchasing/purchase-orders/${poId}`);
  }

  async createPurchaseOrder(data: {
    vendor_name: string;
    products: Array<Record<string, unknown>>;
    create_vendor_if_missing?: boolean;
    category_id?: string | null;
  }) {
    return apiPost(this.request, this.token, "/api/beta/purchasing/purchase-orders", data);
  }

  async recordDelivery(poId: string, data: { item_ids: string[] }) {
    return apiPost(this.request, this.token, `/api/beta/purchasing/purchase-orders/${poId}/delivery`, data);
  }

  async receive(poId: string, data: { items: Array<{ id: string; received_qty: number }> }) {
    return apiPost(this.request, this.token, `/api/beta/purchasing/purchase-orders/${poId}/receive`, data);
  }
}
