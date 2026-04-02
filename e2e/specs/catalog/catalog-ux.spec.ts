import { test, expect } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { LoginPage } from "@pages/login.page";
import { CatalogPage } from "@pages/catalog.page";
import { freshSeed, type SeedContext } from "@support/api-client";
import { e2eIndexedProductName, e2eSessionLabel, uniqueE2eBarcode } from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();

test.describe.serial("Catalog UX Redesign", () => {
  let ctx: SeedContext;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    ctx = await freshSeed(page.request);
    const catalog = new CatalogApi(page.request, ctx.token);

    await catalog.createSku({
      name: e2eIndexedProductName("UX Test Widget", E2E_SESSION, 0),
      price: 29.99,
      cost: 12.5,
      quantity: 100,
      category_id: ctx.categoryIds["HDW"] || Object.values(ctx.categoryIds)[0],
      base_unit: "each",
      sell_uom: "box",
      pack_qty: 12,
      barcode: uniqueE2eBarcode(),
    });
    await page.close();
  });

  test("units API returns DB-backed units", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const units = (await catalog.listUnits()) as Array<{ code: string; family?: string }>;

    expect(units.length).toBeGreaterThan(20);

    const codes = units.map((u) => u.code);
    expect(codes).toContain("each");
    expect(codes).toContain("pallet");
    expect(codes).toContain("bundle");

    const gallon = units.find((u) => u.code === "gallon");
    expect(gallon?.family).toBe("volume");
  });

  test("can create a custom unit via API", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const unitCode = `e2e-custom-${Date.now().toString(36)}`;
    const unit = (await catalog.createUnit({
      code: unitCode,
      name: "E2E Custom",
      family: "discrete",
    })) as { code: string };
    expect(unit.code).toBe(unitCode);

    const product = (await catalog.createSku({
      name: e2eIndexedProductName("Custom Unit Product", E2E_SESSION, 1),
      price: 5.0,
      quantity: 10,
      category_id: ctx.categoryIds["HDW"] || Object.values(ctx.categoryIds)[0],
      base_unit: unitCode,
      sell_uom: unitCode,
    })) as { base_unit: string };
    expect(product.base_unit).toBe(unitCode);
  });

  test("products page loads with simplified columns", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const catalogPage = new CatalogPage(page);
    await catalogPage.goto();
    await catalogPage.switchToTableView();

    await expect(catalogPage.productsRoot).toBeVisible();

    const headers = page.locator("th");
    const headerTexts = await headers.allTextContents();
    const normalised = headerTexts.map((t) => t.trim().toUpperCase());

    expect(normalised).toContain("SKU");
    expect(normalised).toContain("PRODUCT NAME");
    expect(normalised).toContain("CATEGORY");
    expect(normalised).toContain("PRICE");
    // Margin lives in the detail panel, not the simplified table (ProductsPage.jsx columns).

    expect(normalised).not.toContain("UNIT");
    expect(normalised).not.toContain("COST");

    await catalogPage.screenshot("07-catalog-simplified-columns");
  });

  test("detail panel opens with collapsible sections", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const catalogPage = new CatalogPage(page);
    await catalogPage.goto();
    await catalogPage.switchToTableView();

    await catalogPage.clickFirstProductRow();

    await expect(page.locator("text=Price")).toBeVisible();
    await expect(page.locator("text=Cost")).toBeVisible();
    await expect(page.locator("text=Margin")).toBeVisible();

    const detailsHeader = page.locator("text=Details").first();
    await expect(detailsHeader).toBeVisible();

    const suppliersHeader = page.locator("text=Suppliers").first();
    await expect(suppliersHeader).toBeVisible();

    const variantsHeader = page.locator("text=Variants").first();
    await expect(variantsHeader).toBeVisible();

    await catalogPage.screenshot("07-catalog-detail-collapsed");
  });

  test("detail panel sections expand on click", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const catalogPage = new CatalogPage(page);
    await catalogPage.goto();
    await catalogPage.switchToTableView();

    await catalogPage.clickFirstProductRow();

    const detailsTrigger = page.locator("button:has-text('Details')").first();
    await detailsTrigger.click();
    await page.waitForTimeout(300);

    await expect(page.locator("text=Category").first()).toBeVisible();
    await expect(page.locator("text=Sell Unit").first()).toBeVisible();
    await expect(page.locator("text=Base Unit").first()).toBeVisible();
    await expect(page.locator("text=Edit all fields")).toBeVisible();

    await catalogPage.screenshot("07-catalog-detail-expanded");
  });

  test("product form dialog has consistent layout", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const catalogPage = new CatalogPage(page);
    await catalogPage.goto();
    await catalogPage.switchToTableView();

    await catalogPage.openAddProductDialog();
    await expect(catalogPage.productDialog).toBeVisible();

    await expect(catalogPage.nameInput).toBeVisible();
    await expect(catalogPage.priceInput).toBeVisible();
    await expect(catalogPage.departmentSelect).toBeVisible();

    const moreOptions = catalogPage.moreOptionsBtn;
    await expect(moreOptions).toBeVisible();

    await expect(catalogPage.barcodeInput).not.toBeVisible();
    await expect(catalogPage.costInput).not.toBeVisible();

    await moreOptions.click();
    await page.waitForTimeout(300);

    await expect(catalogPage.barcodeInput).toBeVisible();
    await expect(catalogPage.costInput).toBeVisible();

    await catalogPage.screenshot("07-catalog-form-expanded");

    await catalogPage.page.keyboard.press("Escape");
  });

  test("product creation with custom unit works end-to-end", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const catalogPage = new CatalogPage(page);
    await catalogPage.goto();
    await catalogPage.switchToTableView();

    await catalogPage.openAddProductDialog();
    await expect(catalogPage.productDialog).toBeVisible();

    await catalogPage.nameInput.fill(e2eIndexedProductName("Playwright Bundle Widget", E2E_SESSION, 2));
    await catalogPage.departmentSelect.click();
    await page.locator("[role=option]").first().click();
    await catalogPage.priceInput.fill("19.99");

    await catalogPage.moreOptionsBtn.click();
    await page.waitForTimeout(300);

    const baseUnitTrigger = page
      .locator("text=Base Unit")
      .locator("..")
      .locator("[role=combobox]");
    if (await baseUnitTrigger.isVisible()) {
      await baseUnitTrigger.click();
      await page.waitForTimeout(200);
      await page.locator("[cmdk-input]").fill("bundle");
      await page.waitForTimeout(200);
      const bundleOption = page.locator("[cmdk-item]:has-text('Bundle')").first();
      if (await bundleOption.isVisible()) {
        await bundleOption.click();
      }
    }

    await catalogPage.screenshot("07-catalog-create-with-unit");

    await catalogPage.saveBtn.evaluate((el: HTMLElement) => el.click());

    await expect(page.locator("text=created with SKU")).toBeVisible({ timeout: 5000 });

    await catalogPage.screenshot("07-catalog-product-created");
  });
});
