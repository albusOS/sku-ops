import { type Page } from "@playwright/test";

export class SidebarNav {
  constructor(private readonly page: Page) {}

  async navigateTo(navTestId: string): Promise<void> {
    const sidebar = this.page.getByTestId("sidebar");
    const collapsed = await sidebar.evaluate((el) => el.getBoundingClientRect().width < 100);
    if (collapsed) {
      await this.page.getByTestId("sidebar-toggle").click();
      await this.page.waitForTimeout(300);
    }
    await this.page.getByTestId(`nav-${navTestId}`).click();
    await this.page.waitForLoadState("networkidle");
  }
}
