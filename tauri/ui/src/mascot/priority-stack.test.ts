/* Phase 31 Plan 01 — PriorityStack vitest spec.
 *
 * Pure-function tests (no Three.js). All time injection is explicit via
 * caller-provided `now_ms` so the suite is fully deterministic.
 *
 * Coverage:
 *   - 4-channel construction + initial resolve()
 *   - play() schedules with 100ms stagger when multiple layers fire in
 *     the same frame (Pitfall P62)
 *   - same-channel re-target replaces pending (most-recent wins)
 *   - cancel(layer) clears single channel
 *   - cancel(any, {flush:true}) = priority-999 sentinel — flushes all
 *     non-base channels (Pitfall P72)
 *   - cancelAll() leaves base untouched
 *   - pending(now) returns ready transitions in priority order
 *   - activate(layer, clip, now) promotes pending → active + records
 *     timeout deadline
 *   - tick(now) settles timed-out actives
 *   - perf: 100 simultaneous transition cycles complete inside a tight
 *     budget (proxy for the p99 < 22ms gate; real Three.js perf lives
 *     in __tests__/v2-1-four-layer-burst-perf.spec.ts)
 *   - anti-slop: unknown layer name throws
 */

import { describe, expect, it } from "vitest";

import {
  LAYER_PRIORITY,
  PriorityStack,
  STAGGER_MS,
} from "./priority-stack.js";

describe("PriorityStack — construction + initial state", () => {
  it("starts with all 4 channels empty (no active, no pending)", () => {
    const stack = new PriorityStack();
    const snap = stack.resolve();
    expect(snap.active.base).toBeNull();
    expect(snap.active.emotion).toBeNull();
    expect(snap.active.anticipation).toBeNull();
    expect(snap.active.reaction).toBeNull();
    expect(snap.pending.base).toEqual([]);
    expect(snap.pending.emotion).toEqual([]);
    expect(snap.pending.anticipation).toEqual([]);
    expect(snap.pending.reaction).toEqual([]);
  });

  it("LAYER_PRIORITY locks v2.0 anticipation = 70 (Pitfall P47)", () => {
    expect(LAYER_PRIORITY.base).toBe(50);
    expect(LAYER_PRIORITY.emotion).toBe(60);
    expect(LAYER_PRIORITY.anticipation).toBe(70);
    expect(LAYER_PRIORITY.reaction).toBe(80);
  });
});

describe("PriorityStack.play — 100ms stagger across simultaneous transitions (Pitfall P62)", () => {
  it("first play on an empty stack fires at now_ms (no stagger needed)", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("emotion", {
      clip: "neutral",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    const snap = stack.resolve();
    expect(snap.pending.emotion).toHaveLength(1);
    expect(snap.pending.emotion[0]?.fire_at_ms).toBe(t0);
  });

  it("4 simultaneous plays stagger as 0/100/200/300 in priority order", () => {
    const stack = new PriorityStack();
    const t0 = 5_000;
    // Issue in arbitrary order — stagger should sort by priority.
    stack.play("emotion", {
      clip: "neutral",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: t0,
    });
    stack.play("reaction", {
      clip: "react_yes",
      fade_in_ms: 80,
      fade_out_ms: 120,
      now_ms: t0,
    });
    stack.play("anticipation", {
      clip: "prep_lean_in_neutral",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
    });
    const snap = stack.resolve();
    // Reaction is priority 80 → slot 0 → t0.
    expect(snap.pending.reaction[0]?.fire_at_ms).toBe(t0);
    // Anticipation 70 → slot 1 → t0+100.
    expect(snap.pending.anticipation[0]?.fire_at_ms).toBe(t0 + STAGGER_MS);
    // Emotion 60 → slot 2 → t0+200.
    expect(snap.pending.emotion[0]?.fire_at_ms).toBe(t0 + 2 * STAGGER_MS);
    // Base 50 → slot 3 → t0+300.
    expect(snap.pending.base[0]?.fire_at_ms).toBe(t0 + 3 * STAGGER_MS);
  });

  it("same-layer re-target replaces previous pending (most-recent wins)", () => {
    const stack = new PriorityStack();
    const t0 = 100;
    stack.play("emotion", {
      clip: "neutral",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    stack.play("emotion", {
      clip: "hyped",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    const snap = stack.resolve();
    expect(snap.pending.emotion).toHaveLength(1);
    expect(snap.pending.emotion[0]?.clip).toBe("hyped");
  });
});

describe("PriorityStack.cancel — cancel-priority 999 flush (Pitfall P72)", () => {
  it("cancel(layer) clears only that single layer", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("emotion", {
      clip: "hyped",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    stack.play("anticipation", {
      clip: "prep_lean_in_hyped",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
    });
    stack.cancel("emotion");
    const snap = stack.resolve();
    expect(snap.pending.emotion).toEqual([]);
    expect(snap.pending.anticipation).toHaveLength(1);
  });

  it("cancel with flush=true (priority 999) flushes all non-base channels", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: t0,
    });
    stack.play("emotion", {
      clip: "hyped",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    stack.play("anticipation", {
      clip: "prep_lean_in_hyped",
      fade_in_ms: 100,
      fade_out_ms: 100,
      now_ms: t0,
    });
    stack.play("reaction", {
      clip: "react_yes",
      fade_in_ms: 80,
      fade_out_ms: 120,
      now_ms: t0,
    });
    // Priority-999 sentinel — flush.
    stack.cancel("reaction", { flush: true });
    const snap = stack.resolve();
    // Base survives.
    expect(snap.pending.base).toHaveLength(1);
    // Everyone else flushed.
    expect(snap.pending.emotion).toEqual([]);
    expect(snap.pending.anticipation).toEqual([]);
    expect(snap.pending.reaction).toEqual([]);
  });

  it("cancel('base') is a no-op (base never canceled)", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: t0,
    });
    stack.cancel("base");
    const snap = stack.resolve();
    expect(snap.pending.base).toHaveLength(1);
  });

  it("cancelAll() leaves base untouched", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("base", {
      clip: "idle_breathe",
      fade_in_ms: 300,
      fade_out_ms: 300,
      now_ms: t0,
    });
    stack.play("emotion", {
      clip: "hyped",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    stack.cancelAll();
    const snap = stack.resolve();
    expect(snap.pending.base).toHaveLength(1);
    expect(snap.pending.emotion).toEqual([]);
  });
});

describe("PriorityStack.pending — returns ready transitions in priority order", () => {
  it("returns nothing while none crossed fire_at_ms", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("emotion", {
      clip: "neutral",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    expect(stack.pending(t0 - 1)).toEqual([]);
  });

  it("returns transitions whose stagger deadline crossed", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("emotion", {
      clip: "neutral",
      fade_in_ms: 200,
      fade_out_ms: 200,
      now_ms: t0,
    });
    stack.play("reaction", {
      clip: "react_yes",
      fade_in_ms: 80,
      fade_out_ms: 120,
      now_ms: t0,
    });
    // At t0 — reaction (slot 0) is ready, emotion (slot 1) is not.
    const ready = stack.pending(t0);
    expect(ready).toHaveLength(1);
    expect(ready[0]?.layer).toBe("reaction");
    // At t0 + STAGGER_MS, emotion also ready.
    const ready2 = stack.pending(t0 + STAGGER_MS);
    expect(ready2.map((r) => r.layer)).toEqual(["reaction", "emotion"]);
  });
});

describe("PriorityStack.activate + tick — timeout settles active", () => {
  it("activate() promotes pending → active and pops queue", () => {
    const stack = new PriorityStack();
    const t0 = 1_000;
    stack.play("reaction", {
      clip: "react_yes",
      fade_in_ms: 80,
      fade_out_ms: 120,
      now_ms: t0,
      timeout_ms: 2500,
    });
    stack.activate("reaction", "react_yes", t0);
    const snap = stack.resolve();
    expect(snap.pending.reaction).toEqual([]);
    expect(snap.active.reaction?.clip).toBe("react_yes");
    expect(snap.active.reaction?.timeout_at_ms).toBe(t0 + 2500);
  });

  it("tick() settles active when timeout_at_ms crossed (v2.0 2.5s contract)", () => {
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
    expect(stack.tick(t0 + 2499)).toEqual([]);
    const settled = stack.tick(t0 + 2500);
    expect(settled).toEqual(["anticipation"]);
    expect(stack.resolve().active.anticipation).toBeNull();
  });
});

describe("PriorityStack — anti-slop discipline (matches AdditiveLayer)", () => {
  it("play() throws on unknown layer name", () => {
    const stack = new PriorityStack();
    expect(() =>
      stack.play(
        // @ts-expect-error — invalid layer name on purpose.
        "not_a_layer",
        { clip: "x", fade_in_ms: 0, fade_out_ms: 0, now_ms: 0 },
      ),
    ).toThrow(/unknown.*not_a_layer/i);
  });

  it("cancel() throws on unknown layer name", () => {
    const stack = new PriorityStack();
    expect(() =>
      stack.cancel(
        // @ts-expect-error — invalid layer name on purpose.
        "not_a_layer",
      ),
    ).toThrow(/unknown.*not_a_layer/i);
  });
});

describe("PriorityStack — perf proxy (100 cycles under tight budget)", () => {
  it("100 schedule+activate+settle cycles complete in < 50ms wall-clock", () => {
    const stack = new PriorityStack();
    const start = Date.now();
    for (let i = 0; i < 100; i++) {
      const t0 = i * 1000;
      stack.play("emotion", {
        clip: "neutral",
        fade_in_ms: 200,
        fade_out_ms: 200,
        now_ms: t0,
      });
      stack.play("anticipation", {
        clip: "prep_lean_in_neutral",
        fade_in_ms: 100,
        fade_out_ms: 100,
        now_ms: t0,
        timeout_ms: 2500,
      });
      stack.play("reaction", {
        clip: "react_yes",
        fade_in_ms: 80,
        fade_out_ms: 120,
        now_ms: t0,
        timeout_ms: 2500,
      });
      // Drain pending.
      for (const r of stack.pending(t0 + 1000)) {
        stack.activate(r.layer, r.clip.clip, t0 + 1000);
      }
      stack.tick(t0 + 5000);
    }
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(50);
  });
});
