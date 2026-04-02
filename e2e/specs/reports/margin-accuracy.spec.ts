import { test, expect } from "@playwright/test";
import { freshSeed, type SeedContext } from "@support/api-client";
import {
  e2eIndexedProductName,
  e2eSessionLabel,
  e2eSuiteDashboardRange,
  uniqueE2eBarcode,
  uniqueJobCode,
} from "@support/e2e-data";
import { CatalogApi } from "@api/catalog.api";
import { JobsApi } from "@api/jobs.api";
import { OperationsApi, withdrawalLineItemsFromSkus, type SkuLineSource } from "@api/operations.api";
import { ReportsApi } from "@api/reports.api";
import { LoginPage } from "@pages/login.page";
import { ReportsPage } from "@pages/reports.page";

const E2E_SESSION = e2eSessionLabel();

/**
 * Story 5 — Margin and P&L accuracy across products/jobs
 */

const ITEMS = [
  { name: "2x4x8 SPF Stud", price: 6.5, cost: 3.8, qty: 100, wQty: 20, dept: "LUM" },
  { name: "Romex 12/2 250ft", price: 125.0, cost: 78.0, qty: 30, wQty: 4, dept: "ELE" },
  { name: "PVC Cement 8oz", price: 8.0, cost: 3.5, qty: 60, wQty: 10, dept: "PLU" },
];

test.describe.serial("Story 5: Margin and P&L accuracy", () => {
  let ctx: SeedContext;
  /** Withdrawal totals include tax; dashboard `range_revenue` uses these. */
  let totalRevenue = 0;
  /** P&L `summary.revenue` is ledger (pre-tax). */
  let totalSubtotal = 0;
  let totalCost = 0;
  let jobId1: string;
  let jobId2: string;
  let suiteClockStart = "";

  test.beforeAll(async ({ browser }) => {
    suiteClockStart = new Date().toISOString();
    const page = await browser.newPage();
    const req = page.request;
    ctx = await freshSeed(req);
    const t = ctx.token;
    const catalog = new CatalogApi(req, t);
    const jobs = new JobsApi(req, t);
    const operations = new OperationsApi(req, t);

    const j1 = (await jobs.createJob({ code: uniqueJobCode("JOB-MARGIN-1") })) as { id: string };
    const j2 = (await jobs.createJob({ code: uniqueJobCode("JOB-MARGIN-2") })) as { id: string };
    jobId1 = j1.id;
    jobId2 = j2.id;

    const pIds: string[] = [];
    const fallbackDept = Object.values(ctx.categoryIds)[0];
    for (let i = 0; i < ITEMS.length; i++) {
      const item = ITEMS[i]!;
      const p = (await catalog.createSku({
        name: e2eIndexedProductName(item.name, E2E_SESSION, i),
        price: item.price,
        cost: item.cost,
        quantity: item.qty,
        min_stock: 5,
        category_id: ctx.categoryIds[item.dept] ?? fallbackDept,
        barcode: uniqueE2eBarcode(),
      })) as { id: string };
      pIds.push(p.id);
    }

    const skus = (await catalog.listSkus()) as SkuLineSource[];

    const w1 = (await operations.createWithdrawalForContractor(ctx.contractorId, {
      job_id: jobId1,
      service_address: "300 Margin St",
      items: withdrawalLineItemsFromSkus(skus, [
        { product_id: pIds[0], quantity: ITEMS[0].wQty },
        { product_id: pIds[1], quantity: ITEMS[1].wQty },
      ]),
    })) as { total: number; cost_total: number };
    const w2 = (await operations.createWithdrawalForContractor(ctx.contractorId, {
      job_id: jobId2,
      service_address: "400 Profit Blvd",
      items: withdrawalLineItemsFromSkus(skus, [{ product_id: pIds[2], quantity: ITEMS[2].wQty }]),
    })) as { total: number; cost_total: number };
    totalRevenue = w1.total + w2.total;
    totalCost = w1.cost_total + w2.cost_total;
    const TAX_RATE = 0.1;
    totalSubtotal = Math.round((totalRevenue / (1 + TAX_RATE)) * 100) / 100;
    await page.close();
  });

  test("5a — dashboard financials match withdrawal sums", async ({ request }) => {
    const reports = new ReportsApi(request, ctx.token);
    const stats = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      range_revenue: number;
      range_cogs: number;
      range_gross_profit: number;
      range_margin_pct: number;
    };

    expect(stats.range_revenue).toBeCloseTo(totalRevenue, 2);
    expect(stats.range_cogs).toBeCloseTo(totalCost, 2);
    expect(stats.range_gross_profit).toBeCloseTo(totalRevenue - totalCost, 2);

    const expectedMargin = ((totalRevenue - totalCost) / totalRevenue) * 100;
    expect(stats.range_margin_pct).toBeCloseTo(expectedMargin, 1);
  });

  test("5b — P&L report totals match", async ({ request }) => {
    const reports = new ReportsApi(request, ctx.token);
    const pl = (await reports.profitAndLoss(e2eSuiteDashboardRange(suiteClockStart))) as {
      summary: { revenue: number; cogs: number; gross_profit: number };
    };
    expect(pl.summary.revenue).toBeCloseTo(totalSubtotal, 2);
    expect(pl.summary.cogs).toBeCloseTo(totalCost, 2);
    expect(pl.summary.gross_profit).toBeCloseTo(totalSubtotal - totalCost, 2);
  });

  test("5c — inventory report matches catalog valuations (whole org)", async ({ request }) => {
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
      unrealized_margin: number;
    };

    expect(inv.total_retail_value).toBeCloseTo(sumRetail, 0);
    expect(inv.total_cost_value).toBeCloseTo(sumCost, 0);
    expect(inv.unrealized_margin).toBeCloseTo(sumRetail - sumCost, 0);
  });

  test("5d — reports UI shows data", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const reportsPage = new ReportsPage(page);
    await reportsPage.gotoProfitAndLossTab();
    await page.waitForTimeout(1000);
    await reportsPage.screenshot("05-pl-report");
    await reportsPage.gotoInventoryTab();
    await page.waitForTimeout(1000);
    await reportsPage.screenshot("05-inventory-report");
    await reportsPage.goToDashboardViaSidebar();
    await page.waitForTimeout(1000);
    await reportsPage.screenshot("05-dashboard-margins");
  });
});
