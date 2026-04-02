import { test, expect } from "@playwright/test";
import { freshSeed, type SeedContext } from "@support/api-client";
import {
  e2eIndexedProductName,
  e2eSessionLabel,
  e2eSuiteDashboardRange,
  uniqueE2eBarcode,
  uniqueJobCode,
} from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();
import { WSEventCollector } from "@support/ws-collector";
import { CatalogApi } from "@api/catalog.api";
import { JobsApi } from "@api/jobs.api";
import { OperationsApi, withdrawalLineItemsFromSkus, type SkuLineSource } from "@api/operations.api";
import { FinanceApi } from "@api/finance.api";
import { ReportsApi } from "@api/reports.api";
import { LoginPage } from "@pages/login.page";
import { FinancePage } from "@pages/finance.page";

/**
 * Story 2 — Invoice & payment cycle
 */

const PRODUCTS = [
  { name: "PEX Pipe 1/2in 100ft", price: 42.0, cost: 25.0, quantity: 200, min_stock: 20 },
  { name: "Copper Fitting 1/2in Tee", price: 3.5, cost: 1.8, quantity: 500, min_stock: 50 },
];

test.describe.serial("Story 2: Invoice & payment cycle", () => {
  let ctx: SeedContext;
  let withdrawalIds: string[] = [];
  let expectedTotal = 0;
  let invoiceIds: string[] = [];
  let wsCollector: WSEventCollector;
  let jobId: string;
  let suiteClockStart = "";

  test.beforeAll(async ({ browser }) => {
    suiteClockStart = new Date().toISOString();
    const page = await browser.newPage();
    const req = page.request;
    ctx = await freshSeed(req);
    const t = ctx.token;
    const deptId = ctx.categoryIds["PLU"] ?? Object.values(ctx.categoryIds)[0];
    const catalog = new CatalogApi(req, t);
    const jobs = new JobsApi(req, t);
    const operations = new OperationsApi(req, t);

    const pIds: string[] = [];
    for (let i = 0; i < PRODUCTS.length; i++) {
      const p = PRODUCTS[i]!;
      const created = (await catalog.createSku({
        ...p,
        name: e2eIndexedProductName(p.name, E2E_SESSION, i),
        category_id: deptId,
        barcode: uniqueE2eBarcode(),
      })) as { id: string };
      pIds.push(created.id);
    }
    const job = (await jobs.createJob({ code: uniqueJobCode("JOB-INV") })) as { id: string };
    jobId = job.id;

    const skus = (await catalog.listSkus()) as SkuLineSource[];

    const w1 = (await operations.createWithdrawalForContractor(ctx.contractorId, {
      job_id: jobId,
      service_address: "200 Invoice Ave",
      items: withdrawalLineItemsFromSkus(skus, [
        { product_id: pIds[0], quantity: 5 },
        { product_id: pIds[1], quantity: 20 },
      ]),
    })) as { id: string; total: number };
    const w2 = (await operations.createWithdrawalForContractor(ctx.contractorId, {
      job_id: jobId,
      service_address: "200 Invoice Ave",
      items: withdrawalLineItemsFromSkus(skus, [{ product_id: pIds[0], quantity: 3 }]),
    })) as { id: string; total: number };
    withdrawalIds = [w1.id, w2.id];
    expectedTotal = w1.total + w2.total;

    wsCollector = new WSEventCollector();
    await wsCollector.connect(ctx.token);

    await page.close();
  });

  test.afterAll(() => {
    wsCollector?.close();
  });

  test("2a — auto-invoices per withdrawal; combined totals match withdrawals", async ({
    request,
  }) => {
    const finance = new FinanceApi(request, ctx.token);
    const operations = new OperationsApi(request, ctx.token);

    let invoiceSum = 0;
    const invIds: string[] = [];
    for (const wId of withdrawalIds) {
      const w = (await operations.getWithdrawal(wId)) as { invoice_id: string | null };
      expect(w.invoice_id).toBeTruthy();
      const inv = (await finance.getInvoice(w.invoice_id!)) as { total: number };
      invoiceSum += inv.total;
      invIds.push(w.invoice_id!);
    }
    expect(invoiceSum).toBeCloseTo(expectedTotal, 2);
    invoiceIds = invIds;
  });

  test("2b — payment zeroes unpaid balance", async ({ request }) => {
    const reports = new ReportsApi(request, ctx.token);
    const finance = new FinanceApi(request, ctx.token);
    const operations = new OperationsApi(request, ctx.token);

    const statsBefore = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      unpaid_total: number;
      invoiced_total: number;
    };
    // Withdrawals auto-link to invoices → `invoiced`, not `unpaid`.
    expect(statsBefore.unpaid_total).toBe(0);
    expect(statsBefore.invoiced_total).toBeCloseTo(expectedTotal, 2);

    wsCollector.clear();

    for (const invId of invoiceIds) {
      const inv = (await finance.getInvoice(invId)) as { total: number };
      await finance.createPayment({
        invoice_id: invId,
        amount: inv.total,
        method: "bank_transfer",
        reference: `TRF-E2E-${invId.slice(0, 8)}`,
        payment_date: new Date().toISOString().split("T")[0],
      });
    }

    for (const wId of withdrawalIds) {
      const w = (await operations.getWithdrawal(wId)) as { payment_status: string };
      expect(w.payment_status).toBe("paid");
    }

    const statsAfter = (await reports.dashboardStats(e2eSuiteDashboardRange(suiteClockStart))) as {
      unpaid_total: number;
    };
    expect(statsAfter.unpaid_total).toBe(0);
  });

  test("2b-ws — WebSocket events delivered after payment", async () => {
    for (let i = 0; i < withdrawalIds.length; i++) {
      const updated = await wsCollector.waitFor("withdrawal.updated", 5000);
      expect(updated).toBeTruthy();
    }
  });

  test("2c — UI shows invoice and payment", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const financeUi = new FinancePage(page);
    await financeUi.gotoInvoices();
    await page.waitForTimeout(1000);
    await financeUi.screenshot("02-invoices-page");
    await financeUi.gotoPayments();
    await page.waitForTimeout(1000);
    await financeUi.screenshot("02-payments-page");
    await financeUi.gotoDashboard();
    await page.waitForTimeout(1000);
    await financeUi.screenshot("02-dashboard-after-payment");
  });
});
