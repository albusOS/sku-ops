/**
 * Sign-up UI on the login page (no full Supabase sign-up flow unless email is confirmed).
 */
import { expect, test } from "@playwright/test";
import { SignupPage, assertSignupLinkVisible } from "../../pages/signup.page";

test.describe("Signup UI", () => {
  test.beforeEach(async ({ page }) => {
    const signup = new SignupPage(page);
    await signup.goto();
  });

  test("signup link visible on login page", async ({ page }) => {
    await assertSignupLinkVisible(page);
  });

  test("signup form shows name field (contractor - no gate)", async ({ page }) => {
    const signup = new SignupPage(page);
    await signup.selectRoleContractor();
    await signup.toggleToSignup();
    await expect(page.getByTestId("signup-name-input")).toBeVisible();
  });

  test("admin signup shows gate overlay with code field", async ({ page }) => {
    const signup = new SignupPage(page);
    await signup.selectRoleAdmin();
    await signup.toggleToSignup();
    await expect(page.getByTestId("signup-admin-gate-overlay")).toBeVisible();
    await expect(page.getByTestId("signup-admin-code-input")).toBeVisible();
  });

  test("contractor signup shows no code field", async ({ page }) => {
    const signup = new SignupPage(page);
    await signup.selectRoleContractor();
    await signup.toggleToSignup();
    await expect(page.getByTestId("signup-admin-code-input")).not.toBeVisible();
  });

  test("empty signup submit shows validation", async ({ page }) => {
    const signup = new SignupPage(page);
    await signup.selectRoleContractor();
    await signup.toggleToSignup();
    await signup.submitSignup();
    await expect(page.getByText("Please fill in all fields")).toBeVisible();
  });

  test("wrong admin code shows error", async ({ page }) => {
    const signup = new SignupPage(page);
    await signup.selectRoleAdmin();
    await signup.toggleToSignup();
    await signup.enterAdminCode("definitely-wrong-code-xyz");
    await signup.confirmAdminSignupGate();
    await expect(page.getByText(/invalid admin sign-up code/i)).toBeVisible({ timeout: 15_000 });
  });
});
