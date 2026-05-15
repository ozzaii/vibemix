/* Phase 31 Plan 03 — Emotion layer (priority 60).
 *
 * Reads the ws_bus `emotion` payload field (set by the Python
 * emotion_router) and decides when to re-fire the priority-60 channel
 * on the PriorityStack.
 *
 * Re-fire policy: only when the emotion value CHANGES. Same-value
 * updates are no-ops so we don't churn the mixer with redundant
 * crossfades on every 30Hz ws_bus tick.
 *
 * ADDITIVE-ONLY (Pitfall P47): this layer composes on top of the
 * existing mascot rig; it does not modify the v2.0 state-machine.
 */

import type { MascotEmotion } from "../types.js";
import { MASCOT_EMOTIONS } from "../types.js";
import type { PriorityStack } from "../priority-stack.js";
import { transition } from "../crossfade-policy.js";

export const EMOTION_PRIORITY = 60;

/** Maps each emotion to the BaseClip variant we render on the
 *  emotion channel. Naming convention: `emotion_{name}` — matches what
 *  the GLB animation set is expected to provide (Phase 35 lands real
 *  clips; v2.0 placeholders re-use the talk pool). */
const EMOTION_CLIP_NAME: Record<MascotEmotion, string> = {
  neutral: "emotion_neutral",
  focused: "emotion_focused",
  hyped: "emotion_hyped",
  concerned: "emotion_concerned",
};

/**
 * EmotionLayer — pure-state holder that schedules priority-60
 * transitions on a shared PriorityStack.
 */
export class EmotionLayer {
  private current: MascotEmotion;
  private readonly stack: PriorityStack;

  constructor(stack: PriorityStack, initial: MascotEmotion = "neutral") {
    if (!MASCOT_EMOTIONS.includes(initial)) {
      throw new Error(
        `EmotionLayer: invalid initial emotion '${String(initial)}'`,
      );
    }
    this.current = initial;
    this.stack = stack;
  }

  /**
   * Update the layer with a fresh emotion reading.
   *
   * - same as current → no-op (don't churn the mixer).
   * - new emotion → schedule a crossfade on the priority-60 channel.
   *
   * `null` is treated as "no signal" and is a no-op so backward-compat
   * with pre-Phase-31 ws_bus payloads holds.
   */
  update(next: MascotEmotion | null, now_ms: number): void {
    if (next === null) return;
    if (!MASCOT_EMOTIONS.includes(next)) {
      throw new Error(
        `EmotionLayer.update: invalid emotion '${String(next)}'`,
      );
    }
    if (next === this.current) return;
    const clip = EMOTION_CLIP_NAME[next];
    const timing = transition("emotion", EMOTION_CLIP_NAME[this.current], clip);
    this.stack.play("emotion", {
      clip,
      fade_in_ms: timing.fade_in_ms,
      fade_out_ms: timing.fade_out_ms,
      now_ms,
    });
    this.current = next;
  }

  /** Current emotion (last applied). */
  currentEmotion(): MascotEmotion {
    return this.current;
  }
}
