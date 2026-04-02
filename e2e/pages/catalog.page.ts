import { type Locator, type Page } from "@playwright/test";
import { SidebarNav } from "./sidebar.component";
import { takeFullPageScreenshot } from "@support/screenshot";

export class CatalogPage {
  readonly page: Page;
  readonly sidebar: SidebarNav;
  readonly productsRoot: Locator;
  readonly addProductBtn: Locator;
  readonly productDialog: Locator;
  readonly nameInput: Locator;
  readonly priceInput: Locator;
  readonly departmentSelect: Locator;
  readonly moreOptionsBtn: Locator;
  readonly barcodeInput: Locator;
  readonly costInput: Locator;
  readonly saveBtn: Locator;
  readonly cancelBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.sidebar = new SidebarNav(page);
    this.productsRoot = page.getByTestId("products-page");
    this.addProductBtn = page.getByTestId("add-product-btn");
    this.productDialog = page.getByTestId("product-dialog");
    this.nameInput = page.getByTestId("pf-name");
    this.priceInput = page.getByTestId("pf-price");
    this.departmentSelect = page.getByTestId("pf-department");
    this.moreOptionsBtn = page.locator("button:has-text('More options')");
    this.barcodeInput = page.getByTestId("pf-barcode");
    this.costInput = page.getByTestId("pf-cost");
    this.saveBtn = page.getByTestId("product-save-btn");
    this.cancelBtn = page.getByTestId("product-cancel-btn");
  }

  async goto(): Promise<void> {
    await this.sidebar.navigateTo("products");
  }

  /** Products page defaults to card view; table view exposes column headers under `th`. */
  async switchToTableView(): Promise<void> {
    await this.page.locator('button[title="Table view"]').click();
    await this.page.waitForLoadState("networkidle");
  }

  async openAddProductDialog(): Promise<void> {
    await this.addProductBtn.click();
  }

  async expandMoreOptions(): Promise<void> {
    await this.moreOptionsBtn.click();
    await this.page.waitForTimeout(300);
  }

  async clickFirstProductRow(): Promise<void> {
    await this.page.locator("tbody tr").first().click();
    await this.page.waitForTimeout(500);
  }

  async screenshot(name: string): Promise<void> {
    await takeFullPageScreenshot(this.page, name);
  }
}
