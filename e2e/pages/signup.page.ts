import { expect, type Page } from "@playwright/test";

export class SignupPage {
  constructor(readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
  }

  async toggleToSignup(): Promise<void> {
    await this.page.getByTestId("login-mode-toggle").click();
  }

  async toggleToSignin(): Promise<void> {
    await this.page.getByTestId("login-mode-toggle").click();
  }

  async selectRoleAdmin(): Promise<void> {
    await this.page.getByTestId("login-role-admin").click();
  }

  async selectRoleContractor(): Promise<void> {
    await this.page.getByTestId("login-role-contractor").click();
  }

  async fillSignupForm(name: string, email: string, password: string): Promise<void> {
    await this.page.getByTestId("signup-name-input").fill(name);
    await this.page.getByTestId("login-email-input").fill(email);
    await this.page.getByTestId("login-password-input").fill(password);
  }

  async enterAdminCode(code: string): Promise<void> {
    await this.page.getByTestId("signup-admin-code-input").fill(code);
  }

  async confirmAdminSignupGate(): Promise<void> {
    await this.page.getByTestId("signup-admin-unlock-btn").click();
  }

  async submitSignup(): Promise<void> {
    await this.page.getByTestId("login-submit-btn").click();
  }
}

export async function assertSignupLinkVisible(page: import("@playwright/test").Page): Promise<void> {
  await expect(page.getByTestId("login-mode-toggle")).toBeVisible();
  await expect(page.getByTestId("login-mode-toggle")).toHaveText(/sign up/i);
}
