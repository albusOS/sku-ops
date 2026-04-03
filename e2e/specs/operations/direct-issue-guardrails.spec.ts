/**
 * Goal: `/pos/issue` blocks incomplete submissions and surfaces server stock errors clearly.
 */
import { expect, test } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { InventoryApi } from "@api/inventory.api";
import { JobsApi } from "@api/jobs.api";
import { LoginPage } from "@pages/login.page";
import { PosIssuePage } from "@pages/pos-issue.page";
import { freshSeed } from "@support/api-client";
import { e2eScopedProductName, e2eSessionLabel, uniqueE2eBarcode, uniqueJobCode } from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();

const BASE_PRODUCT = {
  price: 12.0,
  cost: 6.0,
  min_stock: 1,
};

test.describe.serial("Direct issue (/pos/issue) guardrails", () => {
  /** Plenty of stock for validation + happy-path checkout. */
  let mainProductName: string;
  /** Dedicated row for insufficient-stock (DB drained while UI may still show old qty). */
  let lowProductName: string;
  let lowProductSku: string;
  let lowProductId: string;
  let jobCode: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const request = page.request;
    const ctx = await freshSeed(request);
    const catalog = new CatalogApi(request, ctx.token);
    const jobs = new JobsApi(request, ctx.token);
    jobCode = uniqueJobCode("E2E-DI");
    await jobs.createJob({ code: jobCode });
    const mainDept = ctx.categoryIds["FAS"] ?? Object.values(ctx.categoryIds)[0];
    const lowDept =
      ctx.categoryIds["ELW"] ??
      ctx.categoryIds["ELE"] ??
      Object.values(ctx.categoryIds).find((id) => id !== mainDept) ??
      mainDept;
    const skuSuffix = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

    mainProductName = e2eScopedProductName(`Direct Issue E2E Bolt ${skuSuffix}`, E2E_SESSION);
    await catalog.createSku({
      ...BASE_PRODUCT,
      name: mainProductName,
      quantity: 80,
      category_id: mainDept,
      barcode: uniqueE2eBarcode(),
    });

    lowProductName = e2eScopedProductName(`Direct Issue Low Stock Bolt ${skuSuffix}`, E2E_SESSION);
    const low = (await catalog.createSku({
      ...BASE_PRODUCT,
      name: lowProductName,
      quantity: 5,
      category_id: lowDept,
      barcode: uniqueE2eBarcode(),
    })) as { id: string; sku: string };
    lowProductId = low.id;
    lowProductSku = low.sku;
    await page.close();
  });

  test("requires contractor before checkout", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const pos = new PosIssuePage(page);
    await pos.goto();
    await pos.addFirstSearchResult(mainProductName);
    await pos.fillJob(jobCode);
    await pos.fillAddress("100 Guardrail Ln");
    await pos.completeSale();
    await expect(page.getByText("Please select a contractor")).toBeVisible();
  });

  test("requires job ID", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const pos = new PosIssuePage(page);
    await pos.goto();
    await pos.addFirstSearchResult(mainProductName);
    await pos.selectFirstContractor();
    await pos.clearJob();
    await pos.fillAddress("200 Guardrail Ln");
    await pos.completeSale();
    await expect(page.getByText("Job ID is required")).toBeVisible();
  });

  test("requires service address", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const pos = new PosIssuePage(page);
    await pos.goto();
    await pos.addFirstSearchResult(mainProductName);
    await pos.selectFirstContractor();
    await pos.fillJob(jobCode);
    await pos.clearAddress();
    await pos.completeSale();
    await expect(page.getByText("Service address is required")).toBeVisible();
  });

  test("happy path completes sale", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const pos = new PosIssuePage(page);
    await pos.goto();
    await pos.addFirstSearchResult(mainProductName);
    await pos.selectFirstContractor();
    await pos.fillJob(jobCode);
    await pos.fillAddress("400 Guardrail Ln");
    await pos.completeSale();
    await expect(page.getByText(/sale complete/i)).toBeVisible({ timeout: 15_000 });
  });

  test("surfaces insufficient stock when backend has less than cart (stale client qty)", async ({
    page,
    request,
  }) => {
    await new LoginPage(page).loginAsAdmin();
    const pos = new PosIssuePage(page);
    await pos.goto();
    await pos.addFirstSearchResult(lowProductName);
    await pos.setLineQuantity(lowProductSku, 5);

    const ctx = await freshSeed(request);
    const inventory = new InventoryApi(request, ctx.token);
    await inventory.adjustStock(lowProductId, { quantity_delta: -4, reason: "e2e-drain-stock" });

    // inventory.updated WS invalidates products; syncStock lowers max_quantity while line qty stays 5
    await page.waitForTimeout(3000);

    await pos.selectFirstContractor();
    await pos.fillJob(jobCode);
    await pos.fillAddress("300 Guardrail Ln");
    await pos.completeSale();

    const skuPat = new RegExp(lowProductSku.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    await expect(page.getByText(/not enough/i).filter({ hasText: skuPat })).toBeVisible({
      timeout: 15_000,
    });
  });
});
