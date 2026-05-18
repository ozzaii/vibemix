// SPDX-License-Identifier: Apache-2.0
// Phase 50 / E2E — Playwright base config for visual-regression snapshots
// against Tauri+Three.js production surfaces.
//
// Pixelmatch threshold maxDiffPixelRatio: 0.02 per REQ E2E-03 verbatim.
// reducedMotion: 'reduce' kills mascot animation jitter for pixel-stable baselines.
// CI-tolerant per PITFALLS § 8 — tauri-plugin-playwright==0.1.0 maturity issues
// fall back to WebView2-only Win e2e + manual Mac walk.

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './snapshots',
  fullyParallel: false, // visual regression must be sequential for snapshot stability
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  outputDir: '../../../dist/e2e-macbook-runs/playwright-output',
  snapshotDir: './__snapshots__',
  // Snapshot path template — platform tag in filename per CONTEXT.md.
  snapshotPathTemplate: './__snapshots__/{testFilePath}--{platform}/{arg}.png',
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      threshold: 0.1,
      animations: 'disabled',
    },
  },
  use: {
    viewport: { width: 1024, height: 768 },
    deviceScaleFactor: 2,
    colorScheme: 'dark',
    reducedMotion: 'reduce',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium-dark',
      use: { ...devices['Desktop Chrome'], colorScheme: 'dark' },
    },
    // webkit-dark project intentionally omitted until tauri-plugin-playwright
    // matures past 0.1.0 macOS WKWebView limitation (PITFALLS § 8 fallback).
  ],
});
