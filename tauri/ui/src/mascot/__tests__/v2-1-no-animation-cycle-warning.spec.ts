/* Phase 31 Plan 08 — v2.1 no animation-cycle warning (Pitfall P62).
 *
 * P62 evidence anchor:
 *   test_no_three_js_cycle_warning_during_burst
 *
 * Three.js logs an "Animation cycle" warning to console when the mixer
 * sees a circular animation dependency under load. Phase 31's priority-
 * stack arbitration MUST NOT introduce such cycles. We spy on
 * console.warn during a synthetic burst and assert it stays clean.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AnimationClip, AnimationMixer, NumberKeyframeTrack, Object3D } from "three";

import { PriorityStack } from "../priority-stack.js";
import { ReactionLayer } from "../layers/reaction.js";

function makeClip(name: string): AnimationClip {
  const track = new NumberKeyframeTrack(".scale[x]", [0, 1], [1, 1.001]);
  return new AnimationClip(name, 1.0, [track]);
}

describe("v2-1-no-animation-cycle-warning — Pitfall P62", () => {
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleWarnSpy.mockRestore();
  });

  it("test_no_three_js_cycle_warning_during_burst", () => {
    const root = new Object3D();
    const mixer = new AnimationMixer(root);
    const stack = new PriorityStack();
    const reaction = new ReactionLayer(stack);

    // Real mixer drive to ensure three.js gets the chance to log. The
    // priority-stack is JS state — three.js only sees the result of
    // pending(now)+activate(). We schedule + drive the mixer through
    // the 4-layer cycle and check no warnings emerge.
    const baseClip = makeClip("idle_breathe");
    const emotionClip = makeClip("emotion_hyped");
    const prepClip = makeClip("prep_lean_in_neutral");
    const reactClip = makeClip("react_fist_pump");

    for (let i = 0; i < 30; i++) {
      const t = i * 1_000;
      stack.play("base", {
        clip: "idle_breathe",
        fade_in_ms: 300,
        fade_out_ms: 300,
        now_ms: t,
      });
      stack.play("emotion", {
        clip: "emotion_hyped",
        fade_in_ms: 200,
        fade_out_ms: 200,
        now_ms: t,
      });
      stack.play("anticipation", {
        clip: "prep_lean_in_neutral",
        fade_in_ms: 100,
        fade_out_ms: 100,
        now_ms: t,
        timeout_ms: 2500,
      });
      reaction.fire("fist_pump", t);
      // Apply to mixer.
      for (const r of stack.pending(t + 500)) {
        const clip =
          r.clip.clip === "idle_breathe"
            ? baseClip
            : r.clip.clip === "emotion_hyped"
              ? emotionClip
              : r.clip.clip === "prep_lean_in_neutral"
                ? prepClip
                : reactClip;
        const action = mixer.clipAction(clip);
        action.fadeIn(r.clip.fade_in_ms / 1000).play();
        stack.activate(r.layer, r.clip.clip, t + 500);
      }
      // Drive the mixer.
      mixer.update(0.5);
    }

    // Filter for "cycle" warnings specifically — other three.js
    // warnings (e.g. about missing tracks on shared scenes) are
    // outside the contract.
    const cycleWarnings = consoleWarnSpy.mock.calls.filter((args) =>
      args.some(
        (a) => typeof a === "string" && /animation\s*cycle/i.test(a),
      ),
    );
    expect(cycleWarnings).toHaveLength(0);
  });
});
