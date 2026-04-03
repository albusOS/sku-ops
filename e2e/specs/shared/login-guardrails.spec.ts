/**
 * Goal: basic abuse / mistake resistance on the login form (empty submit, bad credentials).
 */
import { expect, test } from "@playwright/test";

test.describe("Login guardrails", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
  });

  test("empty submit shows validation feedback (no session)", async ({ page }) => {
    await page.getByTestId("login-submit-btn").click();
    await expect(page.getByText("Please fill in all fields")).toBeVisible();
    await expect(page.getByTestId("app-layout")).not.toBeVisible();
  });

  test("wrong password does not reveal session or layout", async ({ page }) => {
    await page.getByTestId("login-email-input").fill("dev@supply-yard.local");
    await page.getByTestId("login-password-input").fill("not-the-real-password-12345");
    await page.getByTestId("login-submit-btn").click();
    await expect(page.getByText(/login failed/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("app-layout")).not.toBeVisible();
  });
});
