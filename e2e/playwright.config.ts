import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  globalSetup: "./support/global-setup.ts",
  testDir: "./specs",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "on",
    video: "retain-on-failure",
    actionTimeout: 60_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "cd .. && pixi run backend",
      port: 8000,
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "cd .. && pixi run frontend",
      port: 3000,
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
