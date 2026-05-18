/* Phase 47 / MASCOT-04 — Reaction layer (priority 80) for the new 10-reaction taxonomy.
 *
 * Sibling to the existing Phase 31 reaction.ts which uses the v2.0 7-reaction
 * vocabulary (wave/point_left/point_right/fist_pump/nod/headbang/surprised).
 * This file ships the Phase 47 10-reaction event-class set
 * (kick_swap / sub_layer / breakdown / reentry / phrase_boundary /
 * distortion_climb / acid_line / mix_in / mix_out / hype_peak) — maps 1:1
 * to v2.0 EventDetector event classes + 2 Hard Tek detectors.
 *
 * ADDITIVE-ONLY: composes on top of the existing rig via the shared PriorityStack.
 */

import type { ReactionClip } from "../types.js";
import { PHASE_47_REACTIONS } from "../types.js";
import type { PriorityStack } from "../priority-stack.js";
import { transition } from "../crossfade-policy.js";

export const PHASE47_REACTION_PRIORITY = 80;

/** v2.0 priority-70 anticipation contract value — extended to priority-80 reaction. */
export const PHASE47_REACTION_TIMEOUT_MS = 2500;

const REACTION_CLIP_NAME: Record<ReactionClip, string> = {
  react_kick_swap: "react_kick_swap",
  react_sub_layer: "react_sub_layer",
  react_breakdown: "react_breakdown",
  react_reentry: "react_reentry",
  react_phrase_boundary: "react_phrase_boundary",
  react_distortion_climb: "react_distortion_climb",
  react_acid_line: "react_acid_line",
  react_mix_in: "react_mix_in",
  react_mix_out: "react_mix_out",
  react_hype_peak: "react_hype_peak",
};

export class Phase47ReactionLayer {
  private last: ReactionClip | null;
  private readonly stack: PriorityStack;

  constructor(stack: PriorityStack) {
    this.last = null;
    this.stack = stack;
  }

  /** Fire a one-shot reaction. Cancel-aware via PriorityStack's same-channel re-target. */
  fire(intent: ReactionClip, now_ms: number): void {
    if (!PHASE_47_REACTIONS.includes(intent)) {
      throw new Error(
        `Phase47ReactionLayer.fire: invalid intent '${String(intent)}'`,
      );
    }
    const clip = REACTION_CLIP_NAME[intent];
    const prevClip = this.last ? REACTION_CLIP_NAME[this.last] : null;
    const timing = transition("reaction", prevClip, clip);
    this.stack.play("reaction", {
      clip,
      fade_in_ms: timing.fade_in_ms,
      fade_out_ms: timing.fade_out_ms,
      now_ms,
      timeout_ms: PHASE47_REACTION_TIMEOUT_MS,
    });
    this.last = intent;
  }

  lastIntent(): ReactionClip | null {
    return this.last;
  }
}
