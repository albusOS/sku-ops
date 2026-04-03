import { expect, test } from "@playwright/test";
import { JobsApi } from "@api/jobs.api";
import { LoginPage } from "@pages/login.page";
import { SidebarNav } from "@pages/sidebar.component";
import { getAdminToken } from "@support/api-client";

test.describe("Jobs CRUD", () => {
  test("API list, get by code, update", async ({ request }) => {
    const token = await getAdminToken(request);
    const jobs = new JobsApi(request, token);
    const list = (await jobs.listJobs()) as Array<{ code: string; id: string }>;
    expect(list.length).toBeGreaterThan(0);
    const first = list.find((j) => j.code === "RR-2026-001") ?? list[0];
    const one = (await jobs.getJob(first.id)) as { id: string; code: string };
    expect(one.id).toBe(first.id);

    const suffix = Date.now().toString(36);
    const updated = (await jobs.updateJob(first.id, { name: `E2E Job ${suffix}` })) as {
      name: string;
    };
    expect(updated.name).toContain("E2E Job");
  });

  test("UI create job and open detail panel", async ({ page }) => {
    await new LoginPage(page).loginAsAdmin();
    const sidebar = new SidebarNav(page);
    await sidebar.navigateTo("jobs");
    await expect(page.getByTestId("jobs-page")).toBeVisible();

    const code = `E2E-${Date.now().toString(36)}`;
    await page.getByTestId("create-job-btn").click();
    await page.getByPlaceholder("e.g. JOB-2026-001").fill(code);
    await page.getByPlaceholder("Optional descriptive name").fill("Playwright job");
    await page.getByRole("button", { name: /^Create Job$/i }).click();

    // Create success opens the detail panel and closes the dialog; do not click the row
    // (sheet overlay intercepts pointer events).
    await expect(page.getByTestId("job-detail-panel")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Edit" })).toBeVisible();
    await expect(page.locator("tbody tr").filter({ hasText: code }).first()).toBeVisible();
  });
});
