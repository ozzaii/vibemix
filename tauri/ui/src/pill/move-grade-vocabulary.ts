/* Pill move-grade vocabulary.
 *
 * Mirrors src/vibemix/intel/move_grade.py. The backend remains the source of
 * truth; this local contract keeps pill rendering, demo reactions, and transfer
 * docs from drifting while wire data stays authoritative.
 */

import moveGradeVocabularyJson from "./move-grade-vocabulary.json";

export const PILL_MOVE_GRADE_SLUGS = [
  "negative",
  "mid",
  "clean",
  "sexy",
  "bomb",
  "lit_aff",
] as const;

export type MoveGradeSlug = (typeof PILL_MOVE_GRADE_SLUGS)[number];
export type PillDemoReactionKey = MoveGradeSlug;

export interface PillMoveGradeVocabularyEntry {
  label: string;
  xp: number;
  intensity: number;
  reason: string;
  deserved: boolean;
  overdrive: boolean;
  sentiment: "negative" | "neutral" | "positive";
}

export interface PillMoveGradeCopyGrammarEntry {
  role: string;
  evidenceWords: readonly string[];
  operatorVerbs: readonly string[];
  avoidWords: readonly string[];
}

export const PILL_MOVE_GRADE_VOCABULARY =
  moveGradeVocabularyJson as Record<MoveGradeSlug, PillMoveGradeVocabularyEntry>;

export const PILL_MOVE_GRADE_COPY_GRAMMAR: Record<
  MoveGradeSlug,
  PillMoveGradeCopyGrammarEntry
> = {
  negative: {
    role: "risk reset",
    evidenceWords: ["clash", "tempo", "cue", "short", "rub"],
    operatorVerbs: ["stop", "reset", "wait", "clear"],
    avoidWords: ["lit", "bomb", "perfect", "flawless", "guaranteed"],
  },
  mid: {
    role: "careful playable",
    evidenceWords: ["timing", "phrase", "filter", "door", "care"],
    operatorVerbs: ["hold", "wait", "trim", "check"],
    avoidWords: ["clean", "sexy", "perfect", "flawless", "guaranteed"],
  },
  clean: {
    role: "technical lock",
    evidenceWords: ["phrase", "cue", "bass", "key", "tempo"],
    operatorVerbs: ["breathe", "hold", "land", "keep"],
    avoidWords: ["huge", "insane", "perfect", "flawless", "guaranteed"],
  },
  sexy: {
    role: "smooth lift",
    evidenceWords: ["blend", "vocal", "glide", "lift", "handoff"],
    operatorVerbs: ["float", "ease", "ride", "keep"],
    avoidWords: ["thirsty", "perfect", "flawless", "guaranteed"],
  },
  bomb: {
    role: "payoff hit",
    evidenceWords: ["drop", "room", "payoff", "energy", "floor"],
    operatorVerbs: ["snap", "ride", "open", "push"],
    avoidWords: ["safe", "maybe", "perfect", "flawless", "guaranteed"],
  },
  lit_aff: {
    role: "overdrive",
    evidenceWords: ["clicks", "room", "lock", "payoff", "eight"],
    operatorVerbs: ["ride", "hold", "stretch", "own"],
    avoidWords: ["normal", "maybe", "perfect", "flawless", "guaranteed"],
  },
};

export const PILL_DEMO_REACTION_KEYS: PillDemoReactionKey[] = [
  "clean",
  "sexy",
  "mid",
  "bomb",
  "lit_aff",
  "negative",
];

export const PILL_DEMO_REACTION_TEXT: Record<PillDemoReactionKey, string> = {
  clean: "CLEAN. Phrase caught. Bass swap sealed. Let it breathe.",
  sexy: "SEXY. Smooth blend. Vocal floats. Hands stay light.",
  mid: "MID, playable. Hold the filter. Wait for a cleaner door.",
  bomb: "BOMB. Drop landed. Floor opens. Snap next cue on one.",
  lit_aff: "LIT AFF. Everything clicks. Whole room locks. Ride eight.",
  negative: "NEG. Harmonic rub. Do not force it. Reset the exit.",
};

export function isPillMoveGradeSlug(raw: unknown): raw is MoveGradeSlug {
  if (typeof raw !== "string") return false;
  return PILL_MOVE_GRADE_SLUGS.includes(raw.trim().toLowerCase() as MoveGradeSlug);
}

export function normalizePillMoveGradeSlug(raw: unknown): MoveGradeSlug | null {
  if (!isPillMoveGradeSlug(raw)) return null;
  return raw.trim().toLowerCase() as MoveGradeSlug;
}
