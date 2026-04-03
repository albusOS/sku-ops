import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

test.describe("Contractor my history", () => {
  test("stats and orders region render; search input works", async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("my-orders");
    await expect(page).toHaveURL(/\/my-history$/);
    await expect(page.getByTestId("my-history-page")).toBeVisible();
    await expect(page.getByText("Total Orders", { exact: true })).toBeVisible();
    await expect(page.getByTestId("withdrawals-list").getByText("Orders", { exact: true })).toBeVisible();
    await expect(page.getByTestId("withdrawals-list")).toBeVisible();

    const search = page.getByTestId("my-history-order-search");
    await search.fill("nonexistent-xyz-123");
    await expect(page.getByText("No orders match these filters")).toBeVisible();
    await search.clear();
  });
});
