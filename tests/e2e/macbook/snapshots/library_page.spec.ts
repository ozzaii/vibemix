// SPDX-License-Identifier: Apache-2.0
// Phase 50 / E2E — Library-page visual baselines (CDJ Whisper direction)
//
// Two snapshots: empty-state + populated-state (mock fixture).
// Tier-1 surface per REQ E2E-06.

import { test, expect } from '@playwright/test';

const TAURI_DEV_URL = process.env.TAURI_DEV_URL ?? 'http://localhost:1420';

test.beforeAll(async ({ request }) => {
  try {
    const r = await request.get(`${TAURI_DEV_URL}/health`, { timeout: 2000 });
    if (!r.ok()) {
      test.skip(true, 'Tauri dev server unreachable — baselines deferred (PITFALLS § 8)');
    }
  } catch (_err) {
    test.skip(true, 'Tauri dev server unreachable — baselines deferred (PITFALLS § 8)');
  }
});

test('library page — empty state', async ({ page }) => {
  await page.goto(`${TAURI_DEV_URL}/library?fixture=empty`);
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveScreenshot('library-empty.png');
});

test('library page — populated state', async ({ page }) => {
  await page.goto(`${TAURI_DEV_URL}/library?fixture=populated`);
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveScreenshot('library-populated.png');
});
