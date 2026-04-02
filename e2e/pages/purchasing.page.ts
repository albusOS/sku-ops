import { type Page } from "@playwright/test";
import { SidebarNav } from "./sidebar.component";
import { takeFullPageScreenshot } from "@support/screenshot";

export class PurchasingPage {
  readonly sidebar: SidebarNav;

  constructor(private readonly page: Page) {
    this.sidebar = new SidebarNav(page);
  }

  async gotoPurchaseOrders(): Promise<void> {
    await this.sidebar.navigateTo("purchasing");
  }

  async gotoProducts(): Promise<void> {
    await this.sidebar.navigateTo("products");
  }

  async screenshot(name: string): Promise<void> {
    await takeFullPageScreenshot(this.page, name);
  }
}
