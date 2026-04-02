import { type Page } from "@playwright/test";
import { SidebarNav } from "./sidebar.component";
import { takeFullPageScreenshot } from "@support/screenshot";

export class ReportsPage {
  readonly sidebar: SidebarNav;

  constructor(private readonly page: Page) {
    this.sidebar = new SidebarNav(page);
  }

  async gotoProfitAndLossTab(): Promise<void> {
    await this.page.goto("/reports?tab=pl");
    await this.page.waitForLoadState("networkidle");
  }

  async gotoInventoryTab(): Promise<void> {
    await this.page.goto("/reports?tab=inventory");
    await this.page.waitForLoadState("networkidle");
  }

  async goToDashboardViaSidebar(): Promise<void> {
    await this.sidebar.navigateTo("dashboard");
  }

  async screenshot(name: string): Promise<void> {
    await takeFullPageScreenshot(this.page, name);
  }
}
