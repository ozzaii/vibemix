// SPDX-License-Identifier: Apache-2.0

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: /browser-.*\.pw\.ts/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "../../dist/pill-playwright-output",
  webServer: {
    command: "VITE_VIBEMIX_DEMO_NEXT=1 npm run dev -- --host 127.0.0.1 --port 5190",
    url: "http://127.0.0.1:5190/pill.html",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:5190",
    colorScheme: "dark",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
