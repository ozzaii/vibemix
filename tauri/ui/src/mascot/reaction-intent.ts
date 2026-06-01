import { MASCOT_REACTIONS } from "./types.js";
import type { MascotReaction, MascotState } from "./types.js";

export interface ReactionIntentSelection {
  intent: MascotReaction;
  seq: number;
  state: MascotState;
}

export const REACTION_INTENT_STATE: Readonly<Record<MascotReaction, MascotState>> =
  Object.freeze({
    wave: "gesture_wide",
    point_left: "point_explain",
    point_right: "gesture_wide_alt",
    fist_pump: "celebrate",
    nod: "react_yes",
    headbang: "react_drop",
    surprised: "react_surprised",
  });

export function selectReactionIntent(
  message: unknown,
  lastSeq: number,
): ReactionIntentSelection | null {
  if (!message || typeof message !== "object") return null;
  const m = message as Record<string, unknown>;
  if (m.type !== "snapshot") return null;
  const intent = m.reaction_intent;
  if (typeof intent !== "string") return null;
  if (!MASCOT_REACTIONS.includes(intent as MascotReaction)) return null;
  const seq = m.reaction_intent_seq;
  if (typeof seq !== "number" || !Number.isFinite(seq)) return null;
  const wholeSeq = Math.trunc(seq);
  if (wholeSeq <= lastSeq) return null;
  const mascotIntent = intent as MascotReaction;
  return {
    intent: mascotIntent,
    seq: wholeSeq,
    state: REACTION_INTENT_STATE[mascotIntent],
  };
}
