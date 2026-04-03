import { type APIRequestContext } from "@playwright/test";
import { apiGet, apiGetWithRetry } from "@support/api-client";

export type DateRange = { startDate: string; endDate: string };

export class ReportsApi {
  constructor(
    private readonly request: APIRequestContext,
    private readonly token: string,
  ) {}

  async dashboardStats(range?: DateRange) {
    const qs =
      range != null
        ? `?start_date=${encodeURIComponent(range.startDate)}&end_date=${encodeURIComponent(range.endDate)}`
        : "";
    return apiGetWithRetry(this.request, this.token, `/api/beta/reports/dashboard/stats${qs}`);
  }

  async profitAndLoss(range?: DateRange) {
    const qs =
      range != null
        ? `?start_date=${encodeURIComponent(range.startDate)}&end_date=${encodeURIComponent(range.endDate)}`
        : "";
    return apiGet(this.request, this.token, `/api/beta/reports/pl${qs}`);
  }

  async inventoryReport() {
    return apiGet(this.request, this.token, "/api/beta/reports/inventory");
  }
}
