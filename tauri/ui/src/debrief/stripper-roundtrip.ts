// SPDX-License-Identifier: Apache-2.0
// Plan 29-07 Task 2 — renderer-side defense-in-depth stripper.
//
// Mirrors Python EVIDENCE_CITATION_RE (Phase 18 lock). Sentences without
// at least one citation are dropped. The Plan 29-02 sidecar already
// strips server-side; this is the second filter that catches any
// hypothetical bug in the server stripper before user-facing render.

/**
 * Locked Phase 18 grammar (port of Python ``EVIDENCE_CITATION_RE``):
 *   citation := '[' atom ( ',' atom )* ']'
 *   atom     := source ':' body
 *   source   := 'ev' | 'aud' | 'midi' | 'track' | 'screen' | 'mix' | 'tend'
 *   body     := one-or-more chars excluding whitespace, ']', ','
 */
export const EVIDENCE_CITATION_RE =
  /\[(?:ev|aud|midi|track|screen|mix|tend):[^\s,\]]+(?:,(?:ev|aud|midi|track|screen|mix|tend):[^\s,\]]+)*\]/;

const SENTENCE_BOUNDARY = /(?<=[.!?])\s+/;

export interface StripResult {
  text: string;
  strippedCount: number;
}

/**
 * Return ``{ text, strippedCount }`` after filtering sentences without
 * an EVIDENCE_CITATION_RE match.
 */
export function stripUncitedSentences(text: string): StripResult {
  if (!text || !text.trim()) {
    return { text: '', strippedCount: 0 };
  }
  const sentences = text.trim().split(SENTENCE_BOUNDARY);
  const kept: string[] = [];
  let strippedCount = 0;
  for (const s of sentences) {
    const trimmed = s.trim();
    if (!trimmed) continue;
    if (EVIDENCE_CITATION_RE.test(trimmed)) {
      kept.push(trimmed);
    } else {
      strippedCount += 1;
    }
  }
  return { text: kept.join(' '), strippedCount };
}

/**
 * Apply ``stripUncitedSentences`` to every advice text field of a
 * drill payload. Returns a new payload with cleaned text — never
 * mutates input. ``strippedTotal`` is the sum across the 3 fields.
 */
export function stripDrillFields<
  T extends {
    behavior: string;
    impact: string;
    action_recommended: string;
  },
>(drill: T): { drill: T; strippedTotal: number } {
  const b = stripUncitedSentences(drill.behavior);
  const i = stripUncitedSentences(drill.impact);
  const a = stripUncitedSentences(drill.action_recommended);
  return {
    drill: {
      ...drill,
      behavior: b.text || drill.behavior,
      impact: i.text || drill.impact,
      action_recommended: a.text || drill.action_recommended,
    },
    strippedTotal: b.strippedCount + i.strippedCount + a.strippedCount,
  };
}
