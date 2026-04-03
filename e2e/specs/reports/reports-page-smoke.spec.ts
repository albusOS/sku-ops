import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

test.describe("Reports page smoke", () => {
  test("loads reports shell and date control", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("reports");
    await expect(page.getByTestId("reports-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("date-range-btn")).toBeVisible();
  });
});
