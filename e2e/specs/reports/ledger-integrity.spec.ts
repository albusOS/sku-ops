import { test, expect } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { JobsApi } from "@api/jobs.api";
import { OperationsApi, withdrawalLineItemsFromSkus, type SkuLineSource } from "@api/operations.api";
import { ReportsApi } from "@api/reports.api";
import { freshSeed, type SeedContext } from "@support/api-client";
import {
  e2eScopedProductName,
  e2eSessionLabel,
  e2eSuiteDashboardRange,
  uniqueE2eBarcode,
  uniqueJobCode,
} from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();

/**
 * Story 6 — Ledger integrity after mixed financial workload
 */

const PRODUCT = { name: "Romex 14/2 250ft", price: 95.0, cost: 58.0, quantity: 100, min_stock: 10 };
const WD_QTY = 15;
const RET_QTY = 5;

test.describe.serial("Story 6: Ledger integrity", () => {
  let ctx: SeedContext;
  let productId: string;
  let jobId: string;
  let wdTotal: number;
  let retTotal: number;
  let suiteClockStart = "";

  test.beforeAll(async ({ browser }) => {
    suiteClockStart = new Date().toISOString();
    const page = await browser.newPage();
    const req = page.request;
    ctx = await freshSeed(req);
    const catalog = new CatalogApi(req, ctx.token);
    const jobs = new JobsApi(req, ctx.token);

    const product = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(PRODUCT.name, E2E_SESSION),
      category_id: ctx.categoryIds["ELE"],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };
    productId = product.id;
    const job = (await jobs.createJob({ code: uniqueJobCode("JOB-LEDGER") })) as { id: string };
    jobId = job.id;

    await page.close();
  });

  test("6a — withdrawal records revenue correctly", async ({ request }) => {
    const operations = new OperationsApi(request, ctx.token);
    const reports = new ReportsApi(request, ctx.token);
    const catalog = new CatalogApi(request, ctx.token);

    const skus = (await catalog.listSkus()) as SkuLineSource[];
    const items = withdrawalLineItemsFromSkus(skus, [{ product_id: productId, quantity: WD_QTY }]);

    const wd = (await operations.createWithdrawalForContractor(ctx.contractorId, {
      job_id: jobId,
      service_address: "600 Ledger Blvd",
      items,
    })) as { total: number; subtotal: number; cost_total: number };
    wdTotal = wd.total;

    const stats = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      range_revenue: number;
      range_cogs: number;
      unpaid_total: number;
      invoiced_total: number;
    };
    expect(stats.range_revenue).toBeCloseTo(wd.total, 2);
    expect(stats.range_cogs).toBeCloseTo(wd.cost_total, 2);
    expect(stats.unpaid_total).toBe(0);
    expect(stats.invoiced_total).toBeCloseTo(wdTotal, 2);

    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number }>;
    const p = products.find((x) => x.id === productId);
    expect(p?.quantity).toBe(PRODUCT.quantity - WD_QTY);
  });

  test("6b — partial return reduces revenue and restocks", async ({ request }) => {
    const operations = new OperationsApi(request, ctx.token);
    const catalog = new CatalogApi(request, ctx.token);

    const withdrawals = (await operations.listWithdrawals()) as Array<{ id: string }>;
    const wdId = withdrawals[0].id;

    const wd = (await operations.getWithdrawal(wdId)) as {
      items: Array<{ sku_id: string; sku: string; name: string; unit_price: number; cost: number }>;
    };
    const line = wd.items.find((i) => i.sku_id === productId);
    if (!line) throw new Error("withdrawal line for product not found");

    const ret = (await operations.createReturn({
      withdrawal_id: wdId,
      items: [
        {
          sku_id: line.sku_id,
          sku: line.sku,
          name: line.name,
          quantity: RET_QTY,
          unit_price: line.unit_price,
          cost: line.cost,
        },
      ],
    })) as { total: number };
    retTotal = ret.total;

    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number }>;
    const p = products.find((x) => x.id === productId);
    expect(p?.quantity).toBe(PRODUCT.quantity - WD_QTY + RET_QTY);
  });

  test("6c — payment reduces unpaid balance", async ({ request }) => {
    const operations = new OperationsApi(request, ctx.token);
    const reports = new ReportsApi(request, ctx.token);

    const withdrawals = (await operations.listWithdrawals()) as Array<{ id: string }>;
    const wdId = withdrawals[0].id;

    await operations.markWithdrawalPaid(wdId);

    const wd = (await operations.getWithdrawal(wdId)) as { payment_status: string };
    expect(wd.payment_status).toBe("paid");

    const stats = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      unpaid_total: number;
    };
    expect(stats.unpaid_total).toBe(0);
  });

  test("6d — P&L reflects net revenue after return", async ({ request }) => {
    const reports = new ReportsApi(request, ctx.token);
    const pl = (await reports.profitAndLoss(e2eSuiteDashboardRange(suiteClockStart))) as {
      summary: { revenue: number; cogs: number; gross_profit: number };
    };
    const netRevenue = PRODUCT.price * WD_QTY - PRODUCT.price * RET_QTY;
    const netCogs = PRODUCT.cost * WD_QTY - PRODUCT.cost * RET_QTY;

    expect(pl.summary.revenue).toBeCloseTo(netRevenue, 2);
    expect(pl.summary.cogs).toBeCloseTo(netCogs, 2);
    expect(pl.summary.gross_profit).toBeCloseTo(netRevenue - netCogs, 2);
  });

  test("6e — inventory report matches catalog valuations (whole org)", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const reports = new ReportsApi(request, ctx.token);
    const skus = (await catalog.listSkus()) as Array<{ price: number; cost: number; quantity: number }>;
    let sumRetail = 0;
    let sumCost = 0;
    for (const p of skus) {
      sumRetail += p.price * p.quantity;
      sumCost += p.cost * p.quantity;
    }

    const inv = (await reports.inventoryReport()) as {
      total_retail_value: number;
      total_cost_value: number;
    };

    expect(inv.total_retail_value).toBeCloseTo(sumRetail, 0);
    expect(inv.total_cost_value).toBeCloseTo(sumCost, 0);
  });

  test("6f — gross profit = revenue - COGS (always)", async ({ request }) => {
    const reports = new ReportsApi(request, ctx.token);
    const stats = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      range_revenue: number;
      range_cogs: number;
      range_gross_profit: number;
      range_margin_pct: number;
    };
    const revenue = stats.range_revenue;
    const cogs = stats.range_cogs;
    const profit = stats.range_gross_profit;

    expect(profit).toBeCloseTo(revenue - cogs, 2);

    if (revenue > 0) {
      const expectedMarginPct = ((revenue - cogs) / revenue) * 100;
      expect(stats.range_margin_pct).toBeCloseTo(expectedMarginPct, 1);
    }
  });
});
