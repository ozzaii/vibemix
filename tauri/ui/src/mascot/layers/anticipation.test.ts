/* Phase 47 / MASCOT-04 — AnticipationLayer vitest spec. */

import { describe, expect, it } from "vitest";

import {
  ANTICIPATION_PRIORITY,
  ANTICIPATION_TIMEOUT_MS,
  AnticipationLayer,
} from "./anticipation.js";
import { PriorityStack } from "../priority-stack.js";

describe("AnticipationLayer — constants", () => {
  it("ANTICIPATION_PRIORITY is 70 (between Emotion=60 and Reaction=80)", () => {
    expect(ANTICIPATION_PRIORITY).toBe(70);
  });

  it("ANTICIPATION_TIMEOUT_MS matches Phase 22-02 contract (2500ms)", () => {
    expect(ANTICIPATION_TIMEOUT_MS).toBe(2500);
  });
});

describe("AnticipationLayer.update", () => {
  it("initial state is null (no anticipation scheduled at boot)", () => {
    const stack = new PriorityStack();
    const layer = new AnticipationLayer(stack);
    expect(layer.currentIntent()).toBe(null);
  });

  it("update(prep_kick, t) schedules a transition on the anticipation channel", () => {
    const stack = new PriorityStack();
    const layer = new AnticipationLayer(stack);
    layer.update("prep_kick", 1_000);
    expect(layer.currentIntent()).toBe("prep_kick");
    const snap = stack.resolve();
    expect(snap.pending.anticipation.length).toBeGreaterThan(0);
    expect(snap.pending.anticipation[0]?.clip).toBe("prep_kick");
    expect(snap.pending.anticipation[0]?.timeout_ms).toBe(2500);
  });

  it("update(same intent) is a no-op (doesn't churn the mixer)", () => {
    const stack = new PriorityStack();
    const layer = new AnticipationLayer(stack);
    layer.update("prep_drop", 1_000);
    const before = layer.currentIntent();
    layer.update("prep_drop", 1_500);
    expect(layer.currentIntent()).toBe(before);
  });

  it("update(null) is a no-op (release semantics via stack timeout)", () => {
    const stack = new PriorityStack();
    const layer = new AnticipationLayer(stack);
    layer.update("prep_layer", 1_000);
    layer.update(null, 2_000);
    // Current intent unchanged — null is the silence signal, not a release call.
    expect(layer.currentIntent()).toBe("prep_layer");
  });

  it("update with invalid intent throws", () => {
    const stack = new PriorityStack();
    const layer = new AnticipationLayer(stack);
    // @ts-expect-error — runtime guard for non-typed callers
    expect(() => layer.update("invalid_intent", 1_000)).toThrow();
  });

  it("accepts all 5 Phase 47 anticipation intents", () => {
    const stack = new PriorityStack();
    const layer = new AnticipationLayer(stack);
    const intents = [
      "prep_kick",
      "prep_breakdown",
      "prep_drop",
      "prep_layer",
      "prep_mix",
    ] as const;
    for (const intent of intents) {
      layer.update(intent, 1_000);
      expect(layer.currentIntent()).toBe(intent);
    }
  });
});
