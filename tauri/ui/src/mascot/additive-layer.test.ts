/* Phase 22 Plan 02 — additive-layer.ts vitest spec.
 *
 * The AdditiveLayer composes the anticipation prep_* clips on the SAME
 * AnimationMixer as the base-layer mood/dance/talk/react actions. Per
 * PITFALLS.md Pitfall 19 (single-mixer mandate) the constructor does NOT
 * own its own mixer — it takes the renderer's existing mixer and lazily
 * builds AnimationAction layers from it.
 *
 * Tests are framework-pure: we use a real three.js AnimationMixer +
 * AnimationClip (no GLB load) so the assertions exercise the actual
 * blend-mode + weight ramp behavior without needing a renderer + WebGL
 * surface. The clip blendMode is set by AnimationUtils.makeClipAdditive
 * on the LOADER side (asset-loader.ts); these tests construct the clips
 * with makeClipAdditive applied so the layer sees them in the same
 * shape the loader will deliver.
 *
 * Determinism: AnimationMixer.update(dt) drives the weight ramp; we call
 * it with explicit dt values instead of wall-clock so timing is fully
 * deterministic.
 */

import { describe, expect, it } from "vitest";

import {
  AdditiveAnimationBlendMode,
  AnimationClip,
  AnimationMixer,
  AnimationUtils,
  NumberKeyframeTrack,
  Object3D,
} from "three";

import { AdditiveLayer, type LoadedClip } from "./additive-layer.js";
import type { MascotState } from "./types.js";

/**
 * Build a minimal AnimationClip with a single NumberKeyframeTrack so the
 * mixer has something to schedule. Track targets `.scale` on a dummy
 * object — we never look at the rendered output, only at the action's
 * effective weight.
 */
function makeClip(name: string): AnimationClip {
  const track = new NumberKeyframeTrack(".scale[x]", [0, 1], [1, 1.001]);
  return new AnimationClip(name, 1.0, [track]);
}

/**
 * Build the LoadedClip map the AdditiveLayer constructor consumes. Each
 * clip has makeClipAdditive applied (mirroring what asset-loader does at
 * load time), so the layer can verify blendMode without re-running the
 * conversion itself.
 */
function buildClipsMap(): Map<MascotState, LoadedClip> {
  const states: MascotState[] = [
    "prep_lean_in_neutral",
    "prep_lean_in_hyped",
    "prep_head_turn_left",
    "prep_head_turn_right",
    "prep_settle",
  ];
  const map = new Map<MascotState, LoadedClip>();
  for (const state of states) {
    const clip = makeClip(state);
    AnimationUtils.makeClipAdditive(clip);
    map.set(state, { clip, timeScale: 1.0 });
  }
  return map;
}

function buildMixer(): AnimationMixer {
  return new AnimationMixer(new Object3D());
}

describe("AdditiveLayer — construction + initial state", () => {
  it("starts with currentState() === null and no action playing", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);
    expect(layer.currentState()).toBeNull();
  });

  it("shares the caller's mixer (Pitfall 19 — single-mixer)", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);
    // The contract is the layer NEVER constructs an AnimationMixer of
    // its own. Probing via the public surface: ask the layer to play a
    // clip and verify the action it returns is bound to the SAME mixer
    // (mixer.existingAction returns the same action handle for the same
    // clip on the same root).
    layer.play("prep_lean_in_neutral", { blendMs: 100, weight: 1.0 });
    const directlyFromMixer = mixer.existingAction(
      clips.get("prep_lean_in_neutral")!.clip,
    );
    expect(directlyFromMixer).not.toBeNull();
  });
});

describe("AdditiveLayer.play — weight ramp", () => {
  it("crossfade reaches target weight 1.0 within blendMs", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);

    layer.play("prep_lean_in_hyped", { blendMs: 80, weight: 1.0 });

    // Tick the mixer past blendMs (in seconds).
    // 80ms = 0.08s — overshoot to 0.1s to guarantee fade is done.
    mixer.update(0.1);

    const action = mixer.existingAction(
      clips.get("prep_lean_in_hyped")!.clip,
    );
    expect(action).not.toBeNull();
    expect(action!.getEffectiveWeight()).toBeCloseTo(1.0, 2);
    expect(layer.currentState()).toBe("prep_lean_in_hyped");
  });

  it("verifies AnimationUtils.makeClipAdditive was applied (blendMode === AdditiveAnimationBlendMode)", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);
    layer.play("prep_head_turn_left", { blendMs: 100, weight: 1.0 });
    const clip = clips.get("prep_head_turn_left")!.clip;
    // Pitfall 19 / D-LOCKED: prep_* clips MUST be additive. The
    // asset-loader runs makeClipAdditive at load; the layer assumes
    // this and trusts the loader. The test fixture mirrors the same
    // sequence so we can assert post-condition.
    expect(clip.blendMode).toBe(AdditiveAnimationBlendMode);
  });

  it("throws on unknown state (anti-slop discipline matches asset-loader)", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);
    expect(() =>
      // @ts-expect-error — intentionally passing an invalid state to verify
      // the runtime guard fires.
      layer.play("not_a_real_prep_state", { blendMs: 80, weight: 1.0 }),
    ).toThrow(/unknown.*not_a_real_prep_state/i);
  });
});

describe("AdditiveLayer.fadeOut — clears state after blend", () => {
  it("fadeOut drives effectiveWeight to 0 within blendMs and currentState() returns null after tick", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);

    // Play to full weight first.
    layer.play("prep_lean_in_neutral", { blendMs: 50, weight: 1.0 });
    mixer.update(0.06);

    const action = mixer.existingAction(
      clips.get("prep_lean_in_neutral")!.clip,
    );
    expect(action!.getEffectiveWeight()).toBeCloseTo(1.0, 2);

    // Fade out over 200ms.
    layer.fadeOut(200);
    // Drive the mixer + the layer's explicit tick() past the fade window.
    const t0 = 1_000_000;
    layer.tick(t0); // start of fade
    mixer.update(0.25); // 250ms in mixer
    layer.tick(t0 + 250); // tell the layer fade is done

    expect(action!.getEffectiveWeight()).toBeCloseTo(0, 2);
    expect(layer.currentState()).toBeNull();
  });

  it("fadeOut with no current state is a no-op (does not throw)", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);
    expect(() => layer.fadeOut(100)).not.toThrow();
    expect(layer.currentState()).toBeNull();
  });
});

describe("AdditiveLayer — weight initial value (Pitfall 19: weight-managed, not silenced)", () => {
  it("before play(), the action's effective weight is 0 (no leak onto base layer)", () => {
    const mixer = buildMixer();
    const clips = buildClipsMap();
    const layer = new AdditiveLayer(mixer, clips);
    // No play() called yet — the layer should NOT have built any action,
    // OR if it has, the action's effective weight must be 0.
    const clip = clips.get("prep_lean_in_neutral")!.clip;
    const action = mixer.existingAction(clip);
    if (action !== null) {
      expect(action.getEffectiveWeight()).toBe(0);
    }
    expect(layer.currentState()).toBeNull();
  });
});
