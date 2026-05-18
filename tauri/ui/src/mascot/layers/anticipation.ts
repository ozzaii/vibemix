/* Phase 47 / MASCOT-04 — Anticipation layer (priority 70).
 *
 * Fires `prep_*` event-class-specific anticipation clips when the
 * upstream EventDispatcher signals a near-future event (BREAKDOWN_KICK_KILL,
 * PHASE entry breakdown/drop, LAYER_ARRIVAL window, TRACK_CHANGE imminent).
 *
 * Priority 70 — between Emotion (60) and Reaction (80). Fires over
 * Emotion + Base layers; yields to Reaction. 2.5s window matches the
 * Phase 22-02 anticipation contract.
 *
 * NEW LAYER: this file lands in Phase 47. The 5-clip taxonomy here is
 * distinct from the 5 legacy `prep_lean_in_*` / `prep_head_turn_*` /
 * `prep_settle` placeholders from Phase 22-02 which stay for backward-compat.
 *
 * ADDITIVE-ONLY: composes on top of the existing rig via the shared
 * PriorityStack; does not modify the v2.0 state-machine.
 */

import type { AnticipationClip } from "../types.js";
import { PHASE_47_ANTICIPATIONS } from "../types.js";
import type { PriorityStack } from "../priority-stack.js";
import { transition } from "../crossfade-policy.js";

export const ANTICIPATION_PRIORITY = 70;

/** Matches the Phase 22-02 anticipation contract value. */
export const ANTICIPATION_TIMEOUT_MS = 2500;

/** Maps each anticipation intent to the clip name (1:1 — slot stem
 *  == clip name set by retarget_to_neon_rebel.py output). */
const ANTICIPATION_CLIP_NAME: Record<AnticipationClip, string> = {
  prep_kick: "prep_kick",
  prep_breakdown: "prep_breakdown",
  prep_drop: "prep_drop",
  prep_layer: "prep_layer",
  prep_mix: "prep_mix",
};

export class AnticipationLayer {
  private current: AnticipationClip | null;
  private readonly stack: PriorityStack;

  constructor(stack: PriorityStack) {
    this.current = null;
    this.stack = stack;
  }

  /**
   * Fire a near-future anticipation cue.
   *
   * - same as current → no-op (don't churn the mixer).
   * - new intent → schedule a crossfade on the priority-70 channel.
   * - null → no-op (release semantics handled by PriorityStack timeout).
   */
  update(next: AnticipationClip | null, now_ms: number): void {
    if (next === null) return;
    if (!PHASE_47_ANTICIPATIONS.includes(next)) {
      throw new Error(
        `AnticipationLayer.update: invalid intent '${String(next)}'`,
      );
    }
    if (next === this.current) return;
    const clip = ANTICIPATION_CLIP_NAME[next];
    const prevClip = this.current ? ANTICIPATION_CLIP_NAME[this.current] : null;
    const timing = transition("anticipation", prevClip, clip);
    this.stack.play("anticipation", {
      clip,
      fade_in_ms: timing.fade_in_ms,
      fade_out_ms: timing.fade_out_ms,
      now_ms,
      timeout_ms: ANTICIPATION_TIMEOUT_MS,
    });
    this.current = next;
  }

  /** Current anticipation intent (last applied), or null at boot. */
  currentIntent(): AnticipationClip | null {
    return this.current;
  }
}
