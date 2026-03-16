import { test, expect } from "@playwright/test";
import {
  freshSeed,
  apiGet,
  apiPost,
  apiPut,
  type SeedContext,
} from "./helpers";

/**
 * Story 6 — Ledger integrity after mixed financial workload
 *
 * Runs withdrawal + partial return + payment, then verifies:
 * - AR balance = unpaid withdrawal totals
 * - P&L revenue = withdrawal totals minus return totals
 * - Gross profit = revenue - COGS
 * - Inventory report reflects remaining stock value
 */

const PRODUCT = { name: "Romex 14/2 250ft", price: 95.0, cost: 58.0, quantity: 100, min_stock: 10 };
const WD_QTY = 15;
const RET_QTY = 5;

test.describe.serial("Story 6: Ledger integrity", () => {
  let ctx: SeedContext;
  let productId: string;
  let wdTotal: number;
  let retTotal: number;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    ctx = await freshSeed(page.request);
    const req = page.request;
    const t = ctx.token;

    const product = await apiPost(req, t, "/api/beta/catalog/skus", {
      ...PRODUCT,
      category_id: ctx.categoryIds["ELE"],
    });
    productId = product.id;
    await apiPost(req, t, "/api/beta/jobs", { code: "JOB-LEDGER-001" });

    await page.close();
  });

  test("6a — withdrawal records revenue correctly", async ({ request }) => {
    const wd = await apiPost(request, ctx.token, "/api/beta/operations/withdrawals/for-contractor", {
      contractor_id: ctx.contractorId,
      job_id: "JOB-LEDGER-001",
      service_address: "600 Ledger Blvd",
      items: [{ product_id: productId, quantity: WD_QTY }],
    });
    wdTotal = wd.total;

    const stats = await apiGet(request, ctx.token, "/api/beta/reports/dashboard/stats");
    expect(stats.range_revenue).toBeCloseTo(wd.subtotal, 2);
    expect(stats.range_cogs).toBeCloseTo(wd.cost_total, 2);
    expect(stats.unpaid_total).toBeCloseTo(wdTotal, 2);

    // Stock decreased
    const products = await apiGet(request, ctx.token, "/api/beta/catalog/skus");
    const p = products.find((x: any) => x.id === productId);
    expect(p.quantity).toBe(PRODUCT.quantity - WD_QTY);
  });

  test("6b — partial return reduces revenue and restocks", async ({ request }) => {
    const withdrawals = await apiGet(request, ctx.token, "/api/beta/operations/withdrawals");
    const wdId = withdrawals[0].id;

    const ret = await apiPost(request, ctx.token, "/api/beta/operations/returns", {
      withdrawal_id: wdId,
      items: [{ product_id: productId, quantity: RET_QTY }],
    });
    retTotal = ret.total;

    // Stock restocked
    const products = await apiGet(request, ctx.token, "/api/beta/catalog/skus");
    const p = products.find((x: any) => x.id === productId);
    expect(p.quantity).toBe(PRODUCT.quantity - WD_QTY + RET_QTY);
  });

  test("6c — payment reduces unpaid balance", async ({ request }) => {
    const withdrawals = await apiGet(request, ctx.token, "/api/beta/operations/withdrawals");
    const wdId = withdrawals[0].id;

    await apiPut(request, ctx.token, `/api/beta/operations/withdrawals/${wdId}/mark-paid`);

    const wd = await apiGet(request, ctx.token, `/api/beta/operations/withdrawals/${wdId}`);
    expect(wd.payment_status).toBe("paid");

    const stats = await apiGet(request, ctx.token, "/api/beta/reports/dashboard/stats");
    expect(stats.unpaid_total).toBe(0);
  });

  test("6d — P&L reflects net revenue after return", async ({ request }) => {
    const pl = await apiGet(request, ctx.token, "/api/beta/reports/pl");
    const netRevenue = PRODUCT.price * WD_QTY - PRODUCT.price * RET_QTY;
    const netCogs = PRODUCT.cost * WD_QTY - PRODUCT.cost * RET_QTY;

    expect(pl.summary.revenue).toBeCloseTo(netRevenue, 2);
    expect(pl.summary.cogs).toBeCloseTo(netCogs, 2);
    expect(pl.summary.gross_profit).toBeCloseTo(netRevenue - netCogs, 2);
  });

  test("6e — inventory report matches remaining stock value", async ({ request }) => {
    const inv = await apiGet(request, ctx.token, "/api/beta/reports/inventory");
    const remainingQty = PRODUCT.quantity - WD_QTY + RET_QTY;

    expect(inv.total_retail_value).toBeCloseTo(PRODUCT.price * remainingQty, 2);
    expect(inv.total_cost_value).toBeCloseTo(PRODUCT.cost * remainingQty, 2);
  });

  test("6f — gross profit = revenue - COGS (always)", async ({ request }) => {
    const stats = await apiGet(request, ctx.token, "/api/beta/reports/dashboard/stats");
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
