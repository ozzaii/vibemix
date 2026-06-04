// SPDX-License-Identifier: Apache-2.0
//
// Playwright config for the organism runtime visual receipt. jsdom never
// compiles WebGL, so the green vitest suite cannot prove the particle
// organism's GLSL builds or that the teaching-focus dissolve actually moves
// pixels. This config drives `?dev=organism-probe` in real Chromium (real
// WebGL) so browser-organism-probe.pw.ts can assert the canvas is lit and
// alive. Opt-in lane (npm run test:e2e:mascot), not part of `npm test`.

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: /browser-.*\.pw\.ts/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "../../dist/mascot-playwright-output",
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5191",
    url: "http://127.0.0.1:5191/mascot.html?dev=organism-probe",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:5191",
    colorScheme: "dark",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
