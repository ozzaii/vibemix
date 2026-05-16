/* Phase 31 Plan 05 — v2.0 test port-verbatim suite.
 *
 * P47 evidence anchor: `test_anticipation_priority_70_preserved` —
 * direct integer assertion on the anticipation-layer priority value.
 * This is the load-bearing v2.0 invariant: the full 4-layer rewrite
 * MUST NOT alter priority 70 for the anticipation class.
 */

import { describe, expect, it } from "vitest";

import { LAYER_PRIORITY } from "../priority-stack.js";
import { STATE_PRIORITY } from "../types.js";

describe("v2-anticipation-priority-70 — P47 evidence anchor", () => {
  // P47 verbatim test name — MUST appear in this file for the
  // grep_v2_test_names.sh gate to pass.
  it("test_anticipation_priority_70_preserved", () => {
    // v2.0 priority-70 lives in BOTH the legacy STATE_PRIORITY map AND
    // the new PriorityStack LAYER_PRIORITY constant. They MUST agree.
    expect(STATE_PRIORITY.anticipation).toBe(70);
    expect(LAYER_PRIORITY.anticipation).toBe(70);
  });

  it("anticipation priority is strictly between react (60) and reaction (80)", () => {
    // Sanity: the new reaction layer takes priority 80, the old react
    // CLASS at priority 60 is untouched. Anticipation sits between.
    expect(LAYER_PRIORITY.anticipation).toBeGreaterThan(STATE_PRIORITY.react);
    expect(LAYER_PRIORITY.anticipation).toBeLessThan(LAYER_PRIORITY.reaction);
  });
});
