/* Phase 13 Plan 07 — mood.ts vitest spec (Task 1, 9 tests).
 *
 * Tests pin:
 *   - getCurrentMood / setCurrentMood singleton contract (boot default,
 *     mid-session swap, no silent-fallback on bad input).
 *   - pickFromPool deterministic-with-seed + throws on empty pool.
 *   - MOOD_PROFILES shape regression (3 entries, expected cooldown_ms
 *     values, valid MascotState pool entries).
 *
 * NB: each test resets the singleton back to "hype-man" in beforeEach
 * so the suite is order-independent even though mood.ts holds module
 * state.
 */

import { beforeEach, describe, expect, it } from "vitest";

import type { MascotState } from "./types.js";
import {
  MOOD_PROFILES,
  getCurrentMood,
  pickFromPool,
  setCurrentMood,
} from "./mood.js";

// Reset singleton between tests so order-dependence can't leak.
beforeEach(() => {
  setCurrentMood("hype-man");
});

describe("mood.ts — getCurrentMood / setCurrentMood singleton", () => {
  it("Test 1: getCurrentMood initially returns 'hype-man'", () => {
    expect(getCurrentMood()).toBe("hype-man");
  });

  it("Test 2: setCurrentMood('teacher') updates the singleton", () => {
    setCurrentMood("teacher");
    expect(getCurrentMood()).toBe("teacher");
  });

  it("Test 3: setCurrentMood('invalid') throws (no silent fallback)", () => {
    expect(() =>
      setCurrentMood("invalid" as "hype-man"),
    ).toThrow(/unknown mood/);
  });
});

describe("mood.ts — pickFromPool", () => {
  it("Test 4: pickFromPool(['a','b','c'], 0) returns first element", () => {
    expect(pickFromPool(["dance_a", "dance_b", "dance_hard"], 0)).toBe(
      "dance_a",
    );
  });

  it("Test 5: pickFromPool(['a','b','c'], 1) returns second element", () => {
    expect(pickFromPool(["dance_a", "dance_b", "dance_hard"], 1)).toBe(
      "dance_b",
    );
  });

  it("Test 6: pickFromPool([], 0) throws (no silent fallback)", () => {
    expect(() => pickFromPool([] as MascotState[], 0)).toThrow(/empty/);
  });
});

describe("mood.ts — MOOD_PROFILES shape", () => {
  it("Test 7: MOOD_PROFILES has exactly 3 entries with correct names", () => {
    const keys = Object.keys(MOOD_PROFILES).sort();
    expect(keys).toEqual(["coach", "hype-man", "teacher"]);
    expect(MOOD_PROFILES["hype-man"].name).toBe("hype-man");
    expect(MOOD_PROFILES["teacher"].name).toBe("teacher");
    expect(MOOD_PROFILES["coach"].name).toBe("coach");
  });

  it("Test 8: every MoodProfile pool entry is a valid MascotState", () => {
    // Structural test — list of all valid MascotState names from types.ts.
    // (Lifted from types.ts MascotState union; if a future state is added,
    // include it here too.)
    const VALID_STATES: ReadonlySet<MascotState> = new Set<MascotState>([
      "idle_breathe",
      "idle_breathe_slow",
      "idle_bop_to_beat_mellow",
      "idle_bop_to_beat_energetic",
      "dance_a",
      "dance_b",
      "dance_hard",
      "dance_alt",
      "dance_alt2",
      "talk_loop",
      "talk_loop_calm",
      "talk_loop_energetic",
      "react_yes",
      "react_no",
      "react_no_alt",
      "react_surprised",
      "react_drop",
      "react_glitch",
      "point_explain",
      "gesture_wide",
      "gesture_wide_alt",
      "puff_particle",
      "celebrate",
      "sleep",
      "locomotion_walk",
      "locomotion_run",
    ]);

    for (const moodName of Object.keys(MOOD_PROFILES) as Array<
      keyof typeof MOOD_PROFILES
    >) {
      const profile = MOOD_PROFILES[moodName];
      expect(VALID_STATES.has(profile.idle_default)).toBe(true);
      expect(VALID_STATES.has(profile.talk_state)).toBe(true);
      for (const s of profile.idle_pool) expect(VALID_STATES.has(s)).toBe(true);
      for (const s of profile.dance_pool) expect(VALID_STATES.has(s)).toBe(true);
    }
  });

  it("Test 9: reaction_cooldown_ms pins per-mood cadence values", () => {
    // Regression pin from PLAN.md <interfaces> block. Don't drift without
    // a deliberate plan update.
    expect(MOOD_PROFILES["hype-man"].reaction_cooldown_ms).toBe(12_000);
    expect(MOOD_PROFILES["teacher"].reaction_cooldown_ms).toBe(18_000);
    expect(MOOD_PROFILES["coach"].reaction_cooldown_ms).toBe(24_000);
  });
});
