/* Phase 43 Plan 43-06 / VIS-05 — mood → animation pool mapping.
 *
 * Three personas, each with a 3-clip pool. Pool entries reference the
 * prep_*.glb slot names from Plan 43-05 §VIS-04 retarget pipeline.
 *
 * Taxonomy is FIXED per 43-CONTEXT §VIS-05 — pool entries are a closed
 * set; animation expansion beyond these 5 clips is v2.x deferred (per
 * 43-CONTEXT <deferred> "Animation expansion beyond 5 clips: v2.x").
 *
 * Pure data + lookup. No THREE dependency. Crossfade policy + state
 * machine consume this via the existing dispatcher in event-dispatcher.ts.
 *
 * SOURCE-OF-TRUTH NOTE:
 *   Pool TAXONOMY (kinds per mood) is locked here.
 *   Pool PICKING ORDER + SEEDING uses pickFromPool() in mood.ts (Phase 13).
 *   This module does not handle picking — only the closed-set declaration.
 *
 * Threat T-43-06-01 (Tampering):
 *   pools.test.ts grep-gates this taxonomy against §VIS-05 verbatim.
 *   Any kind change requires updating the test in lockstep.
 */

export type MoodKey = "hype-man" | "teacher" | "coach";

/** Closed set of clip kinds across all 3 mood pools (5 unique). */
export type ClipKind =
  | "idle"
  | "talk_short"
  | "talk_long"
  | "celebrate"
  | "headbob";

export interface PoolEntry {
  /** Abstract clip kind (idle / talk_short / talk_long / celebrate / headbob). */
  kind: ClipKind;
  /** prep_*.glb slot name (without .glb extension); sourced from §VIS-04 mapping. */
  slot: string;
}

/**
 * kind → prep_* slot mapping. Shared across all pools (a kind that
 * appears in two pools maps to the SAME slot). Sourced verbatim from
 * Plan 43-05 §VIS-04 retarget slot taxonomy.
 *
 * Why a flat map instead of per-pool slot strings: locking the mapping
 * in one place catches T-43-06-01 (Tampering) at the type system level
 * and surfaces drift via the cross-pool consistency test.
 */
const KIND_TO_SLOT: Readonly<Record<ClipKind, string>> = Object.freeze({
  idle: "prep_settle",
  talk_short: "prep_head_turn_left",
  talk_long: "prep_head_turn_right",
  celebrate: "prep_lean_in_hyped",
  headbob: "prep_lean_in_neutral",
});

function entry(kind: ClipKind): PoolEntry {
  return Object.freeze({ kind, slot: KIND_TO_SLOT[kind] });
}

/**
 * The 3 mood pools, verbatim from 43-CONTEXT §VIS-05.
 *
 *   Hype-man = [idle, talk_short, celebrate]
 *   Teacher  = [idle, talk_long,  headbob]
 *   Coach    = [idle, talk_short, headbob]
 *
 * Frozen at module load — runtime mutation throws under strict mode.
 */
export const MOOD_POOLS: Readonly<Record<MoodKey, readonly PoolEntry[]>> =
  Object.freeze({
    "hype-man": Object.freeze([
      entry("idle"),
      entry("talk_short"),
      entry("celebrate"),
    ]),
    teacher: Object.freeze([
      entry("idle"),
      entry("talk_long"),
      entry("headbob"),
    ]),
    coach: Object.freeze([
      entry("idle"),
      entry("talk_short"),
      entry("headbob"),
    ]),
  });

/**
 * Lookup the pool for a mood key. Throws on unknown mood — anti-silent-
 * fallback, mirrors mood.ts setCurrentMood() behavior.
 *
 * Accepts `string` (not just MoodKey) because callers may receive mood
 * names off the WS bus where the schema validator at the boundary has
 * already rejected non-canonical strings; this is belt-and-braces.
 */
export function getPoolForMood(mood: string): readonly PoolEntry[] {
  if (!Object.prototype.hasOwnProperty.call(MOOD_POOLS, mood)) {
    throw new Error(
      `unknown mood: '${String(mood)}' (expected one of ${Object.keys(MOOD_POOLS).join(", ")})`,
    );
  }
  return MOOD_POOLS[mood as MoodKey];
}
