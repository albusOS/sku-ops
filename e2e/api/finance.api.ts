import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiPost } from "@support/api-client";

export class FinanceApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async getInvoice(invoiceId: string) {
    return apiGet(this.request, this.token, `/api/beta/finance/invoices/${invoiceId}`);
  }

  async createInvoice(data: { withdrawal_ids: string[] }) {
    return apiPost(this.request, this.token, "/api/beta/finance/invoices", data);
  }

  async createPayment(data: Record<string, unknown>) {
    return apiPost(this.request, this.token, "/api/beta/finance/payments", data);
  }
}
