import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

test.describe("Contractors billing entities UI", () => {
  test("create billing entity opens detail panel", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("contractors");
    await expect(page.getByTestId("contractors-page")).toBeVisible({ timeout: 30_000 });

    await page.getByTestId("contractors-new-billing-entity-btn").click();
    await expect(page.getByTestId("billing-entity-dialog")).toBeVisible();

    const name = `E2E Billing ${Date.now().toString(36)}`;
    await page.getByTestId("billing-entity-name-input").fill(name);
    await page.getByTestId("billing-entity-save-btn").click();

    await expect(page.getByTestId("billing-entity-detail-panel")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(name, { exact: true }).first()).toBeVisible();
  });
});
