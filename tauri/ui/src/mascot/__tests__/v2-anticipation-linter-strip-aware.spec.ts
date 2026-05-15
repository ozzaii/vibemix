/* Phase 31 Plan 05 — v2.0 test port-verbatim suite.
 *
 * P47 evidence anchor: `test_total_strip_crossfades_to_settle_then_ack_only`
 * — v2.0 linter-strip path. When the citation linter strips ALL content
 * from a Gemini reply, the mascot should crossfade to settle and then
 * play an ack-only clip on the next valid input — NOT freeze in
 * lean-in.
 *
 * In v2.1 this is modeled as:
 *   1. anticipation layer is active (mascot leans in for incoming speech).
 *   2. Linter total-strip event fires → equivalent to a cancel signal.
 *   3. Reaction layer fires an ack intent (e.g. `nod`) AFTER cancel.
 *   4. Stack settles to base + reaction (ack-only).
 */

import { describe, expect, it } from "vitest";

import { PriorityStack } from "../priority-stack.js";
import { ReactionLayer } from "../layers/reaction.js";

describe("v2-anticipation-linter-strip-aware — P47 evidence anchor", () => {
  // P47 verbatim test name — MUST appear in this file for the
  // grep_v2_test_names.sh gate to pass.
  it("test_total_strip_crossfades_to_settle_then_ack_only", () => {
    const stack = new PriorityStack();
    const reaction = new ReactionLayer(stack);
    const t_lean_in = 1_000;
    const t_total_strip = 1_200; // 200ms later — linter ran, total strip.
    const t_ack = 1_300; // 100ms after cancel — ack arrives.

    // (1) Anticipation lean-in.
    stack.play("anticipation", {
      clip: "prep_lean_in_neutral",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t_lean_in,
      timeout_ms: 2500,
    });
    stack.activate("anticipation", "prep_lean_in_neutral", t_lean_in);

    // (2) Total-strip event. Equivalent to a cancel — every non-base
    // layer flushes. The mascot must NOT wedge in lean-in.
    reaction.cancel();
    let snap = stack.resolve();
    expect(snap.active.anticipation).toBeNull();
    expect(snap.active.reaction).toBeNull();

    // (3) Ack-only fire — the mascot follows up with a nod (or wave).
    // No anticipation re-prep — the original reply was totally stripped
    // so there's nothing to anticipate.
    reaction.fire("nod", t_ack);
    snap = stack.resolve();
    expect(snap.pending.reaction).toHaveLength(1);
    expect(snap.pending.reaction[0]?.clip).toBe("react_nod");
    // Anticipation channel stays settled — we do NOT re-fire lean-in
    // after a total strip.
    expect(snap.pending.anticipation).toEqual([]);
    expect(snap.active.anticipation).toBeNull();
  });

  it("ack-only path leaves base layer untouched (priority 50 invariant)", () => {
    const stack = new PriorityStack();
    const reaction = new ReactionLayer(stack);
    const t0 = 1_000;
    // Stage base to assert it survives the cancel.
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: t0,
    });
    // Lean in + strip + ack.
    stack.play("anticipation", {
      clip: "prep_lean_in_neutral",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
      timeout_ms: 2500,
    });
    stack.activate("anticipation", "prep_lean_in_neutral", t0);
    reaction.cancel();
    reaction.fire("nod", t0 + 100);

    const snap = stack.resolve();
    // Base survived the cancel sentinel.
    expect(snap.pending.base).toHaveLength(1);
    expect(snap.pending.base[0]?.clip).toBe("idle_breathe");
  });
});
