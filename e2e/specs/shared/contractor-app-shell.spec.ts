/**
 * Goal: contractor role nav resolves and primary pages mount.
 * Uses provisioned `DEV_CONTRACTOR` from `devtools/scripts/company.py`.
 */
import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

const contractorRoutes: Array<{ navTestId: string; path: string; pageTestId: string }> = [
  { navTestId: "dashboard", path: "/", pageTestId: "dashboard-page" },
  { navTestId: "browse-&-order", path: "/request-materials", pageTestId: "request-materials-page" },
  { navTestId: "scan-&-checkout", path: "/scan", pageTestId: "scan-mode-page" },
  { navTestId: "my-orders", path: "/my-history", pageTestId: "my-history-page" },
];

test.describe("Contractor app shell", () => {
  test.beforeEach(async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
  });

  for (const { navTestId, path, pageTestId } of contractorRoutes) {
    test(`sidebar → ${navTestId} (${path})`, async ({ page }) => {
      const sidebar = new SidebarNav(page);
      await sidebar.navigateTo(navTestId);
      await expect(page).toHaveURL((u) => u.pathname === path);
      await expect(page.getByTestId(pageTestId)).toBeVisible({ timeout: 30_000 });
    });
  }
});
