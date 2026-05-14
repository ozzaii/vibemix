/* Phase 22 Plan 02 — AdditiveLayer: anticipation overlay on the SAME mixer.
 *
 * Pitfall 19 mandate: there is ONE AnimationMixer per mascot. The
 * anticipation layer is the SECOND AnimationAction layer wired to that
 * same mixer (NOT a second mixer). Weight management drives the additive
 * blend: when no anticipation is active the action's effective weight is
 * 0 and the base layer (mood/idle/dance/talk/react) renders alone. When
 * an event is anticipated, the layer plays a prep_* clip + ramps weight
 * to 1.0 over blendMs. When the predicted event lands (or the window
 * times out) the layer fades weight back to 0 over blendMs.
 *
 * D-LOCKED: v2.0 ships the 3-layer subset (mood + anticipation +
 * speak/react). The full 4-layer additive model is deferred to v2.1.
 *
 * Anti-slop discipline (mirrors asset-loader.ts):
 *   - Unknown state name → throw (do NOT silently no-op).
 *   - Unknown clip name → throw.
 *   - Per Pitfall 19 the layer NEVER constructs an AnimationMixer of its
 *     own — the constructor consumes the renderer's mixer.
 *
 * Purity (mirrors state-machine.ts):
 *   - No setTimeout / no wall-clock reads inside the class. Time-based
 *     state transitions (e.g. "fadeOut completed") are driven by
 *     explicit `tick(now)` calls from the renderer's rAF loop.
 */

import type { AnimationAction, AnimationClip, AnimationMixer } from "three";

import type { MascotState } from "./types.js";

/**
 * Asset-loader's per-clip record. Re-exported here so tests can build the
 * map without importing the heavier asset-loader module. The runtime
 * boundary is identical to asset-loader's `LoadedClip`.
 */
export interface LoadedClip {
  /** The AnimationClip — for prep_* states this MUST already have
   *  AnimationUtils.makeClipAdditive applied (asset-loader handles this
   *  on load; tests apply it manually). */
  clip: AnimationClip;
  /** Playback rate (1.0 = native). prep_* clips always default to 1.0. */
  timeScale: number;
}

/** Options for play() — both required for explicit, no-default discipline. */
export interface PlayOpts {
  /** Crossfade-in duration in ms. */
  blendMs: number;
  /** Target effective weight at end of fade (0..1). Use 1.0 for full
   *  anticipation, lower for restrained "mid-confidence" prep. */
  weight: number;
}

/**
 * AdditiveLayer — owns the anticipation-layer AnimationAction on the
 * caller-provided AnimationMixer. Constructed once per mascot session by
 * the renderer; lives for the duration of the mixer.
 */
export class AdditiveLayer {
  private readonly mixer: AnimationMixer;
  private readonly clips: Map<MascotState, LoadedClip>;
  /** Lazily built per-state — populated on first play() of each state. */
  private readonly actions = new Map<MascotState, AnimationAction>();
  /** Currently playing prep_* state (null when nothing fired or fading
   *  out has completed). */
  private current: MascotState | null = null;
  /** Fade-out bookkeeping. `pendingMs` is the relative duration captured
   *  by fadeOut(); on the first tick(now) we convert it to an absolute
   *  deadline (`deadlineAt`). Subsequent ticks compare `now >= deadlineAt`
   *  to detect completion. Using two separate fields (instead of a single
   *  magnitude-based sentinel) keeps the logic correct for ANY clock
   *  base — performance.now() and Date.now() differ by ~13 orders of
   *  magnitude and a magnitude sentinel can't span both. */
  private fadeOutPendingMs: number | null = null;
  private fadeOutDeadlineAt: number | null = null;

  constructor(mixer: AnimationMixer, clips: Map<MascotState, LoadedClip>) {
    this.mixer = mixer;
    this.clips = clips;
  }

  /**
   * Play (or re-target) the anticipation layer onto a specific prep_*
   * clip. Builds the AnimationAction lazily on first request per state;
   * subsequent calls re-use the same action handle (matching three's
   * existingAction contract).
   *
   * Crossfade behavior: the action's effective weight ramps from its
   * current value to `opts.weight` over `opts.blendMs` ms. We use the
   * Three.js stdlib `fadeIn` mechanism — driven by `mixer.update(dt)`
   * which the renderer's rAF loop already calls.
   *
   * Throws on unknown state name (anti-slop — silent fallback would
   * mask asset-loader/manifest drift).
   */
  play(state: MascotState, opts: PlayOpts): void {
    const loaded = this.clips.get(state);
    if (!loaded) {
      throw new Error(
        `AdditiveLayer.play failed: unknown state ${String(state)} ` +
          `(not in clips map — check manifest.json + asset-loader)`,
      );
    }

    // Lazy build — keep the per-action AnimationAction allocation pinned
    // so repeated plays of the same state don't churn handles. We do NOT
    // pre-set effectiveWeight here: calling setEffectiveWeight on the
    // action cancels any pending weight interpolant (see Three's
    // AnimationAction._updateWeight) which would corrupt the fadeIn
    // schedule we install below. Until play() is called the action is
    // not part of the mixer's active list, so the default weight=1
    // doesn't leak onto rendering. The pre-play test guards this via
    // `if (action !== null)` (no action built ⇒ no leak).
    let action = this.actions.get(state);
    if (!action) {
      action = this.mixer.clipAction(loaded.clip);
      action.timeScale = loaded.timeScale;
      // Scale the action's STATIC weight by opts.weight so the fadeIn
      // ramp (0 → 1 internally) yields a final effective weight that
      // honors the caller's target. action.weight is a multiplier, not
      // an interpolant — safe to set without cancelling fades.
      action.weight = opts.weight;
      this.actions.set(state, action);
    } else {
      // Re-play: update the static weight multiplier in case the caller
      // requests a different target this round.
      action.weight = opts.weight;
    }

    // Cancel any in-flight fadeOut on the layer — a new play overrides.
    this.fadeOutPendingMs = null;
    this.fadeOutDeadlineAt = null;

    // Start the clip + ramp weight via the Three.js stdlib timeline.
    // reset() rewinds + clears the fade scheduling, play() activates the
    // clip on the mixer, fadeIn() schedules the weight interpolant from
    // 0 → 1 over the blend window. action.weight (the static multiplier
    // set above) scales the interpolant — final effective weight peaks
    // at opts.weight.
    action.reset().play();
    const blendSec = Math.max(0.001, opts.blendMs / 1000);
    action.fadeIn(blendSec);

    this.current = state;
  }

  /**
   * Fade the anticipation layer back to 0 over `blendMs` ms. The mixer's
   * fadeOut handles the weight ramp; we track the completion timestamp so
   * `tick(now)` can clear `current` once the fade has actually decayed.
   *
   * No-op if no clip is currently playing (callers shouldn't have to
   * track layer state themselves).
   */
  fadeOut(blendMs: number): void {
    if (this.current === null) {
      return;
    }
    const action = this.actions.get(this.current);
    if (!action) {
      // Defensive — `current` is only set when we have an action.
      this.current = null;
      return;
    }
    const blendSec = Math.max(0.001, blendMs / 1000);
    action.fadeOut(blendSec);
    // Store the relative duration; the next tick(now) converts it into
    // an absolute deadline in the renderer's clock space. We don't read
    // wall-clock ourselves (purity discipline mirroring state-machine.ts
    // — `now` is always passed in).
    this.fadeOutPendingMs = blendMs;
    this.fadeOutDeadlineAt = null;
  }

  /**
   * Renderer tick. Pass the same wall-clock-ish `now` (ms) the renderer
   * uses elsewhere — the layer uses it ONLY to detect fadeOut completion.
   *
   * On the first tick after `fadeOut(blendMs)` we convert the relative
   * blendMs into an absolute deadline. On subsequent ticks we check
   * whether `now` has crossed that deadline; if so, we clear `current`
   * + reset the action's weight to 0 so the layer is truly silent.
   */
  tick(now: number): void {
    // First tick after fadeOut(): convert the relative blendMs into an
    // absolute deadline in the caller's clock space.
    if (this.fadeOutPendingMs !== null) {
      this.fadeOutDeadlineAt = now + this.fadeOutPendingMs;
      this.fadeOutPendingMs = null;
      return;
    }
    if (this.fadeOutDeadlineAt === null) return;
    if (now >= this.fadeOutDeadlineAt) {
      // Fade complete — silence the layer fully + clear state.
      if (this.current !== null) {
        const action = this.actions.get(this.current);
        if (action) {
          action.setEffectiveWeight(0);
          action.stop();
        }
        this.current = null;
      }
      this.fadeOutDeadlineAt = null;
    }
  }

  /**
   * Currently playing anticipation state, or null if the layer is silent.
   * Used by the state-machine to know whether an anticipation is in
   * flight (Wave 2 fire-path consults this before firing a new prep_*).
   */
  currentState(): MascotState | null {
    return this.current;
  }
}
