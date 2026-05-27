// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-03 — Tab cycles through control groups in canonical DOM
//                    order so hardware-free users can browse the controller
//                    surface via keyboard alone.
//
// Phase 91 Plan 02 — RED-state. This is morally a Playwright spec (the real
// Tab-key dispatch needs a live DOM with focusable elements), but vitest's
// glob picks up `*.spec.ts` so we stub here. When Plan 05 lands the Learn
// entrypoint AND Plan 04 lands the Tauri window, this test gets rewritten
// to playwright and moved to tests/e2e/. For Wave 0 it is skipped with a
// note pointing the next executor at the right plan.

import { describe, it } from "vitest";

describe("test_keyboard_nav_order.spec.ts (RENDER-03)", () => {
  it.skip(
    "Tab cycles through every <g data-control-id> in DOM order (plan 05 lands entrypoint)",
    () => {
      // TODO: plan 05 executor — once Learn entrypoint lands, rewrite this
      // as a real playwright spec under tests/e2e/learn/ that:
      //   1. opens the Learn window via app.invoke('open_learn_window')
      //   2. focuses the first control group with `page.keyboard.press('Tab')`
      //   3. iterates Tab presses; collects focused-element `data-control-id`
      //   4. asserts the collected order matches DOM source order
      //      (i.e. `Array.from(document.querySelectorAll('[data-control-id]'))`
      //       .map(g => g.dataset.controlId))
      //   5. flip `it.skip` → `test` (playwright API) and update imports
      // The stub stays here as a Wave-0 contract marker.
    },
  );
});
