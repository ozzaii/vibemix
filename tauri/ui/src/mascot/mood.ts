/* Phase 13 Plan 07 — Mood profile system (renderer side).
 *
 * SOURCE-OF-TRUTH NOTE:
 *   `currentMood` in this module is a LOCAL CACHE of the canonical sidecar
 *   mood (Python `MusicState.mood`, owned by SettingsApplier per Plan 13-05).
 *   It is NOT the authoritative source — only update it via setCurrentMood()
 *   in response to bus `ipc.mascot.mood_change` events (consumed in index.ts
 *   via the WS bridge added by Plan 13-06).
 *
 *   Three layers hold mood, each at a different abstraction:
 *     1. sidecar  — Python MusicState.mood          (source of truth)
 *     2. UI       — SessionState.settings.mood      (Phase 12 settings drawer)
 *     3. mascot   — currentMood (this module)       (renderer-side cache)
 *
 *   The mascot cache exists so the renderer's animation-pool picker and
 *   the rAF loop don't have to round-trip through SessionState every frame.
 *
 * Purity discipline: this module is Three.js-free (no `import "three"`).
 * The renderer consumes MOOD_PROFILES + getCurrentMood() and wraps the
 * THREE.Color tinting on its side. Keeping mood.ts pure means it loads
 * cheaply in tests and never drags webgl into the test environment.
 *
 * Public surface (interfaces verbatim from 13-07-PLAN.md <interfaces>):
 *   - MoodProfile interface
 *   - MOOD_PROFILES record
 *   - getCurrentMood() / setCurrentMood(mood)
 *   - pickFromPool(pool, seed?)
 */

import type { MascotState } from "./types.js";

/**
 * The renderer-side projection of a mood persona. Sidecar Plan 13-05
 * owns `voice_id` + `vocab_profile` on its half of the same persona
 * record; this interface covers only the rig + lighting + cooldown
 * fields the renderer needs.
 */
export interface MoodProfile {
  name: "hype-man" | "teacher" | "coach";
  // ── Animation pool ──────────────────────────────────────────────────
  /** What the mascot returns to when no event fires. */
  idle_default: MascotState;
  /** Alternates between these for idle variety. */
  idle_pool: MascotState[];
  /** Pool the dance class picks from when phase=drop/groove triggers. */
  dance_pool: MascotState[];
  /** talk_loop variant for this mood. */
  talk_state: MascotState;
  // ── Light + render tuning ───────────────────────────────────────────
  /** 0.0..1.0 — hype-man brighter, coach moodier. */
  ambient_intensity: number;
  /** Directional light intensity. */
  key_intensity: number;
  // ── Cadence ─────────────────────────────────────────────────────────
  /**
   * Reaction cooldown (ms). Sidecar reads this too via the prompt
   * template; the renderer respects the same cadence for clip-pool
   * re-shuffling.
   */
  reaction_cooldown_ms: number;
}

/**
 * The three mood personas, verbatim from 13-07-PLAN.md <interfaces>.
 * Verbatim — do NOT tune these values without a planner pass.
 *
 * Pool naming references:
 *   - idle_bop_to_beat_energetic / _mellow → bound to Bass_Beats /
 *     Indoor_Swing clips per manifest.json (Plan 13-01).
 *   - dance_a / dance_b / dance_hard / dance_alt → manifest dance clips.
 *   - talk_loop / talk_loop_calm / talk_loop_energetic → manifest talk
 *     variants.
 */
export const MOOD_PROFILES: Record<
  "hype-man" | "teacher" | "coach",
  MoodProfile
> = {
  "hype-man": {
    name: "hype-man",
    idle_default: "idle_bop_to_beat_energetic",
    idle_pool: ["idle_bop_to_beat_energetic", "idle_bop_to_beat_mellow"],
    dance_pool: ["dance_hard", "dance_a", "dance_b", "dance_alt"],
    talk_state: "talk_loop_energetic",
    ambient_intensity: 0.5,
    key_intensity: 0.9,
    reaction_cooldown_ms: 12_000,
  },
  teacher: {
    name: "teacher",
    idle_default: "idle_bop_to_beat_mellow",
    idle_pool: ["idle_bop_to_beat_mellow", "idle_breathe"],
    dance_pool: ["dance_a", "dance_b"],
    talk_state: "talk_loop_calm",
    ambient_intensity: 0.55,
    key_intensity: 0.7,
    reaction_cooldown_ms: 18_000,
  },
  coach: {
    name: "coach",
    idle_default: "idle_breathe",
    idle_pool: ["idle_breathe", "idle_bop_to_beat_mellow"],
    dance_pool: ["dance_a"],
    talk_state: "talk_loop",
    ambient_intensity: 0.4,
    key_intensity: 0.6,
    reaction_cooldown_ms: 24_000,
  },
};

// ── Singleton state ──────────────────────────────────────────────────────

/**
 * Local cache of the canonical sidecar mood. CONTEXT Open Q 3 + 13-CONTEXT
 * Area 4 default = "hype-man". Only setCurrentMood() in response to a bus
 * `ipc.mascot.mood_change` event is allowed to update this — never write
 * it directly from anywhere else in the codebase.
 */
let currentMood: "hype-man" | "teacher" | "coach" = "hype-man";

/** Read the current mood. Returns the local cache; bus is canonical. */
export function getCurrentMood(): "hype-man" | "teacher" | "coach" {
  return currentMood;
}

/**
 * Update the local mood cache. Rejects unknown mood strings with a thrown
 * Error — anti-silent-fallback per PLAN must-haves + 13-CONTEXT trust
 * boundary T-13-07-01.
 *
 * The Literal narrowing on the parameter type already catches static
 * misuse; the runtime guard handles dynamic input from the WS bus where
 * the schema validator at the boundary should have already rejected
 * non-canonical strings, but this is belt-and-braces.
 */
export function setCurrentMood(
  mood: "hype-man" | "teacher" | "coach",
): void {
  if (!Object.prototype.hasOwnProperty.call(MOOD_PROFILES, mood)) {
    throw new Error(
      `unknown mood: '${String(mood)}' (expected one of ${Object.keys(
        MOOD_PROFILES,
      ).join(", ")})`,
    );
  }
  currentMood = mood;
}

// ── Pool picker ──────────────────────────────────────────────────────────

/**
 * Pick a MascotState from a pool.
 *
 * - Empty pool → throws (no silent fallback to a default state).
 * - Seed undefined → random pick via Math.random.
 * - Seed number → deterministic `pool[seed % pool.length]`. Used by
 *   tests + future Plan 13-06 event-dispatcher to compute repeatable
 *   picks within a single bar.
 */
export function pickFromPool(
  pool: MascotState[],
  seed?: number,
): MascotState {
  if (pool.length === 0) {
    throw new Error("pickFromPool: empty pool (no silent fallback)");
  }
  if (seed === undefined) {
    return pool[Math.floor(Math.random() * pool.length)] as MascotState;
  }
  // Deterministic branch — modulo handles negative + non-integer seeds
  // by coercing to a positive integer first.
  const idx = ((Math.trunc(seed) % pool.length) + pool.length) % pool.length;
  return pool[idx] as MascotState;
}
