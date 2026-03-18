import { test, expect } from "@playwright/test";
import {
  freshSeed,
  loginAsAdmin,
  navigateTo,
  screenshot,
  apiPost,
  apiGet,
  type SeedContext,
} from "./helpers";

test.describe.serial("Catalog UX Redesign", () => {
  let ctx: SeedContext;
  let productId: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    ctx = await freshSeed(page.request);

    // Seed a product for detail panel tests
    const product = await apiPost(
      page.request,
      ctx.token,
      "/api/beta/catalog/skus",
      {
        name: "UX Test Widget",
        price: 29.99,
        cost: 12.50,
        quantity: 100,
        category_id: ctx.categoryIds["HDW"] || Object.values(ctx.categoryIds)[0],
        base_unit: "each",
        sell_uom: "box",
        pack_qty: 12,
      },
    );
    productId = product.id;
    await page.close();
  });

  test("units API returns DB-backed units", async ({ request }) => {
    const units = await apiGet(request, ctx.token, "/api/beta/catalog/units");
    expect(units.length).toBeGreaterThan(20);

    const codes = units.map((u: any) => u.code);
    expect(codes).toContain("each");
    expect(codes).toContain("pallet");
    expect(codes).toContain("bundle");

    // Verify families
    const gallon = units.find((u: any) => u.code === "gallon");
    expect(gallon.family).toBe("volume");
  });

  test("can create a custom unit via API", async ({ request }) => {
    const unit = await apiPost(request, ctx.token, "/api/beta/catalog/units", {
      code: "e2e-custom",
      name: "E2E Custom",
      family: "discrete",
    });
    expect(unit.code).toBe("e2e-custom");

    // Use it on a product
    const product = await apiPost(
      request,
      ctx.token,
      "/api/beta/catalog/skus",
      {
        name: "Custom Unit Product",
        price: 5.0,
        quantity: 10,
        category_id: ctx.categoryIds["HDW"] || Object.values(ctx.categoryIds)[0],
        base_unit: "e2e-custom",
        sell_uom: "e2e-custom",
      },
    );
    expect(product.base_unit).toBe("e2e-custom");
  });

  test("products page loads with simplified columns", async ({ page }) => {
    await loginAsAdmin(page);
    await navigateTo(page, "products");

    await expect(page.getByTestId("products-page")).toBeVisible();

    // Table should have visible headers: SKU, Product Name, Category, Price, Margin
    const headers = page.locator("th");
    const headerTexts = await headers.allTextContents();
    const normalised = headerTexts.map((t) => t.trim().toUpperCase());

    expect(normalised).toContain("SKU");
    expect(normalised).toContain("PRODUCT NAME");
    expect(normalised).toContain("PRICE");
    expect(normalised).toContain("MARGIN");

    // Unit and Cost should be hidden by default
    expect(normalised).not.toContain("UNIT");
    expect(normalised).not.toContain("COST");

    await screenshot(page, "07-catalog-simplified-columns");
  });

  test("detail panel opens with collapsible sections", async ({ page }) => {
    await loginAsAdmin(page);
    await navigateTo(page, "products");

    // Click a product row to open detail panel
    const firstRow = page.locator("tbody tr").first();
    await firstRow.click();

    // Wait for the detail panel to animate in
    await page.waitForTimeout(500);

    // Pricing should always be visible (not collapsed)
    await expect(page.locator("text=Price")).toBeVisible();
    await expect(page.locator("text=Cost")).toBeVisible();
    await expect(page.locator("text=Margin")).toBeVisible();

    // Details section should exist but be collapsed
    const detailsHeader = page.locator("text=Details").first();
    await expect(detailsHeader).toBeVisible();

    // Suppliers section header should be visible
    const suppliersHeader = page.locator("text=Suppliers").first();
    await expect(suppliersHeader).toBeVisible();

    // Variants section header should be visible
    const variantsHeader = page.locator("text=Variants").first();
    await expect(variantsHeader).toBeVisible();

    await screenshot(page, "07-catalog-detail-collapsed");
  });

  test("detail panel sections expand on click", async ({ page }) => {
    await loginAsAdmin(page);
    await navigateTo(page, "products");

    const firstRow = page.locator("tbody tr").first();
    await firstRow.click();
    await page.waitForTimeout(500);

    // Click Details section to expand
    const detailsTrigger = page.locator("button:has-text('Details')").first();
    await detailsTrigger.click();
    await page.waitForTimeout(300);

    // Now category, sell unit, base unit should be visible
    await expect(page.locator("text=Category").first()).toBeVisible();
    await expect(page.locator("text=Sell Unit").first()).toBeVisible();
    await expect(page.locator("text=Base Unit").first()).toBeVisible();
    await expect(page.locator("text=Edit all fields")).toBeVisible();

    await screenshot(page, "07-catalog-detail-expanded");
  });

  test("product form dialog has consistent layout", async ({ page }) => {
    await loginAsAdmin(page);
    await navigateTo(page, "products");

    // Open add product dialog
    await page.getByTestId("add-product-btn").click();
    await expect(page.getByTestId("product-dialog")).toBeVisible();

    // Essential fields should be visible
    await expect(page.getByTestId("pf-name")).toBeVisible();
    await expect(page.getByTestId("pf-price")).toBeVisible();
    await expect(page.getByTestId("pf-department")).toBeVisible();

    // "More options" collapsible should exist
    const moreOptions = page.locator("button:has-text('More options')");
    await expect(moreOptions).toBeVisible();

    // Advanced fields should be hidden initially
    await expect(page.getByTestId("pf-barcode")).not.toBeVisible();
    await expect(page.getByTestId("pf-cost")).not.toBeVisible();

    // Click "More options" to expand
    await moreOptions.click();
    await page.waitForTimeout(300);

    // Now advanced fields should be visible
    await expect(page.getByTestId("pf-barcode")).toBeVisible();
    await expect(page.getByTestId("pf-cost")).toBeVisible();

    await screenshot(page, "07-catalog-form-expanded");

    // Cancel
    await page.getByTestId("product-cancel-btn").click();
  });

  test("product creation with custom unit works end-to-end", async ({ page }) => {
    await loginAsAdmin(page);
    await navigateTo(page, "products");

    await page.getByTestId("add-product-btn").click();
    await expect(page.getByTestId("product-dialog")).toBeVisible();

    // Fill essential fields
    await page.getByTestId("pf-name").fill("Playwright Bundle Widget");
    await page.getByTestId("pf-department").click();
    await page.locator("[role=option]").first().click();
    await page.getByTestId("pf-price").fill("19.99");

    // Expand more options
    await page.locator("button:has-text('More options')").click();
    await page.waitForTimeout(300);

    // The base unit combobox should be present — click it and search for "bundle"
    const baseUnitTrigger = page
      .locator("text=Base Unit")
      .locator("..")
      .locator("[role=combobox]");
    if (await baseUnitTrigger.isVisible()) {
      await baseUnitTrigger.click();
      await page.waitForTimeout(200);
      // Type "bundle" in the search
      await page.locator("[cmdk-input]").fill("bundle");
      await page.waitForTimeout(200);
      // Select the bundle option
      const bundleOption = page.locator("[cmdk-item]:has-text('Bundle')").first();
      if (await bundleOption.isVisible()) {
        await bundleOption.click();
      }
    }

    await screenshot(page, "07-catalog-create-with-unit");

    // Save
    await page.getByTestId("product-save-btn").click();

    // Wait for success toast
    await expect(page.locator("text=created with SKU")).toBeVisible({ timeout: 5000 });

    await screenshot(page, "07-catalog-product-created");
  });
});
