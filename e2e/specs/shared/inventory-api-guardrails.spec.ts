/**
 * Goal: API rejects adjustments that would corrupt inventory (oversell via adjust, zero delta).
 */
import { expect, test } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { apiPostExpectStatus } from "@support/api-client";
import { freshSeed, API_BASE_URL } from "@support/api-client";
import { e2eScopedProductName, e2eSessionLabel, uniqueE2eBarcode } from "@support/e2e-data";

const E2E_SESSION = e2eSessionLabel();
const PRODUCT = {
  name: "Guardrail Stock Widget",
  price: 10,
  cost: 5,
  quantity: 4,
  min_stock: 1,
};

test.describe("Inventory API guardrails", () => {
  test("reject adjustment that would make quantity negative", async ({ request }) => {
    const ctx = await freshSeed(request);
    const catalog = new CatalogApi(request, ctx.token);
    const u = `${Date.now()}-a`;
    const created = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(`${PRODUCT.name} ${u}`, E2E_SESSION),
      category_id: ctx.categoryIds["ELE"] ?? Object.values(ctx.categoryIds)[0],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };

    await apiPostExpectStatus(
      request,
      ctx.token,
      `/api/beta/inventory/stock/${created.id}/adjust`,
      { quantity_delta: -PRODUCT.quantity - 1, reason: "e2e-negative-guard" },
      400,
    );
  });

  test("reject zero quantity_delta", async ({ request }) => {
    const ctx = await freshSeed(request);
    const catalog = new CatalogApi(request, ctx.token);
    const u = `${Date.now()}-b`;
    const created = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(`${PRODUCT.name} ${u}`, E2E_SESSION),
      category_id: ctx.categoryIds["PNT"] ?? Object.values(ctx.categoryIds)[0],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };

    await apiPostExpectStatus(
      request,
      ctx.token,
      `/api/beta/inventory/stock/${created.id}/adjust`,
      { quantity_delta: 0, reason: "e2e-zero" },
      400,
    );
  });

  test("reject stock adjust without auth", async ({ request }) => {
    const ctx = await freshSeed(request);
    const catalog = new CatalogApi(request, ctx.token);
    const u = `${Date.now()}-c`;
    const created = (await catalog.createSku({
      ...PRODUCT,
      name: e2eScopedProductName(`${PRODUCT.name} ${u}`, E2E_SESSION),
      category_id: ctx.categoryIds["HDW"] ?? Object.values(ctx.categoryIds)[0],
      barcode: uniqueE2eBarcode(),
    })) as { id: string };

    const resp = await request.post(`${API_BASE_URL}/api/beta/inventory/stock/${created.id}/adjust`, {
      headers: { "Content-Type": "application/json" },
      data: { quantity_delta: 1, reason: "x" },
    });
    expect([401, 403]).toContain(resp.status());
  });
});
