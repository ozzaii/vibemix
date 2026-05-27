// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-03 — Screen-reader polite announcement on
//                    `ipc.learn.controller_detected` arrival. Shape:
//                    `<aria-live="polite">${display_name} connected.</aria-live>`
//                    so VoiceOver / NVDA read the controller name without
//                    interrupting the user's current focus.
//
// Phase 91 Plan 02 — RED-state. Stub is `it.todo` because the LearnWindow
// surface that owns the aria-live region lands in Plan 05; the wiring from
// the ipc envelope into a DOM mutation is also a Plan 05 concern.

import { describe, it } from "vitest";

describe("test_sr_announcement.spec.ts (RENDER-03)", () => {
  it.todo(
    "aria-live polite region receives `<display_name> connected.` on controller_detected (plan 05)",
    // TODO: plan 05 executor — when LearnWindow lands, write the test as:
    //   1. Mount LearnWindow into jsdom
    //   2. Dispatch a fake `ipc.learn.controller_detected` envelope
    //      with `display_name: "Pioneer DDJ-FLX4"`
    //   3. Assert the document's `[aria-live="polite"]` element's
    //      textContent === "Pioneer DDJ-FLX4 connected."
    //   4. Flip `it.todo` → `it`, fill in the body
    // Sibling test_aria_labels_present already pins per-control labels;
    // this test pins the WINDOW-level announcement.
  );
});
