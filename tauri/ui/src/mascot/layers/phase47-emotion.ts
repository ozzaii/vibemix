/* Phase 47 / MASCOT-04 — Emotion layer (priority 60) for the new 5-emotion taxonomy.
 *
 * Sibling to the existing Phase 31 emotion.ts which uses the v2.0 4-emotion
 * vocabulary (neutral/focused/hyped/concerned). This file ships the Phase 47
 * 5-emotion taxonomy (joy/trust/surprise/anticipation/focus) anchored to
 * Plutchik 8-primary subset per .planning/research/FEATURES.md § MASCOT.
 *
 * Both layers can coexist; the new EVENT_LAYER_PRIORITY_MAP in event-dispatcher.ts
 * routes Phase 47 events through this new layer.
 *
 * ADDITIVE-ONLY: composes on top of the existing rig via the shared PriorityStack.
 */

import type { EmotionClip } from "../types.js";
import { PHASE_47_EMOTIONS } from "../types.js";
import type { PriorityStack } from "../priority-stack.js";
import { transition } from "../crossfade-policy.js";

export const PHASE47_EMOTION_PRIORITY = 60;

/** 1:1 mapping — slot stem = clip name set by retarget_to_neon_rebel.py output. */
const EMOTION_CLIP_NAME: Record<EmotionClip, string> = {
  emotion_joy: "emotion_joy",
  emotion_trust: "emotion_trust",
  emotion_surprise: "emotion_surprise",
  emotion_anticipation: "emotion_anticipation",
  emotion_focus: "emotion_focus",
};

export class Phase47EmotionLayer {
  private current: EmotionClip;
  private readonly stack: PriorityStack;

  constructor(stack: PriorityStack, initial: EmotionClip = "emotion_focus") {
    if (!PHASE_47_EMOTIONS.includes(initial)) {
      throw new Error(
        `Phase47EmotionLayer: invalid initial emotion '${String(initial)}'`,
      );
    }
    this.current = initial;
    this.stack = stack;
  }

  update(next: EmotionClip | null, now_ms: number): void {
    if (next === null) return;
    if (!PHASE_47_EMOTIONS.includes(next)) {
      throw new Error(
        `Phase47EmotionLayer.update: invalid emotion '${String(next)}'`,
      );
    }
    if (next === this.current) return;
    const clip = EMOTION_CLIP_NAME[next];
    const prevClip = EMOTION_CLIP_NAME[this.current];
    const timing = transition("emotion", prevClip, clip);
    this.stack.play("emotion", {
      clip,
      fade_in_ms: timing.fade_in_ms,
      fade_out_ms: timing.fade_out_ms,
      now_ms,
    });
    this.current = next;
  }

  currentEmotion(): EmotionClip {
    return this.current;
  }
}
