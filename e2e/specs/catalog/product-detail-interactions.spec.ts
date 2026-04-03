import { expect, test } from "@playwright/test";
import { CatalogApi } from "@api/catalog.api";
import { LoginPage } from "@pages/login.page";
import { getAdminToken } from "@support/api-client";

test.describe("Product detail interactions", () => {
  test("header Edit opens dialog then cancel", async ({ page, request }) => {
    const token = await getAdminToken(request);
    const catalog = new CatalogApi(request, token);
    const skus = (await catalog.listSkus()) as Array<{ id: string; product_family_id?: string | null }>;
    expect(skus.length).toBeGreaterThan(0);
    const familyId = skus[0].product_family_id ?? skus[0].id;

    await new LoginPage(page).loginAsAdmin();
    await page.goto(`/products/${familyId}`);
    await expect(page.getByTestId("product-detail-page")).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Edit" }).first().click();
    await expect(page.getByTestId("product-dialog")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("product-cancel-btn").click();
    await expect(page.getByTestId("product-dialog")).toBeHidden({ timeout: 10_000 });
  });
});
