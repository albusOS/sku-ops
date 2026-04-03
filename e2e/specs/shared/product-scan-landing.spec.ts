/**
 * Goal: QR deep link /product/scan/:code handles unknown codes and known barcodes for each role.
 */
import { expect, test } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { freshSeed } from "@support/api-client";
import { e2eScopedProductName, e2eSessionLabel, uniqueE2eBarcode } from "@support/e2e-data";
import { LoginPage } from "@pages/login.page";

const E2E_SESSION = e2eSessionLabel();

test.describe.serial("Product scan landing (QR deep links)", () => {
  let barcode: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const ctx = await freshSeed(page.request);
    const catalog = new CatalogApi(page.request, ctx.token);
    barcode = uniqueE2eBarcode();
    await catalog.createSku({
      name: e2eScopedProductName("QR Deep Link SKU", E2E_SESSION),
      price: 11,
      cost: 6,
      quantity: 20,
      min_stock: 2,
      category_id: ctx.categoryIds["MSC"] ?? Object.values(ctx.categoryIds)[0],
      barcode,
    });
    await page.close();
  });

  test("unknown code shows not-found UX after login", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    await page.goto(`/product/scan/${encodeURIComponent("no-such-barcode-e2e-999")}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("product-scan-landing")).toBeVisible();
    await expect(page.getByRole("heading", { name: /product not found/i })).toBeVisible();
  });

  test("known barcode shows product and inventory CTA for admin", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    await page.goto(`/product/scan/${encodeURIComponent(barcode)}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("product-scan-landing")).toBeVisible();
    await expect(page.getByRole("button", { name: /view in inventory/i })).toBeVisible();
  });

  test("known barcode shows add-to-cart for contractor", async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
    await page.goto(`/product/scan/${encodeURIComponent(barcode)}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("product-scan-landing")).toBeVisible();
    await expect(page.getByRole("button", { name: /add to cart/i })).toBeVisible();
  });
});
