import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

test.describe("POS hub interactions", () => {
  test.beforeEach(async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("point-of-sale");
    await expect(page.getByTestId("pos-page")).toBeVisible();
  });

  test("process sales and invoices sections render with table", async ({ page }) => {
    await expect(page.getByTestId("pos-process-sales")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pickup orders" })).toBeVisible();
    await expect(page.getByTestId("pos-invoices-section")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Invoices", exact: true })).toBeVisible();

    const table = page.getByTestId("pos-invoices-section").locator("table");
    await expect(table).toBeVisible();
  });

  test("POS page shows returns subsection when section loads", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /returns/i })).toBeVisible({ timeout: 30_000 });
  });
});
