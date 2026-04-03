import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

test.describe("Inventory detail panel", () => {
  test("row click opens inline stock detail", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("stock-levels");
    await expect(page.getByTestId("inventory-page")).toBeVisible({ timeout: 30_000 });

    const row = page.locator("tbody tr").first();
    await expect(row).toBeVisible();
    await row.click();

    await expect(page.getByTestId("inventory-detail-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Adjust Stock" }).first()).toBeVisible();
  });
});
