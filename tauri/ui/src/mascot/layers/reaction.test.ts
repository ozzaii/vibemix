/* Phase 31 Plan 04 — ReactionLayer vitest spec. */

import { describe, expect, it } from "vitest";

import {
  REACTION_PRIORITY,
  REACTION_TIMEOUT_MS,
  ReactionLayer,
} from "./reaction.js";
import { PriorityStack } from "../priority-stack.js";

describe("ReactionLayer — constants", () => {
  it("priority is locked at 80", () => {
    expect(REACTION_PRIORITY).toBe(80);
  });

  it("timeout is locked at 2500ms (v2.0 priority-70 contract)", () => {
    expect(REACTION_TIMEOUT_MS).toBe(2500);
  });
});

describe("ReactionLayer.fire — schedules on priority-80 channel", () => {
  it("fires a whitelisted intent and records it as current", () => {
    const stack = new PriorityStack();
    const layer = new ReactionLayer(stack);
    layer.fire("fist_pump", 1_000);
    const snap = stack.resolve();
    expect(snap.pending.reaction).toHaveLength(1);
    expect(snap.pending.reaction[0]?.clip).toBe("react_fist_pump");
    expect(snap.pending.reaction[0]?.timeout_ms).toBe(2500);
    expect(layer.currentIntent()).toBe("fist_pump");
  });

  it("back-to-back same-intent fires are FIFO (Pitfall P47 same-intent stack)", () => {
    const stack = new PriorityStack();
    const layer = new ReactionLayer(stack);
    layer.fire("nod", 1_000);
    // Activate to clear pending, then fire again.
    stack.activate("reaction", "react_nod", 1_000);
    layer.fire("nod", 2_000);
    const snap = stack.resolve();
    expect(snap.pending.reaction).toHaveLength(1);
    expect(snap.pending.reaction[0]?.clip).toBe("react_nod");
  });

  it("throws on unknown intent (anti-slop)", () => {
    const stack = new PriorityStack();
    const layer = new ReactionLayer(stack);
    expect(() =>
      layer.fire(
        // @ts-expect-error — invalid intent on purpose.
        "wink",
        1_000,
      ),
    ).toThrow(/unknown intent/i);
  });

  it("each whitelisted intent maps to a unique clip name", () => {
    const stack = new PriorityStack();
    const layer = new ReactionLayer(stack);
    const seen = new Set<string>();
    const intents = [
      "wave",
      "point_left",
      "point_right",
      "fist_pump",
      "nod",
      "headbang",
      "surprised",
    ] as const;
    let now = 1_000;
    for (const i of intents) {
      layer.fire(i, now);
      const snap = stack.resolve();
      const head = snap.pending.reaction[0];
      if (head) {
        seen.add(head.clip);
        stack.activate("reaction", head.clip, now);
      }
      now += 100;
    }
    expect(seen.size).toBe(intents.length);
  });
});

describe("ReactionLayer.cancel — priority-999 flush (Pitfall P72)", () => {
  it("flushes the reaction channel AND every other non-base layer", () => {
    const stack = new PriorityStack();
    const layer = new ReactionLayer(stack);
    // Stage several layers.
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: 1_000,
    });
    stack.play("emotion", {
      clip: "emotion_hyped",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: 1_000,
    });
    stack.play("anticipation", {
      clip: "prep_lean_in_hyped",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: 1_000,
    });
    layer.fire("fist_pump", 1_000);
    // Cancel via the reaction layer — priority-999 flush.
    layer.cancel();
    const snap = stack.resolve();
    expect(snap.pending.base).toHaveLength(1);
    expect(snap.pending.emotion).toEqual([]);
    expect(snap.pending.anticipation).toEqual([]);
    expect(snap.pending.reaction).toEqual([]);
    expect(layer.currentIntent()).toBeNull();
  });
});

describe("ReactionLayer.onTimeout — settles diagnostic state", () => {
  it("clears currentIntent after the caller observes a timeout", () => {
    const stack = new PriorityStack();
    const layer = new ReactionLayer(stack);
    layer.fire("headbang", 1_000);
    stack.activate("reaction", "react_headbang", 1_000);
    // Timeout fires at t + 2500.
    const settled = stack.tick(1_000 + REACTION_TIMEOUT_MS);
    expect(settled).toEqual(["reaction"]);
    layer.onTimeout();
    expect(layer.currentIntent()).toBeNull();
  });
});
