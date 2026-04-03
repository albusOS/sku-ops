/**
 * Goal: every primary admin surface mounts after real sidebar navigation.
 * Complements story specs (API-heavy flows) with UI routing/interactivity smoke.
 */
import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";

const adminRoutes: Array<{ navTestId: string; path: string; pageTestId: string }> = [
  { navTestId: "dashboard", path: "/", pageTestId: "dashboard-page" },
  { navTestId: "reports", path: "/reports", pageTestId: "reports-page" },
  { navTestId: "point-of-sale", path: "/pos", pageTestId: "pos-page" },
  { navTestId: "contractors", path: "/contractors", pageTestId: "contractors-page" },
  { navTestId: "jobs", path: "/jobs", pageTestId: "jobs-page" },
  { navTestId: "products", path: "/products", pageTestId: "products-page" },
  { navTestId: "categories", path: "/departments", pageTestId: "departments-page" },
  { navTestId: "vendors", path: "/vendors", pageTestId: "vendors-page" },
  { navTestId: "stock-levels", path: "/inventory", pageTestId: "inventory-page" },
  { navTestId: "stock-counts", path: "/cycle-counts", pageTestId: "cycle-counts-page" },
  { navTestId: "purchasing", path: "/purchasing", pageTestId: "purchasing-page" },
  { navTestId: "xero-status", path: "/xero-health", pageTestId: "xero-health-page" },
  { navTestId: "settings", path: "/settings", pageTestId: "settings-page" },
];

test.describe("Admin app shell", () => {
  test.beforeEach(async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
  });

  for (const { navTestId, path, pageTestId } of adminRoutes) {
    test(`sidebar → ${navTestId} (${path})`, async ({ page }) => {
      const sidebar = new SidebarNav(page);
      await sidebar.navigateTo(navTestId);
      await expect(page).toHaveURL((u) => u.pathname === path);
      const timeout = pageTestId === "dashboard-page" ? 60_000 : 30_000;
      await expect(page.getByTestId(pageTestId)).toBeVisible({ timeout });
    });
  }

  test("POS quick links: direct issue and scan mode", async ({ page }) => {
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("point-of-sale");
    await expect(page.getByTestId("pos-page")).toBeVisible();

    await page.getByRole("link", { name: /new sale/i }).click();
    await expect(page).toHaveURL(/\/pos\/issue$/);
    await expect(page.getByTestId("pos-page")).toBeVisible();

    await page.goBack();
    await expect(page).toHaveURL(/\/pos$/);

    await page.getByRole("link", { name: /scan mode/i }).click();
    await expect(page).toHaveURL(/\/pos\/scan$/);
    await expect(page.getByTestId("scan-mode-page")).toBeVisible({ timeout: 30_000 });
  });
});
