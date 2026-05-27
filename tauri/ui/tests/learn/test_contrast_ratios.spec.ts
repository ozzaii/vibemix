// SPDX-License-Identifier: Apache-2.0
// REQ-ID: N/A — A11Y contrast — Learn window passes axe-core color-contrast
//               audit (WCAG 2.1 AA, 4.5:1 for normal text, 3:1 for large
//               text and meaningful graphics).
//
// Phase 91 Plan 02 — RED-state. axe-core needs a real DOM with computed
// CSS to evaluate luminance ratios; jsdom does not compute CSS. So this is
// a playwright spec that drives the real Tauri webview against the running
// Learn window. Wave 0 stub — Plan 05 lands the Learn entrypoint that
// allows this test to attach.

import { describe, it } from "vitest";

describe("test_contrast_ratios.spec.ts (A11Y contrast)", () => {
  it.skip(
    "axe-core color-contrast violations === 0 on Learn window (plan 05 lands entrypoint)",
    () => {
      // TODO: plan 05 executor — once Learn entrypoint lands, rewrite this
      // as a real playwright spec under tests/e2e/learn/ that:
      //   1. opens the Learn window via app.invoke('open_learn_window')
      //   2. injects axe-core into the page
      //   3. runs `await new AxeBuilder({ page }).withTags(['wcag2aa']).analyze()`
      //   4. filters results.violations to color-contrast rules
      //   5. asserts the count is 0; emits all offending nodes if not
      //   6. flip `it.skip` → `test` (playwright API), update imports
      // The Learn surface palette is silk-22 + amber by design; the FLX4
      // SVG strokes use `currentColor` so the inherited `color: var(--silk-22)`
      // gives the contrast — this gate catches any future drift to a
      // lower-contrast token (e.g. silk-13 by accident).
    },
  );
});
