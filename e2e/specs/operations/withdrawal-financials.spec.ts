import { test, expect } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { JobsApi } from "@api/jobs.api";
import {
  OperationsApi,
  withdrawalLineItemsFromSkus,
  type SkuLineSource,
} from "@api/operations.api";
import { InventoryApi } from "@api/inventory.api";
import { ReportsApi } from "@api/reports.api";
import { freshSeed, type SeedContext } from "@support/api-client";
import {
  e2eScopedProductName,
  e2eSessionLabel,
  e2eSuiteDashboardRange,
  uniqueE2eBarcode,
  uniqueJobCode,
} from "@support/e2e-data";
import { WSEventCollector } from "@support/ws-collector";
import { LoginPage } from "@pages/login.page";
import { DashboardPage } from "@pages/dashboard.page";

const E2E_SESSION = e2eSessionLabel();

/**
 * Story 1 — Withdrawal creates correct financial entries
 */

const PRODUCT = { name: "10AWG THHN Wire 500ft", price: 85.0, cost: 52.0, quantity: 50, min_stock: 5 };
const WITHDRAW_QTY = 3;

test.describe.serial("Story 1: Withdrawal financials", () => {
  let ctx: SeedContext;
  let productId: string;
  let jobId: string;
  let wsCollector: WSEventCollector;
  /** Populated in 1b for 1c dashboard assertions (includes tax). */
  let withdrawalRevenueTotal = 0;
  let withdrawalCostTotal = 0;
  /** Limits dashboard aggregates to this file (Playwright runs many suites per day). */
  let suiteClockStart = "";

  test.beforeAll(async ({ browser }) => {
    suiteClockStart = new Date().toISOString();
    const page = await browser.newPage();
    const request = page.request;
    ctx = await freshSeed(request);
    const catalog = new CatalogApi(request, ctx.token);
    const jobs = new JobsApi(request, ctx.token);
    const created = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(PRODUCT.name, E2E_SESSION),
      category_id: ctx.categoryIds["ELE"],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };
    productId = created.id;
    const job = (await jobs.createJob({ code: uniqueJobCode("JOB-E2E") })) as { id: string };
    jobId = job.id;

    wsCollector = new WSEventCollector();
    await wsCollector.connect(ctx.token);

    await page.close();
  });

  test.afterAll(() => {
    wsCollector?.close();
  });

  test("1a — product starts with correct stock", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const products = (await catalog.listSkus()) as Array<{
      id: string;
      quantity: number;
      price: number;
      cost: number;
    }>;
    const p = products.find((x) => x.id === productId);
    expect(p?.quantity).toBe(PRODUCT.quantity);
    expect(p?.price).toBe(PRODUCT.price);
    expect(p?.cost).toBe(PRODUCT.cost);
  });

  test("1b — withdrawal decrements stock and records revenue", async ({ request }) => {
    wsCollector.clear();

    const operations = new OperationsApi(request, ctx.token);
    const catalog = new CatalogApi(request, ctx.token);
    const inventory = new InventoryApi(request, ctx.token);

    const skus = (await catalog.listSkus()) as SkuLineSource[];
    const items = withdrawalLineItemsFromSkus(skus, [{ product_id: productId, quantity: WITHDRAW_QTY }]);

    const withdrawal = (await operations.createWithdrawalForContractor(ctx.contractorId, {
      job_id: jobId,
      service_address: "100 Test Lane",
      items,
    })) as {
      total: number;
      items: Array<{ quantity: number; unit_price: number; subtotal: number }>;
      cost_total: number;
    };

    withdrawalRevenueTotal = withdrawal.total;
    withdrawalCostTotal = withdrawal.cost_total;

    const item = withdrawal.items[0];
    expect(item.quantity).toBe(WITHDRAW_QTY);
    expect(item.unit_price).toBe(PRODUCT.price);
    expect(item.subtotal).toBeCloseTo(PRODUCT.price * WITHDRAW_QTY, 2);
    expect(withdrawal.cost_total).toBeCloseTo(PRODUCT.cost * WITHDRAW_QTY, 2);

    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number }>;
    const p = products.find((x) => x.id === productId);
    expect(p?.quantity).toBe(PRODUCT.quantity - WITHDRAW_QTY);

    const history = (await inventory.getStockHistory(productId)) as {
      history: Array<{
        reference_type?: string;
        quantity_delta: number;
        quantity_after: number;
      }>;
    };
    const entry = history.history.find((h) => h.reference_type === "withdrawal");
    expect(entry).toBeTruthy();
    expect(entry?.quantity_delta).toBe(-WITHDRAW_QTY);
    expect(entry?.quantity_after).toBe(PRODUCT.quantity - WITHDRAW_QTY);
  });

  test("1b-ws — WebSocket events delivered after withdrawal", async () => {
    const created = await wsCollector.waitFor("withdrawal.created", 5000);
    expect(created).toBeTruthy();

    const invUpdated = await wsCollector.waitFor("inventory.updated", 5000);
    expect(invUpdated).toBeTruthy();
  });

  test("1c — dashboard revenue matches withdrawal", async ({ request, page }) => {
    const reports = new ReportsApi(request, ctx.token);
    const stats = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      range_revenue: number;
      range_cogs: number;
      range_gross_profit: number;
      unpaid_total: number;
      invoiced_total: number;
    };

    expect(stats.range_revenue).toBeCloseTo(withdrawalRevenueTotal, 2);
    expect(stats.range_cogs).toBeCloseTo(withdrawalCostTotal, 2);
    expect(stats.range_gross_profit).toBeCloseTo(withdrawalRevenueTotal - withdrawalCostTotal, 2);
    expect(stats.unpaid_total).toBe(0);
    expect(stats.invoiced_total).toBeCloseTo(withdrawalRevenueTotal, 2);

    await new LoginPage(page).loginAsAdmin();
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await page.waitForTimeout(1000);
    await dashboard.screenshot("01-dashboard-after-withdrawal");
  });
});
