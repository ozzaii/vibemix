/* Phase 31 Plan 08 — v2.1 four-layer burst perf (Pitfall P62).
 *
 * P62 evidence anchor:
 *   test_p99_under_22ms_on_4_simultaneous_layers
 *
 * 60-event-per-minute synthetic burst, all 4 layers firing inside a
 * single frame window. Asserts p99 frame budget < 22ms across the
 * priority-stack arbitration path.
 *
 * The full p99 across the three.js mixer is exercised in the
 * additive-layer.test.ts surface; this spec covers the JS-side
 * arbitration cost (priority-stack + crossfade-policy + 4 layer
 * classes composed). That cost is the NEW work added by Phase 31 —
 * if it exceeds the budget the four-layer extension is non-viable.
 */

import { describe, expect, it } from "vitest";

import { PriorityStack } from "../priority-stack.js";
import { BaseLayer } from "../layers/base.js";
import { EmotionLayer } from "../layers/emotion.js";
import { ReactionLayer } from "../layers/reaction.js";

/** 60 events per minute = one event per second. We compress the
 *  workload to 100 cycles so the suite stays fast. */
const CYCLES = 100;

/**
 * Compute the p99 of a numeric array.
 *
 * Implementation note: ascending sort, then index ceil(n * 0.99) - 1.
 * For n=100 that's index 98 (the 99th value out of 100, 0-indexed).
 */
function p99(samples: number[]): number {
  const sorted = [...samples].sort((a, b) => a - b);
  const idx = Math.max(0, Math.ceil(sorted.length * 0.99) - 1);
  return sorted[idx] ?? 0;
}

describe("v2-1-four-layer-burst-perf — Pitfall P62", () => {
  it("test_p99_under_22ms_on_4_simultaneous_layers", () => {
    const stack = new PriorityStack();
    new BaseLayer(); // construct to validate boot path
    const emotion = new EmotionLayer(stack);
    const reaction = new ReactionLayer(stack);

    const samples: number[] = [];
    const emotions = ["neutral", "focused", "hyped", "concerned"] as const;
    const intents = [
      "wave",
      "point_left",
      "point_right",
      "fist_pump",
      "nod",
      "headbang",
      "surprised",
    ] as const;

    for (let i = 0; i < CYCLES; i++) {
      const t0 = i * 1_000;
      const start = performance.now();

      // 4 simultaneous transitions in the same frame.
      stack.play("base", {
        clip: "idle_breathe",
        fade_in_ms: 300,
        fade_out_ms: 300,
        now_ms: t0,
      });
      emotion.update(emotions[i % emotions.length] ?? null, t0);
      stack.play("anticipation", {
        clip: "prep_lean_in_neutral",
        fade_in_ms: 100,
        fade_out_ms: 100,
        now_ms: t0,
        timeout_ms: 2500,
      });
      reaction.fire(intents[i % intents.length] ?? "nod", t0);

      // Drain pending — simulate a renderer frame applying ready ones.
      for (const r of stack.pending(t0 + 500)) {
        stack.activate(r.layer, r.clip.clip, t0 + 500);
      }
      stack.tick(t0 + 3000);

      const elapsed = performance.now() - start;
      samples.push(elapsed);
    }

    const p99_ms = p99(samples);
    // Budget: 22ms per Pitfall P62. The JS arbitration cost should be
    // well under (mixer work happens elsewhere); we set a generous
    // pass threshold for CI variance.
    expect(p99_ms).toBeLessThan(22);
  });
});
