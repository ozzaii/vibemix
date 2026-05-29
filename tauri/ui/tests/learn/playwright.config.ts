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
  outputDir: "../../dist/learn-playwright-output",
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5188",
    url: "http://127.0.0.1:5188/learn.html",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:5188",
    viewport: { width: 1280, height: 720 },
    colorScheme: "dark",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
