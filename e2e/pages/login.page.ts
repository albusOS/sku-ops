import { expect, type Page } from "@playwright/test";

export class LoginPage {
  constructor(readonly page: Page) {}

  async loginAsAdmin(): Promise<void> {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
    await this.page.getByTestId("login-email-input").fill("dev@supply-yard.local");
    await this.page.getByTestId("login-password-input").fill("dev123");
    await this.page.getByTestId("login-submit-btn").click();
    await this.page.waitForLoadState("networkidle");
    await expect(this.page.getByTestId("app-layout")).toBeVisible();
  }

  /** Provisioned dev user — see `devtools/scripts/company.py` (`DEV_CONTRACTOR`). */
  async loginAsContractor(): Promise<void> {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
    await this.page.getByTestId("login-role-contractor").click();
    await this.page.getByTestId("login-email-input").fill("contractor@supply-yard.local");
    await this.page.getByTestId("login-password-input").fill("dev123");
    await this.page.getByTestId("login-submit-btn").click();
    await this.page.waitForLoadState("networkidle");
    await expect(this.page.getByTestId("app-layout")).toBeVisible();
  }
}
