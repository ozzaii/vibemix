/* Phase 31 Plan 08 — v2.1 cancel-flush queue regression (Pitfall P72).
 *
 * P72 evidence anchor:
 *   test_cancel_during_anticipation_with_pending_layers_flushes_to_settle_within_100ms
 *
 * Stage: anticipation active + emotion queued + reaction queued; fire
 * cancel. Assert: all 3 non-base layers settle to silence within 100ms.
 */

import { describe, expect, it } from "vitest";

import { PriorityStack } from "../priority-stack.js";
import { ReactionLayer } from "../layers/reaction.js";

describe("v2-1-cancel-flushes-queue — Pitfall P72", () => {
  it("test_cancel_during_anticipation_with_pending_layers_flushes_to_settle_within_100ms", () => {
    const stack = new PriorityStack();
    const reaction = new ReactionLayer(stack);
    const t0 = 1_000;

    // Stage anticipation as ACTIVE.
    stack.play("anticipation", {
      clip: "prep_lean_in_neutral",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
      timeout_ms: 2500,
    });
    stack.activate("anticipation", "prep_lean_in_neutral", t0);

    // Queue emotion + reaction in same frame.
    stack.play("emotion", {
      clip: "emotion_hyped",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    reaction.fire("fist_pump", t0);

    // BEFORE cancel: anticipation active, emotion + reaction queued.
    let snap = stack.resolve();
    expect(snap.active.anticipation?.clip).toBe("prep_lean_in_neutral");
    expect(snap.pending.emotion).toHaveLength(1);
    expect(snap.pending.reaction).toHaveLength(1);

    // Cancel fires. Cancel-priority 999 sentinel flushes everything.
    reaction.cancel();

    // AFTER cancel: every non-base channel is silent. No queue residue.
    snap = stack.resolve();
    expect(snap.active.anticipation).toBeNull();
    expect(snap.active.emotion).toBeNull();
    expect(snap.active.reaction).toBeNull();
    expect(snap.pending.anticipation).toEqual([]);
    expect(snap.pending.emotion).toEqual([]);
    expect(snap.pending.reaction).toEqual([]);
  });

  it("cancel-flush leaves base layer untouched", () => {
    const stack = new PriorityStack();
    const reaction = new ReactionLayer(stack);
    const t0 = 1_000;
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: t0,
    });
    stack.play("anticipation", {
      clip: "prep_lean_in_hyped",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
      timeout_ms: 2500,
    });
    reaction.cancel();
    const snap = stack.resolve();
    expect(snap.pending.base).toHaveLength(1);
    expect(snap.pending.base[0]?.clip).toBe("idle_breathe");
  });
});
