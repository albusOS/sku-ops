import { expect, type Page } from "@playwright/test";

/**
 * Admin direct issue flow at `/pos/issue` (IssueMaterials / POS.jsx).
 */
export class PosIssuePage {
  constructor(readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/pos/issue");
    await this.page.waitForLoadState("networkidle");
    await expect(this.page.getByTestId("pos-page")).toBeVisible();
    await expect(this.page.getByRole("heading", { name: /new sale/i })).toBeVisible();
  }

  async addFirstSearchResult(query: string): Promise<void> {
    const input = this.page.getByTestId("item-search-input");
    await input.fill(query);
    await expect(this.page.getByTestId("search-dropdown")).toBeVisible({ timeout: 10_000 });
    const row = this.page.getByTestId("search-dropdown").locator("button").first();
    await expect(row).toBeVisible();
    await row.click();
    await expect(this.page.getByTestId("search-dropdown")).not.toBeVisible();
  }

  async selectFirstContractor(): Promise<void> {
    await this.page.getByTestId("select-contractor").click();
    await this.page.getByRole("option").first().click();
  }

  async fillJob(code: string): Promise<void> {
    const input = this.page.getByTestId("job-picker-input");
    await input.fill(code);
    await input.blur();
  }

  async clearJob(): Promise<void> {
    await this.page.getByTestId("job-picker-input").clear();
  }

  async fillAddress(line: string): Promise<void> {
    const input = this.page.getByTestId("address-picker-input");
    await input.fill(line);
    await input.blur();
  }

  async clearAddress(): Promise<void> {
    await this.page.getByTestId("address-picker-input").clear();
  }

  async setLineQuantity(sku: string, quantity: number): Promise<void> {
    const row = this.page.getByTestId(`item-row-${sku}`);
    await expect(row).toBeVisible();
    const input = row.locator('input[type="number"]');
    await input.fill(String(quantity));
    await input.blur();
  }

  async completeSale(): Promise<void> {
    await this.page.getByTestId("checkout-btn").click();
  }
}
