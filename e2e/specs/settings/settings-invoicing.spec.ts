import { expect, test } from "@playwright/test";
import { LoginPage } from "@pages/login.page";

test.describe("Settings invoicing", () => {
  test("auto-invoice switch is visible and toggles", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    await page.goto("/settings");
    await expect(page.getByTestId("settings-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Invoicing" })).toBeVisible();

    const sw = page.getByTestId("settings-auto-invoice-switch");
    await expect(sw).toBeVisible();
    await expect(sw).toBeEnabled({ timeout: 45_000 });

    const before = await sw.getAttribute("data-state");
    const wantChecked = before !== "checked";

    const putPromise = page.waitForResponse(
      (r) => r.url().includes("finance/settings/xero") && r.request().method() === "PUT",
      { timeout: 30_000 },
    );
    await sw.click();
    const resp = await putPromise;
    if (!resp.ok()) {
      throw new Error(`PUT finance/settings/xero -> ${resp.status()} ${await resp.text()}`);
    }

    await expect(sw).toHaveAttribute("data-state", wantChecked ? "checked" : "unchecked", {
      timeout: 15_000,
    });
  });
});
