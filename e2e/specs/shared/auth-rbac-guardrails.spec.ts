/**
 * Goal: users cannot reach role-inappropriate routes by typing URLs or using stale bookmarks.
 * Router sends wrong-role users to `/`; unauthenticated users to `/login`.
 */
import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";

test.describe("Auth and RBAC guardrails", () => {
  test("unauthenticated visit to /products redirects to login", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("contractor cannot open admin catalog or finance URLs (forced to dashboard)", async ({
    page,
  }) => {
    await new LoginPage(page).loginAsContractor();
    for (const path of ["/products", "/inventory", "/reports", "/settings", "/pos", "/pos/issue"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expect(page).toHaveURL((u) => u.pathname === "/");
      await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 15_000 });
    }
  });

  test("contractor can open shared scan routes (admin-grade checkout surfaces)", async ({
    page,
  }) => {
    await new LoginPage(page).loginAsContractor();
    await page.goto("/pos/scan");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL((u) => u.pathname === "/pos/scan");
    await expect(page.getByTestId("scan-mode-page")).toBeVisible({ timeout: 30_000 });
  });

  test("admin cannot open contractor-only materials or history URLs", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    for (const path of ["/request-materials", "/my-history"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expect(page).toHaveURL((u) => u.pathname === "/");
    }
  });

  test("legacy /invoices sends admin to POS", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    await page.goto("/invoices");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL((u) => u.pathname === "/pos");
    await expect(page.getByTestId("pos-page")).toBeVisible();
  });

  test("legacy /invoices cannot strand contractor on POS (dashboard)", async ({ page }) => {
    await new LoginPage(page).loginAsContractor();
    await page.goto("/invoices");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL((u) => u.pathname === "/");
    await expect(page.getByTestId("dashboard-page")).toBeVisible();
  });

  test("legacy /billing-entities redirects admin to contractors", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    await page.goto("/billing-entities");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL((u) => u.pathname === "/contractors");
    await expect(page.getByTestId("contractors-page")).toBeVisible();
  });

  test("admin cannot open bogus cycle count id (graceful not-found)", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    await page.goto("/cycle-counts/00000000-0000-0000-0000-000000000001");
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("cycle-count-not-found")).toBeVisible({ timeout: 15_000 });
  });
});
