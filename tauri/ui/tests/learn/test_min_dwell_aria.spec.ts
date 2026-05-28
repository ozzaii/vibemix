// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-04 / A11Y — 45 s min-dwell visual + aria contract.
//
// Phase 92 Plan 02 — RED-state. The 45 s anti-speedrun floor is invisible
// by design (no countdown timer surfaced — countdowns train rushing), but
// the disabled "i got it" button must communicate WHY it's disabled to
// motor-impaired + screen-reader users (Pitfall 5 mitigation per
// 92-RESEARCH.md §Pitfall 5).
//
// Plan 92-05 lands the LearnWindow + skip-button locked state. This spec
// pins the aria contract per UI-SPEC §Copywriting line 364:
//
//   "at least 45 seconds per lesson — that's the floor."  (verbatim tooltip)
//
// Visual lockout = opacity 0.4 + `aria-disabled="true"` +
// `data-min-dwell-locked="true"`. Silent unlock at t=45 s — no animation,
// no toast, no SR announcement.

import { describe, it } from "vitest";

describe("test_min_dwell_aria.spec.ts (LESSON-04 a11y)", () => {
  it.todo(
    "skip button at t<45s has aria-disabled='true' + data-min-dwell-locked='true' (Plan 92-05)",
    // TODO: Plan 92-05 executor — once LearnWindow + skip-button land:
    //   1. Mount LearnWindow with a loaded lesson at t=0 (just after begin).
    //   2. Query the skip-button selector (Plan 92-05 to settle the
    //      canonical selector; expected: `[data-action="skip-lesson"]`).
    //   3. Assert `aria-disabled === "true"` AND
    //      `data-min-dwell-locked === "true"`.
    //   4. Hover the button; assert the tooltip element renders
    //      "at least 45 seconds per lesson — that's the floor." verbatim.
    //   5. Advance the dwell clock to t=46 s (test-mode hook on the
    //      LessonRuntime singleton OR a synthetic CustomEvent that mirrors
    //      Plan 92-05's clock advance API).
    //   6. Assert `aria-disabled` removed AND tooltip no longer shows.
    //   7. CRITICAL: the unlock at t=45 must NOT fire an aria-live
    //      announcement — silent unlock is the pedagogy floor (Pitfall 5).
    //      Assert that the `#learn-sr-announcement` region's textContent
    //      did NOT change during the t=44 → t=46 transition.
  );

  it.todo(
    "tooltip 'at least 45 seconds per lesson — that's the floor.' present (Plan 92-05)",
  );

  it.todo(
    "silent unlock at t=45s — no aria-live announcement (Plan 92-05)",
  );
});
