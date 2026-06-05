// Single source of truth: engine vocabulary to DJ language.
//
// The engine keeps its internal words (grounded, CLAP, sidecar, the ML model
// ids); the UI prints only the DJ-facing phrases below. This generalizes the
// deck status language, so the shell and live deck never drift to two words for the
// same concept. New user-visible copy should reach for these instead of
// inventing a fresh synonym.
//
// Keep every value DJ-plain: no engine jargon (grounded, proof, receipt,
// sidecar, CLAP, cosine), no model filenames, no em dashes. The slop gate
// asserts this (a contributor must not launder jargon through the helper).

export const DJ_VOCAB = {
  /** The co-host is listening + watching + ready to react. */
  grounded: "reading the room",
  /** Booting / not yet ready to react. */
  tuningIn: "tuning in",
  /** The reaction brain is unreachable. */
  serviceOffline: "AI service offline",
  /** The CLAP similarity model, by what it does. */
  soundMatch: "Sound match",
  /** The CUE-DETR cue model, by what it does. */
  cueFinder: "Cue finder",
  /** The MOSS speech model, by what it does. */
  voiceModel: "Voice",
  /** A debrief citation: the evidence behind a call. */
  whyReview: "the why",
} as const;

export type DjVocabKey = keyof typeof DJ_VOCAB;

/** Look up the one DJ phrase for an engine concept. */
export function djLabel(key: DjVocabKey): string {
  return DJ_VOCAB[key];
}
