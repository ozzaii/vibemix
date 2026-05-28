// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-05 / WCAG — tutor-speak dock contrast contract.
//
// Phase 92 Plan 02 — RED-state. The tutor-speak dock has TWO copy
// channels with distinct contrast contracts per UI-SPEC §Accessibility
// line 334:
//
//   * The `.now` line (active tutor narration) — WCAG AAA at 24-32 px on
//     silk over void.
//   * The hint italic — WCAG AA Large (silk-65 on void at 14 px is the
//     documented exception; smaller font → relaxed contrast bar at AA
//     Large rather than AAA).
//
// Plan 92-05 lands the dock component; this spec runs axe-core against
// the rendered DOM and asserts zero contrast violations on the .now
// line. The .now line MUST hit AAA; the hint italic MUST hit AA Large.
//
// IMPORTANT: axe-core runs in a browser; this is morally a Playwright
// spec. For Wave 0 stub, we leave `it.todo` markers.

import { describe, it } from "vitest";

describe("test_contrast_p92.spec.ts (LESSON-05 WCAG)", () => {
  it.todo(
    "tutor dock .now line passes WCAG AAA at 24-32 px silk/void (Plan 92-05)",
    // TODO: Plan 92-05 executor — when tutor-speak dock lands:
    //   1. Migrate this file to a Playwright spec under
    //      tests/e2e/learn/test_contrast_p92.spec.ts (Playwright owns
    //      axe-core integration).
    //   2. Launch the Learn window with a loaded lesson; dispatch a
    //      tutor_speak envelope with text="find deck A play button".
    //   3. Run `axe-core` (or @axe-core/playwright) scoped to the dock
    //      selector.
    //   4. Filter results to `.now` line; assert no AAA contrast
    //      violations.
    //   5. Filter to hint italic; assert no AA Large violations (the
    //      relaxed bar — see UI-SPEC line 334's documented exception).
  );

  it.todo(
    "tutor dock hint italic passes WCAG AA Large (silk-65/void/14px) (Plan 92-05)",
  );

  it.todo(
    "highlight cue_color amber + warning both pass WCAG AA against SVG fill (Plan 92-05)",
  );
});
