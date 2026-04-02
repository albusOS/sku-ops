import { test, expect } from "@playwright/test";
import { freshSeed, type SeedContext } from "@support/api-client";
import { e2eScopedProductName, e2eSessionLabel, uniqueE2eBarcode } from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();
import { CatalogApi } from "@api/catalog.api";
import { InventoryApi } from "@api/inventory.api";
import { ReportsApi } from "@api/reports.api";
import { LoginPage } from "@pages/login.page";
import { InventoryPage } from "@pages/inventory.page";

/**
 * Story 4 — Stock adjustments track correctly
 */

const PRODUCT = { name: "Interior Latex Paint 1gal White", price: 32.0, cost: 18.0, quantity: 25, min_stock: 5 };

test.describe.serial("Story 4: Stock adjustments", () => {
  let ctx: SeedContext;
  let productId: string;
  /** Dashboard aggregate after seed product exists (org may hold more inventory). */
  let inventoryCostBaseline: number;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const request = page.request;
    ctx = await freshSeed(request);
    const catalog = new CatalogApi(request, ctx.token);
    const reports = new ReportsApi(request, ctx.token);
    const product = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(PRODUCT.name, E2E_SESSION),
      category_id: ctx.categoryIds["PNT"],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };
    productId = product.id;
    inventoryCostBaseline = (
      (await reports.dashboardStats()) as { inventory_cost: number }
    ).inventory_cost;
    await page.close();
  });

  test("4a — positive adjustment increases stock", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const inventory = new InventoryApi(request, ctx.token);

    await inventory.adjustStock(productId, {
      quantity_delta: 10,
      reason: "Correction",
    });

    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number }>;
    const p = products.find((x) => x.id === productId);
    expect(p?.quantity).toBe(PRODUCT.quantity + 10);

    const history = (await inventory.getStockHistory(productId)) as {
      history: Array<{ transaction_type: string; quantity_delta: number; quantity_after: number }>;
    };
    const adj = history.history.find(
      (h) => h.transaction_type === "adjustment" && h.quantity_delta === 10,
    );
    expect(adj).toBeTruthy();
    expect(adj?.quantity_after).toBe(PRODUCT.quantity + 10);
  });

  test("4b — negative adjustment decreases stock", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const inventory = new InventoryApi(request, ctx.token);

    await inventory.adjustStock(productId, {
      quantity_delta: -3,
      reason: "Damage",
    });

    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number }>;
    const p = products.find((x) => x.id === productId);
    expect(p?.quantity).toBe(PRODUCT.quantity + 10 - 3);

    const history = (await inventory.getStockHistory(productId)) as {
      history: Array<{ transaction_type: string; quantity_delta: number; reason?: string }>;
    };
    const adj = history.history.find(
      (h) => h.transaction_type === "adjustment" && h.quantity_delta === -3,
    );
    expect(adj).toBeTruthy();
    expect(adj?.reason).toBe("Damage");
  });

  test("4c — inventory cost reflects adjusted quantities", async ({ request, page }) => {
    const reports = new ReportsApi(request, ctx.token);
    const stats = (await reports.dashboardStats()) as { inventory_cost: number };
    const netQtyDelta = 10 - 3;
    expect(stats.inventory_cost).toBeCloseTo(
      inventoryCostBaseline + PRODUCT.cost * netQtyDelta,
      2,
    );

    await new LoginPage(page).loginAsAdmin();
    const invPage = new InventoryPage(page);
    await invPage.gotoDashboard();
    await page.waitForTimeout(1000);
    await invPage.screenshot("04-dashboard-after-adjustments");
  });
});
