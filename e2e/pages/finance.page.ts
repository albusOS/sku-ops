import { type Page } from "@playwright/test";
import { SidebarNav } from "./sidebar.component";
import { takeFullPageScreenshot } from "@support/screenshot";

export class FinancePage {
  readonly sidebar: SidebarNav;

  constructor(private readonly page: Page) {
    this.sidebar = new SidebarNav(page);
  }

  /** Invoices and payments live under Point of Sale (`/invoices` redirects to `/pos`). */
  async gotoInvoices(): Promise<void> {
    await this.sidebar.navigateTo("point-of-sale");
  }

  async gotoPayments(): Promise<void> {
    await this.sidebar.navigateTo("point-of-sale");
  }

  async gotoDashboard(): Promise<void> {
    await this.sidebar.navigateTo("dashboard");
  }

  async screenshot(name: string): Promise<void> {
    await takeFullPageScreenshot(this.page, name);
  }
}
