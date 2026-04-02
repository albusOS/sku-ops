import { test as base, type Page } from "@playwright/test";
import { freshSeed, getAdminToken, type SeedContext } from "../support/api-client";
import { LoginPage } from "../pages/login.page";

type E2EFixtures = {
  adminToken: string;
  authenticatedPage: Page;
  seed: SeedContext;
};

export const test = base.extend<E2EFixtures>({
  adminToken: async ({ request }, use) => {
    const token = await getAdminToken(request);
    await use(token);
  },
  authenticatedPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await loginPage.loginAsAdmin();
    await use(page);
  },
  seed: async ({ request }, use) => {
    const ctx = await freshSeed(request);
    await use(ctx);
  },
});

export { expect } from "@playwright/test";
