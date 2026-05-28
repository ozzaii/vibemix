// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-04 / A11Y — "I got it" skip button reachable via keyboard.
//
// Phase 92 Plan 02 — RED-state. Plan 92-05 lands the LearnWindow with the
// "I got it" skip button (motor-impaired-safe — always available after the
// 45 s min-dwell elapses). This spec pins the keyboard reachability gate
// per UI-SPEC §Accessibility line 332.
//
// Shape contract:
//   1. Mount LearnWindow with a loaded lesson (Plan 92-05 entrypoint).
//   2. Press Tab N times (N ≤ 8 in the canonical layout).
//   3. Expect focus to land on the "i got it" button before N=8 exhausts.
//   4. Press Space; expect the page to emit `ipc.learn.complete_lesson`
//      with `payload.reason === "user_skip"`.
//   5. Assert: 45 s min-dwell guard must be PAST (the button is enabled).

import { describe, it } from "vitest";

describe("test_keyboard_skip_reachable.spec.ts (LESSON-04 a11y)", () => {
  it.todo(
    "Tab reaches 'i got it' button + Space emits complete_lesson user_skip (Plan 92-05)",
    // TODO: Plan 92-05 executor — when LearnWindow lands the skip button:
    //   1. Mount the window in JSDOM with a loaded lesson at t > 45 s
    //      (use a monkeypatched clock OR fast-forward dwell via runtime
    //      hook in test mode).
    //   2. Get the document.activeElement; press Tab repeatedly until
    //      `document.activeElement.matches('[data-action="skip-lesson"]')`
    //      (or whatever selector Plan 92-05 chooses; this test pins ONE
    //      such element MUST exist + be reachable in ≤8 Tab presses).
    //   3. Spy on `emitIpc` (via vi.mock("../../src/ipc/client.js"))
    //   4. Dispatch a `KeyboardEvent("keydown", { key: "Enter" })` OR
    //      Space; assert spy called with
    //      ("ipc.learn.complete_lesson", { reason: "user_skip" })
    //   5. Flip `it.todo` → `it`, fill in body
  );

  it.todo(
    "Before 45 s dwell, skip button is aria-disabled (Plan 92-05)",
  );
});
