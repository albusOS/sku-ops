/**
 * Goal: contractor Browse & Order flow validates cart + modal, then submits successfully.
 */
import { expect, test } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { JobsApi } from "@api/jobs.api";
import { LoginPage } from "@pages/login.page";
import { freshSeed } from "@support/api-client";
import { e2eScopedProductName, e2eSessionLabel, uniqueE2eBarcode, uniqueJobCode } from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();

test.describe.serial("Contractor material request", () => {
  let productName: string;
  /** Must exist in DB: material_requests.job_id is resolved from job code on create. */
  let existingJobCode: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const ctx = await freshSeed(page.request);
    const catalog = new CatalogApi(page.request, ctx.token);
    const jobs = new JobsApi(page.request, ctx.token);
    existingJobCode = uniqueJobCode("E2E-MR-SEED");
    await jobs.createJob({ code: existingJobCode });
    const skuSuffix = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    productName = e2eScopedProductName(`Contractor Req Coil E2E ${skuSuffix}`, E2E_SESSION);
    await catalog.createSku({
      name: productName,
      price: 9,
      cost: 4,
      quantity: 25,
      min_stock: 2,
      category_id: ctx.categoryIds["ELW"] ?? Object.values(ctx.categoryIds)[0],
      barcode: uniqueE2eBarcode(),
    });
    await page.close();
  });

  test("submit request disabled when cart is empty", async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
    await page.goto("/request-materials");
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("request-materials-page")).toBeVisible();
    await expect(page.getByTestId("submit-request-btn")).toBeDisabled();
  });

  test("modal requires job and service address", async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
    await page.goto("/request-materials");
    await page.waitForLoadState("networkidle");

    await page.getByPlaceholder(/search by name/i).fill(productName);
    await expect(page.getByText(/\d+ product/)).toBeVisible();
    await page.getByRole("button", { name: /^Add$/ }).first().click();

    await page.getByTestId("submit-request-btn").click();
    await expect(page.getByTestId("submit-request-modal")).toBeVisible();

    const confirm = page.getByTestId("confirm-material-request-btn");
    await expect(confirm).toBeDisabled();
    await expect(page.getByText(/job and address are required/i)).toBeVisible();
  });

  test("happy path submits material request", async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
    await page.goto("/request-materials");
    await page.waitForLoadState("networkidle");

    await page.getByPlaceholder(/search by name/i).fill(productName);
    await page.getByRole("button", { name: /^Add$/ }).first().click();
    await page.getByTestId("submit-request-btn").click();
    const modal = page.getByTestId("submit-request-modal");
    await expect(modal).toBeVisible();

    await modal.getByTestId("job-picker-input").fill(existingJobCode);
    await modal.getByTestId("address-picker-input").fill("600 Material Request Way");

    const submitRespPromise = page.waitForResponse(
      (r) =>
        r.url().includes("material-requests") &&
        r.request().method() === "POST" &&
        !r.url().includes("/process"),
    );
    await modal.getByTestId("confirm-material-request-btn").click();
    const submitResp = await submitRespPromise;
    expect(
      submitResp.ok(),
      `material-request POST failed: ${submitResp.status()} ${await submitResp.text()}`,
    ).toBeTruthy();

    await expect(page.getByText(/material request submitted/i)).toBeVisible({ timeout: 15_000 });
  });
});
