import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiPost, apiPut } from "@support/api-client";

export type SkuLineSource = {
  id: string;
  sku: string;
  name: string;
  price: number;
  cost: number;
  sell_uom?: string | null;
};

/** Build withdrawal line items matching MaterialWithdrawal line schema. */
export function withdrawalLineItemsFromSkus(
  skus: SkuLineSource[],
  lines: Array<{ product_id: string; quantity: number }>,
) {
  return lines.map((line) => {
    const p = skus.find((s) => s.id === line.product_id);
    if (!p) throw new Error(`SKU not found for product_id ${line.product_id}`);
    return {
      sku_id: p.id,
      sku: p.sku,
      name: p.name,
      quantity: line.quantity,
      unit: p.sell_uom ?? "each",
      unit_price: p.price,
      cost: p.cost,
    };
  });
}

export class OperationsApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async listContractors() {
    return apiGet(this.request, this.token, "/api/beta/operations/contractors");
  }

  async createWithdrawalForContractor(contractorId: string, data: Record<string, unknown>) {
    const q = new URLSearchParams({ contractor_id: contractorId });
    return apiPost(
      this.request,
      this.token,
      `/api/beta/operations/withdrawals/for-contractor?${q.toString()}`,
      data,
    );
  }

  async getWithdrawal(id: string) {
    return apiGet(this.request, this.token, `/api/beta/operations/withdrawals/${id}`);
  }

  async listWithdrawals() {
    return apiGet(this.request, this.token, "/api/beta/operations/withdrawals");
  }

  async createReturn(data: Record<string, unknown>) {
    return apiPost(this.request, this.token, "/api/beta/operations/returns", data);
  }

  async markWithdrawalPaid(id: string) {
    return apiPut(this.request, this.token, `/api/beta/operations/withdrawals/${id}/mark-paid`, {});
  }
}
