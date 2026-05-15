/* Phase 31 Plan 05 — v2.0 test port-verbatim suite.
 *
 * P47 evidence anchor: `test_2_5s_timeout_crossfades_to_settle` —
 * fires an anticipation clip, advances time past 2.5s, asserts the
 * layer settles WITHOUT a manual cancel signal.
 */

import { describe, expect, it } from "vitest";

import { PriorityStack } from "../priority-stack.js";

describe("v2-anticipation-timeout-crossfade — P47 evidence anchor", () => {
  // P47 verbatim test name — MUST appear in this file for the
  // grep_v2_test_names.sh gate to pass.
  it("test_2_5s_timeout_crossfades_to_settle", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("anticipation", {
      clip: "prep_lean_in_neutral",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
      timeout_ms: 2500,
    });
    stack.activate("anticipation", "prep_lean_in_neutral", t0);

    // At t + 2499ms — still active (timeout has not elapsed).
    let settled = stack.tick(t0 + 2499);
    expect(settled).toEqual([]);
    expect(stack.resolve().active.anticipation?.clip).toBe(
      "prep_lean_in_neutral",
    );

    // At t + 2500ms — settles. No manual cancel signal needed.
    settled = stack.tick(t0 + 2500);
    expect(settled).toEqual(["anticipation"]);
    expect(stack.resolve().active.anticipation).toBeNull();
  });

  it("settle is automatic — caller does NOT need to issue cancel()", () => {
    const stack = new PriorityStack();
    const t0 = 5_000;
    stack.play("anticipation", {
      clip: "prep_settle",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
      timeout_ms: 2500,
    });
    stack.activate("anticipation", "prep_settle", t0);
    // No cancel() called. tick() across the deadline does the work.
    const settled = stack.tick(t0 + 3000);
    expect(settled).toEqual(["anticipation"]);
  });
});
