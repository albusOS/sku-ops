/**
 * Onboarding dialog E2E tests.
 * Tests the onboarding flow for users without an organization assignment.
 */
import { expect, test } from "@playwright/test";
import { LoginPage } from "../../pages/login.page";
import { OnboardingPage } from "../../pages/onboarding.page";

test.describe("Onboarding / login regression", () => {
  test("login page still works for seeded admin", async ({ page }) => {
    const login = new LoginPage(page);
    await login.loginAsAdmin();
  });

  test("login page still works for seeded contractor", async ({ page }) => {
    const login = new LoginPage(page);
    await login.loginAsContractor();
  });
});

test.describe("Onboarding dialog UI", () => {
  test("admin sees onboarding dialog with org dropdown", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingAdmin();
    await onboarding.expectDialogVisible();

    await expect(page.getByTestId("onboarding-org-select")).toBeVisible();
    await expect(page.getByTestId("onboarding-phone-input")).toBeVisible();
    await expect(page.getByTestId("onboarding-company-input")).not.toBeVisible();
    await expect(page.getByTestId("onboarding-org-name-input")).not.toBeVisible();
  });

  test("admin can toggle to create new org mode", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingAdmin();
    await onboarding.expectDialogVisible();

    await onboarding.selectCreateNewOrganization();
    await expect(page.getByTestId("onboarding-org-name-input")).toBeVisible();
  });

  test("contractor sees onboarding dialog with company and org dropdown", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingContractor();
    await onboarding.expectDialogVisible();

    await expect(page.getByTestId("onboarding-org-select")).toBeVisible();
    await expect(page.getByTestId("onboarding-company-input")).toBeVisible();
    await expect(page.getByTestId("onboarding-phone-input")).toBeVisible();
    await expect(page.getByTestId("onboarding-org-name-input")).not.toBeVisible();
  });

  test("contractor cannot create new organization (option not shown)", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingContractor();
    await onboarding.expectDialogVisible();

    const select = page.getByTestId("onboarding-org-select");
    const options = await select.locator("option").allTextContents();
    expect(options.some((o) => o.includes("Create new"))).toBe(false);
  });

  test("org dropdown shows existing organizations", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingAdmin();
    await onboarding.expectDialogVisible();

    const select = page.getByTestId("onboarding-org-select");
    await expect(select).toBeVisible();
    const options = await select.locator("option").allTextContents();
    expect(options.some((o) => o.includes("Supply Yard"))).toBe(true);
  });
});

test.describe("Onboarding form validation", () => {
  test("admin must select org before submitting", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingAdmin();
    await onboarding.expectDialogVisible();

    await onboarding.submit();
    await expect(page.getByText("Select an organization or create a new one")).toBeVisible({
      timeout: 5_000,
    });
  });

  test("admin must fill org name when creating new", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingAdmin();
    await onboarding.expectDialogVisible();

    await onboarding.selectCreateNewOrganization();
    await onboarding.submit();
    await expect(page.getByText(/organization name.*required/i)).toBeVisible({ timeout: 5_000 });
  });

  test("contractor must fill company before submitting", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.loginAsOnboardingContractor();
    await onboarding.expectDialogVisible();

    await onboarding.selectOrganization("Supply Yard");
    await onboarding.submit();
    await expect(page.getByText(/company.*required/i)).toBeVisible({ timeout: 5_000 });
  });
});
