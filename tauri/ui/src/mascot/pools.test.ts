/* Phase 43 Plan 43-06 / VIS-05 — mood pool taxonomy test.
 *
 * Pins the 3-persona × {idle, talk_short, talk_long, celebrate, headbob}
 * pool taxonomy verbatim from 43-CONTEXT §VIS-05. Any drift requires
 * updating this test in lockstep with pools.ts AND CONTEXT —
 * threat T-43-06-01 (Tampering).
 *
 * Slot names reference the prep_*.glb slots from Plan 43-05 §VIS-04
 * retarget mapping. The mapping is shared across all 3 personas; e.g.
 * every "talk_short" entry MUST point at prep_head_turn_left.
 */
import { describe, test, expect } from "vitest";

import {
  MOOD_POOLS,
  getPoolForMood,
  type PoolEntry,
  type MoodKey,
  type ClipKind,
} from "./pools.js";

describe("MOOD_POOLS — VIS-05 taxonomy lock", () => {
  test("MOOD_POOLS has exactly 3 keys: hype-man, teacher, coach", () => {
    const keys = Object.keys(MOOD_POOLS).sort();
    expect(keys).toEqual(["coach", "hype-man", "teacher"]);
  });

  test("Hype-man pool = [idle, talk_short, celebrate] (§VIS-05 verbatim)", () => {
    const pool = MOOD_POOLS["hype-man"];
    expect(pool.length).toBe(3);
    expect(pool.map((e: PoolEntry) => e.kind)).toEqual([
      "idle",
      "talk_short",
      "celebrate",
    ]);
  });

  test("Teacher pool = [idle, talk_long, headbob] (§VIS-05 verbatim)", () => {
    const pool = MOOD_POOLS.teacher;
    expect(pool.length).toBe(3);
    expect(pool.map((e: PoolEntry) => e.kind)).toEqual([
      "idle",
      "talk_long",
      "headbob",
    ]);
  });

  test("Coach pool = [idle, talk_short, headbob] (§VIS-05 verbatim)", () => {
    const pool = MOOD_POOLS.coach;
    expect(pool.length).toBe(3);
    expect(pool.map((e: PoolEntry) => e.kind)).toEqual([
      "idle",
      "talk_short",
      "headbob",
    ]);
  });

  test("every pool entry's slot is in the prep_* allow-set (§VIS-04)", () => {
    const ALLOWED = new Set([
      "prep_settle",
      "prep_head_turn_left",
      "prep_head_turn_right",
      "prep_lean_in_hyped",
      "prep_lean_in_neutral",
    ]);
    for (const mood of Object.keys(MOOD_POOLS) as MoodKey[]) {
      for (const entry of MOOD_POOLS[mood]) {
        expect(ALLOWED.has(entry.slot)).toBe(true);
      }
    }
  });

  test("getPoolForMood returns the right pool; unknown mood throws", () => {
    expect(getPoolForMood("coach")).toBe(MOOD_POOLS.coach);
    expect(getPoolForMood("hype-man")).toBe(MOOD_POOLS["hype-man"]);
    expect(getPoolForMood("teacher")).toBe(MOOD_POOLS.teacher);
    expect(() => getPoolForMood("unknown")).toThrow(/unknown mood/);
    expect(() => getPoolForMood("")).toThrow(/unknown mood/);
  });

  test("kind→slot mapping is consistent across pools (e.g. all 'talk_short' → prep_head_turn_left)", () => {
    // For every kind that appears in more than one pool, every entry of
    // that kind MUST reference the same slot (T-43-06-01 mitigation).
    const kindToSlot = new Map<ClipKind, string>();
    for (const mood of Object.keys(MOOD_POOLS) as MoodKey[]) {
      for (const entry of MOOD_POOLS[mood]) {
        const seen = kindToSlot.get(entry.kind);
        if (seen === undefined) {
          kindToSlot.set(entry.kind, entry.slot);
        } else {
          expect(entry.slot).toBe(seen);
        }
      }
    }
    // Spot-check three of the most consequential mappings.
    expect(kindToSlot.get("idle")).toBe("prep_settle");
    expect(kindToSlot.get("talk_short")).toBe("prep_head_turn_left");
    expect(kindToSlot.get("talk_long")).toBe("prep_head_turn_right");
    expect(kindToSlot.get("celebrate")).toBe("prep_lean_in_hyped");
    expect(kindToSlot.get("headbob")).toBe("prep_lean_in_neutral");
  });
});
