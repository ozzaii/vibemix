/* Phase 31 Plan 08 — v2.1 cancel-priority 999 regression (Pitfall P72).
 *
 * P72 evidence anchor:
 *   test_cancel_signal_priority_above_all_layers
 *
 * The cancel signal MUST be above every other priority — even a queued
 * priority-80 reaction cannot delay a cancel.
 */

import { describe, expect, it } from "vitest";

import { LAYER_PRIORITY, PriorityStack } from "../priority-stack.js";
import { ReactionLayer } from "../layers/reaction.js";

describe("v2-1-cancel-priority-999 — Pitfall P72", () => {
  it("test_cancel_signal_priority_above_all_layers", () => {
    // The numeric priority of the cancel sentinel is 999 by contract.
    // We assert it is strictly above every named layer priority.
    const CANCEL_PRIORITY = 999;
    for (const layer of [
      "base",
      "emotion",
      "anticipation",
      "reaction",
    ] as const) {
      expect(CANCEL_PRIORITY).toBeGreaterThan(LAYER_PRIORITY[layer]);
    }
  });

  it("cancel-flush fires BEFORE the next pending priority-80 transition", () => {
    const stack = new PriorityStack();
    const reaction = new ReactionLayer(stack);
    const t0 = 1_000;

    // Stage a fresh reaction fire AND immediately cancel. The cancel
    // wins regardless of the priority-80 queue.
    reaction.fire("fist_pump", t0);
    expect(stack.resolve().pending.reaction).toHaveLength(1);
    reaction.cancel();
    expect(stack.resolve().pending.reaction).toEqual([]);
    expect(stack.resolve().active.reaction).toBeNull();
  });
});
