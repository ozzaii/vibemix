/* Phase 31 Plan 02 — Base layer (priority 50, never canceled).
 *
 * The Base layer is the always-on heartbeat — idle breathing + sway loop.
 * It is the FOUNDATION of the additive state machine: the other three
 * channels (emotion, anticipation, reaction) layer on top.
 *
 * Contract (load-bearing):
 *   - Priority 50 (lowest in the 4-layer stack).
 *   - `cancel()` is a NO-OP. Even the priority-999 sentinel
 *     (PriorityStack.cancel(_, {flush:true})) leaves base untouched —
 *     the mascot must never freeze, even mid-cancel.
 *   - Default clip = `idle_breathe`. Optionally swapped to
 *     `idle_breathe_slow` or `idle_bop_to_beat_*` by the renderer when
 *     beat-locked entry is enabled (Plan 13-04 logic).
 *
 * Purity: pure-state class. No three.js imports. The renderer wraps this
 * around the actual AnimationAction; this class merely tracks which clip
 * the base layer SHOULD be playing.
 */

import type { MascotState } from "../types.js";

/** Pool of valid base-layer clip names. Limited to the idle_* family. */
export type BaseClip =
  | "idle_breathe"
  | "idle_breathe_slow"
  | "idle_bop_to_beat_mellow"
  | "idle_bop_to_beat_energetic";

const VALID_BASE_CLIPS: readonly BaseClip[] = Object.freeze([
  "idle_breathe",
  "idle_breathe_slow",
  "idle_bop_to_beat_mellow",
  "idle_bop_to_beat_energetic",
]);

export const BASE_PRIORITY = 50;
export const DEFAULT_BASE_CLIP: BaseClip = "idle_breathe";

/**
 * BaseLayer — tracks the current base-layer clip. The actual
 * AnimationAction lives on the renderer's mixer; this class is a
 * pure-state holder so the PriorityStack consumer can query the active
 * base clip without depending on three.js.
 */
export class BaseLayer {
  private current: BaseClip;

  constructor(initial: BaseClip = DEFAULT_BASE_CLIP) {
    if (!VALID_BASE_CLIPS.includes(initial)) {
      throw new Error(
        `BaseLayer: invalid initial clip '${String(initial)}' ` +
          `(expected one of ${VALID_BASE_CLIPS.join(", ")})`,
      );
    }
    this.current = initial;
  }

  /**
   * Swap the base clip. Allowed at any time — the base layer is the only
   * channel that can change clip without a priority check (it never
   * conflicts with itself because there's only ever ONE base clip).
   */
  play(clip: BaseClip): void {
    if (!VALID_BASE_CLIPS.includes(clip)) {
      throw new Error(
        `BaseLayer.play: invalid clip '${String(clip)}' ` +
          `(expected one of ${VALID_BASE_CLIPS.join(", ")})`,
      );
    }
    this.current = clip;
  }

  /**
   * Cancel is a NO-OP for the base layer.
   *
   * Contract (Pitfall P47): the priority-999 sentinel flushes every layer
   * EXCEPT base. Base must always have an active clip — even mid-cancel,
   * the mascot keeps breathing.
   */
  cancel(): void {
    // intentionally empty — base is never canceled.
  }

  /** Current base-layer clip name. */
  currentClip(): BaseClip {
    return this.current;
  }

  /**
   * Cross-reference with the existing MascotState union: the base clip
   * is always a valid `MascotState` value (specifically in the idle pool).
   * Helper for callers that need to plug into the v2.0 state-machine.
   */
  asMascotState(): MascotState {
    return this.current;
  }
}
