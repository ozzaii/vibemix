// SPDX-License-Identifier: Apache-2.0
// Phase 50 / E2E — Live-session visual baseline (Tier-1 surface only)
//
// Tier-2 surfaces deferred per CONTEXT.md scope guardrails.

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

test('live session — Tier-1 surface with mock mascot state', async ({ page }) => {
  await page.goto(`${TAURI_DEV_URL}/live-session?fixture=mock`);
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveScreenshot('live-session-tier1.png');
});
