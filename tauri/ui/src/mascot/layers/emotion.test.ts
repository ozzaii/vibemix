/* Phase 31 Plan 03 — EmotionLayer vitest spec. */

import { describe, expect, it } from "vitest";

import { EMOTION_PRIORITY, EmotionLayer } from "./emotion.js";
import { PriorityStack } from "../priority-stack.js";

describe("EmotionLayer — construction", () => {
  it("defaults to neutral", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack);
    expect(layer.currentEmotion()).toBe("neutral");
  });

  it("EMOTION_PRIORITY is locked at 60", () => {
    expect(EMOTION_PRIORITY).toBe(60);
  });

  it("throws on invalid initial emotion (anti-slop)", () => {
    const stack = new PriorityStack();
    expect(
      () =>
        new EmotionLayer(
          stack,
          // @ts-expect-error — invalid emotion on purpose.
          "not_an_emotion",
        ),
    ).toThrow(/invalid initial/i);
  });
});

describe("EmotionLayer.update — change → re-fire", () => {
  it("transitioning emotion enqueues to priority-60 channel", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack);
    layer.update("hyped", 1_000);
    const snap = stack.resolve();
    expect(snap.pending.emotion).toHaveLength(1);
    expect(snap.pending.emotion[0]?.clip).toBe("emotion_hyped");
    expect(layer.currentEmotion()).toBe("hyped");
  });

  it("same emotion → no-op (no mixer churn)", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack, "focused");
    layer.update("focused", 1_000);
    const snap = stack.resolve();
    expect(snap.pending.emotion).toHaveLength(0);
  });

  it("null update is no-op (backward-compat with pre-Phase-31 ws_bus)", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack);
    layer.update(null, 1_000);
    const snap = stack.resolve();
    expect(snap.pending.emotion).toHaveLength(0);
  });

  it("multiple consecutive changes schedule on the emotion channel", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack);
    layer.update("hyped", 1_000);
    // Activate to drain queue so the next update can re-enqueue.
    stack.activate("emotion", "emotion_hyped", 1_000);
    layer.update("concerned", 2_000);
    const snap = stack.resolve();
    expect(snap.pending.emotion).toHaveLength(1);
    expect(snap.pending.emotion[0]?.clip).toBe("emotion_concerned");
  });
});

describe("EmotionLayer.update — anti-slop", () => {
  it("throws on invalid emotion value", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack);
    expect(() =>
      layer.update(
        // @ts-expect-error — invalid value on purpose.
        "rage",
        1_000,
      ),
    ).toThrow(/invalid emotion/i);
  });
});

describe("EmotionLayer — all 4 emotions reachable", () => {
  it("each MascotEmotion produces a unique clip name", () => {
    const stack = new PriorityStack();
    const layer = new EmotionLayer(stack);
    const seen = new Set<string>();
    let now = 1_000;
    for (const e of ["neutral", "focused", "hyped", "concerned"] as const) {
      layer.update(e, now);
      const snap = stack.resolve();
      // Activate + drain so each iteration starts from a clean queue.
      const pending = snap.pending.emotion[0];
      if (pending) {
        seen.add(pending.clip);
        stack.activate("emotion", pending.clip, now);
      }
      now += 1_000;
    }
    // neutral → no transition (was the initial), so we expect 3 unique clips.
    expect(seen.size).toBe(3);
  });
});
