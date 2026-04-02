import { test, expect } from "@playwright/test";
import { freshSeed, type SeedContext } from "@support/api-client";
import { e2eScopedProductName, e2eSessionLabel, uniqueE2eBarcode } from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();
import { CatalogApi } from "@api/catalog.api";
import { PurchasingApi } from "@api/purchasing.api";
import { ReportsApi } from "@api/reports.api";
import { InventoryApi } from "@api/inventory.api";
import { LoginPage } from "@pages/login.page";
import { PurchasingPage } from "@pages/purchasing.page";

/**
 * Story 3 — PO receiving increases stock and inventory cost
 */

const PRODUCT = { name: "Deck Screws #8 3in Box/1000", price: 35.0, cost: 18.0, quantity: 5, min_stock: 20 };
const PO_QTY = 50;

test.describe.serial("Story 3: PO receiving and stock", () => {
  let ctx: SeedContext;
  let productId: string;
  let vendorName: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const req = page.request;
    ctx = await freshSeed(req);
    const catalog = new CatalogApi(req, ctx.token);

    const vendors = (await catalog.listVendors()) as Array<{ name: string }>;
    vendorName = vendors[0].name;

    const product = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(PRODUCT.name, E2E_SESSION),
      category_id: ctx.categoryIds["HDW"] ?? Object.values(ctx.categoryIds)[0],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };
    productId = product.id;
    await page.close();
  });

  test("3a — product starts as low stock", async ({ request }) => {
    const reports = new ReportsApi(request, ctx.token);
    const stats = (await reports.dashboardStats()) as { low_stock_count: number };
    expect(stats.low_stock_count).toBeGreaterThanOrEqual(1);
  });

  test("3b — create PO and receive items increases stock", async ({ request }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const reports = new ReportsApi(request, ctx.token);
    const purchasing = new PurchasingApi(request, ctx.token);
    const inventory = new InventoryApi(request, ctx.token);

    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number; sku: string; name: string }>;
    const p = products.find((x) => x.id === productId)!;
    const stockBefore = p.quantity;

    const statsBefore = (await reports.dashboardStats()) as { inventory_cost: number };
    const invCostBefore = statsBefore.inventory_cost;

    const created = (await purchasing.createPurchaseOrder({
      vendor_name: vendorName,
      create_vendor_if_missing: true,
      products: [
        {
          name: p.name,
          sku_id: productId,
          quantity: PO_QTY,
          cost: PRODUCT.cost,
          price: PRODUCT.cost,
          ai_parsed: true,
          suggested_department: "HDW",
        },
      ],
    })) as { id: string; status: string };
    expect(created.status).toBe("ordered");

    const po = (await purchasing.getPurchaseOrder(created.id)) as {
      id: string;
      status: string;
      items: Array<{ id: string }>;
    };

    await purchasing.recordDelivery(po.id, {
      item_ids: po.items.map((i) => i.id),
    });

    await purchasing.receive(po.id, {
      items: po.items.map((i) => ({ id: i.id, received_qty: PO_QTY })),
    });

    const productsAfter = (await catalog.listSkus()) as Array<{ id: string; quantity: number }>;
    const pAfter = productsAfter.find((x) => x.id === productId);
    expect(pAfter?.quantity).toBe(stockBefore + PO_QTY);

    const statsAfter = (await reports.dashboardStats()) as { inventory_cost: number };
    expect(statsAfter.inventory_cost).toBeCloseTo(invCostBefore + PRODUCT.cost * PO_QTY, 2);

    const history = (await inventory.getStockHistory(productId)) as {
      history: Array<{ transaction_type: string; quantity_delta: number }>;
    };
    const receiving = history.history.find((h) => h.transaction_type === "receiving");
    expect(receiving).toBeTruthy();
    expect(receiving?.quantity_delta).toBe(PO_QTY);
  });

  test("3c — low stock resolved after receiving", async ({ request, page }) => {
    const catalog = new CatalogApi(request, ctx.token);
    const products = (await catalog.listSkus()) as Array<{ id: string; quantity: number; min_stock: number }>;
    const p = products.find((x) => x.id === productId)!;
    expect(p.quantity).toBeGreaterThan(p.min_stock);

    await new LoginPage(page).loginAsAdmin();
    const poPage = new PurchasingPage(page);
    await poPage.gotoPurchaseOrders();
    await page.waitForTimeout(1000);
    await poPage.screenshot("03-purchase-orders");
    await poPage.gotoProducts();
    await page.waitForTimeout(1000);
    await poPage.screenshot("03-products-after-receiving");
  });
});
