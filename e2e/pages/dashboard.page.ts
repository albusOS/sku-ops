import { type Page } from "@playwright/test";
import { SidebarNav } from "./sidebar.component";
import { takeFullPageScreenshot } from "@support/screenshot";

export class DashboardPage {
  readonly sidebar: SidebarNav;

  constructor(private readonly page: Page) {
    this.sidebar = new SidebarNav(page);
  }

  async goto(): Promise<void> {
    await this.sidebar.navigateTo("dashboard");
  }

  async screenshot(name: string): Promise<void> {
    await takeFullPageScreenshot(this.page, name);
  }
}
