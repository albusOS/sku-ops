import { expect, type Page } from "@playwright/test";

export class OnboardingPage {
  constructor(readonly page: Page) {}

  async loginAsOnboardingAdmin(): Promise<void> {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
    await this.page.getByTestId("login-role-admin").click();
    await this.page.getByTestId("login-email-input").fill("e2e-onboard-admin@test.local");
    await this.page.getByTestId("login-password-input").fill("dev123");
    await this.page.getByTestId("login-submit-btn").click();
    await this.page.waitForLoadState("networkidle");
  }

  async loginAsOnboardingContractor(): Promise<void> {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
    await this.page.getByTestId("login-role-contractor").click();
    await this.page.getByTestId("login-email-input").fill("e2e-onboard-ctr@test.local");
    await this.page.getByTestId("login-password-input").fill("dev123");
    await this.page.getByTestId("login-submit-btn").click();
    await this.page.waitForLoadState("networkidle");
  }

  async expectDialogVisible(): Promise<void> {
    await expect(this.page.getByTestId("onboarding-dialog")).toBeVisible({ timeout: 10_000 });
  }

  async expectDialogNotVisible(): Promise<void> {
    await expect(this.page.getByTestId("onboarding-dialog")).not.toBeVisible({ timeout: 5_000 });
  }

  async selectOrganization(orgName: string): Promise<void> {
    const select = this.page.getByTestId("onboarding-org-select");
    await select.selectOption({ label: orgName });
  }

  async selectCreateNewOrganization(): Promise<void> {
    const select = this.page.getByTestId("onboarding-org-select");
    await select.selectOption({ value: "__create_new__" });
  }

  async fillOrganizationName(name: string): Promise<void> {
    await this.page.getByTestId("onboarding-org-name-input").fill(name);
  }

  async fillCompany(company: string): Promise<void> {
    await this.page.getByTestId("onboarding-company-input").fill(company);
  }

  async fillPhone(phone: string): Promise<void> {
    await this.page.getByTestId("onboarding-phone-input").fill(phone);
  }

  async submit(): Promise<void> {
    await this.page.getByTestId("onboarding-submit-btn").click();
  }

  async expectAppLayoutVisible(): Promise<void> {
    await expect(this.page.getByTestId("app-layout")).toBeVisible({ timeout: 15_000 });
  }
}
