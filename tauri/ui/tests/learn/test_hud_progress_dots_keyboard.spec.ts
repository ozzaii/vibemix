// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-02 / A11Y — HUD progress-dots keyboard navigation.
//
// Phase 92 Plan 02 — RED-state. The LearnLessonLoaded envelope's
// `progress_dots[]` array (one entry per lesson in the active course)
// becomes the HUD strip. Each dot has `status: "pending" | "current" |
// "completed"`. Keyboard contract per UI-SPEC §Accessibility line 329:
//
//   * Tab moves focus across dots in DOM order.
//   * Enter on a COMPLETED dot → emit `ipc.learn.start_lesson { lesson_id, level: "replay" }`.
//   * Enter on the CURRENT dot → no-op (already there).
//   * Enter on a PENDING dot → show tooltip "prerequisite lessons not yet complete."
//
// Plan 92-05 lands the HUD component; this spec is `it.todo` until then.

import { describe, it } from "vitest";

describe("test_hud_progress_dots_keyboard.spec.ts (LESSON-02 a11y)", () => {
  it.todo(
    "Enter on completed dot emits start_lesson { level: 'replay' } (Plan 92-05)",
    // TODO: Plan 92-05 executor — when HUD progress-dots component lands:
    //   1. Mount LearnWindow + dispatch a fake `ipc.learn.lesson_loaded`
    //      with progress_dots = [
    //        { lesson_id: "L0.00-press-play", status: "completed" },
    //        { lesson_id: "L0.01-cue", status: "current" },
    //        { lesson_id: "L0.02-mix", status: "pending" },
    //      ]
    //   2. Tab to the first dot (Plan 92-05 confirms canonical selector
    //      — expected: `[data-progress-dot][data-status="completed"]`)
    //   3. Spy on emitIpc; dispatch Enter; assert call with
    //      ("ipc.learn.start_lesson", { lesson_id: "L0.00-press-play",
    //                                    level: "replay" })
    //   4. Tab once more (current dot); dispatch Enter; assert spy NOT
    //      called.
    //   5. Tab once more (pending dot); dispatch Enter; assert spy NOT
    //      called BUT the tooltip "prerequisite lessons not yet complete."
    //      renders verbatim.
  );

  it.todo(
    "Enter on current dot is a no-op (Plan 92-05)",
  );

  it.todo(
    "Enter on pending dot shows tooltip + no envelope (Plan 92-05)",
  );
});
