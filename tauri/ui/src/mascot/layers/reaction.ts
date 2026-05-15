/* Phase 31 Plan 04 — Reaction layer (priority 80).
 *
 * Fires reaction clips in response to `[emote:NAME]` tags parsed out of
 * Gemini response text (Python `emote_parser` extracts; ws_bus
 * `reaction_intent` field carries the latest fire to the frontend).
 *
 * Priority 80 — highest in the 4-layer stack. Cancel-aware (Pitfall
 * P72): a `cancel()` call uses the PriorityStack priority-999 sentinel
 * to flush the reaction queue AND every other non-base layer in the
 * same call.
 *
 * 2.5s timeout — matches the v2.0 priority-70 anticipation contract.
 * After the timeout, PriorityStack.tick() settles the layer and the
 * caller is expected to clear it back to silence (no follow-up clip on
 * the reaction channel; reactions are one-shot).
 */

import type { MascotReaction } from "../types.js";
import { MASCOT_REACTIONS } from "../types.js";
import type { PriorityStack } from "../priority-stack.js";
import { transition } from "../crossfade-policy.js";

export const REACTION_PRIORITY = 80;

/** v2.0 priority-70 anticipation contract value — extended to priority-80
 *  reaction per CONTEXT Area 1.5. */
export const REACTION_TIMEOUT_MS = 2500;

/** Map intent → clip name. Naming convention matches the existing
 *  react_* / point_* / gesture_* family in `types.ts`. */
const REACTION_CLIP_NAME: Record<MascotReaction, string> = {
  wave: "react_wave",
  point_left: "gesture_point_left",
  point_right: "gesture_point_right",
  fist_pump: "react_fist_pump",
  nod: "react_nod",
  headbang: "react_headbang",
  surprised: "react_surprised",
};

/**
 * ReactionLayer — schedules priority-80 transitions on a shared
 * PriorityStack.
 */
export class ReactionLayer {
  private readonly stack: PriorityStack;
  /** Most-recent intent fired (for diagnostic / dedup); null after
   *  PriorityStack.tick() settles the layer. */
  private lastIntent: MascotReaction | null = null;

  constructor(stack: PriorityStack) {
    this.stack = stack;
  }

  /**
   * Fire a reaction. Anti-slop: unknown intent throws — the Python
   * `emote_parser` is supposed to whitelist before this is invoked.
   *
   * Same-intent re-fire is allowed and stacks via PriorityStack's
   * queue (back-to-back fist pumps work).
   */
  fire(intent: MascotReaction, now_ms: number): void {
    if (!MASCOT_REACTIONS.includes(intent)) {
      throw new Error(
        `ReactionLayer.fire: unknown intent '${String(intent)}' ` +
          `(expected one of ${MASCOT_REACTIONS.join(", ")})`,
      );
    }
    const clip = REACTION_CLIP_NAME[intent];
    const timing = transition("reaction", null, clip);
    this.stack.play("reaction", {
      clip,
      fade_in_ms: timing.fade_in_ms,
      fade_out_ms: timing.fade_out_ms,
      now_ms,
      timeout_ms: REACTION_TIMEOUT_MS,
    });
    this.lastIntent = intent;
  }

  /**
   * Cancel — uses PriorityStack priority-999 sentinel which flushes ALL
   * non-base layers. This matches the v2.0 cancel-aware crossfade-to-
   * settle path (Pitfall P72): a cancel during reaction should snap
   * everything except base to silence within 100ms.
   */
  cancel(): void {
    this.stack.cancel("reaction", { flush: true });
    this.lastIntent = null;
  }

  /** Most-recent fired intent, or null after timeout / cancel. */
  currentIntent(): MascotReaction | null {
    return this.lastIntent;
  }

  /**
   * Hook called by the caller after PriorityStack.tick() reports a
   * `reaction` channel timeout. Clears the diagnostic intent. The
   * renderer is expected to fade the reaction clip back to silence
   * (no follow-up settle clip — reactions are one-shot).
   */
  onTimeout(): void {
    this.lastIntent = null;
  }
}
