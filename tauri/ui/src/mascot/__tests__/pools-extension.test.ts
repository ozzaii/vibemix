/* Phase 47 / MASCOT-04 — pools.ts extension vitest spec.
 *
 * Asserts:
 *   - Each Phase 47 sibling map (BASE / EMOTION / ANTICIPATION / REACTION
 *     CLIP_TO_SLOT) has correct cardinality.
 *   - Phase 47 anticipation slots are disjoint from legacy KIND_TO_SLOT prep_*.
 *   - Existing Phase 43 § VIS-05 invariants (KIND_TO_SLOT + MOOD_POOLS) preserved.
 */

import { describe, expect, it } from "vitest";

import {
  BASE_CLIP_TO_SLOT,
  EMOTION_CLIP_TO_SLOT,
  ANTICIPATION_CLIP_TO_SLOT,
  REACTION_CLIP_TO_SLOT,
  PHASE_47_ALL_SLOTS,
  MOOD_POOLS,
} from "../pools.js";

/** KIND_TO_SLOT is module-internal in pools.ts. Mirror its 5 entries here
 *  via the public MOOD_POOLS surface to verify the § VIS-05 invariant. */
const LEGACY_PREP_SLOTS = new Set([
  "prep_settle",
  "prep_head_turn_left",
  "prep_head_turn_right",
  "prep_lean_in_hyped",
  "prep_lean_in_neutral",
]);

describe("Phase 47 / MASCOT-04 — pools.ts extension", () => {
  it("BASE_CLIP_TO_SLOT has exactly 3 entries", () => {
    expect(Object.keys(BASE_CLIP_TO_SLOT)).toHaveLength(3);
  });

  it("EMOTION_CLIP_TO_SLOT has exactly 5 entries", () => {
    expect(Object.keys(EMOTION_CLIP_TO_SLOT)).toHaveLength(5);
  });

  it("ANTICIPATION_CLIP_TO_SLOT has exactly 5 entries (NEW prep_kick family)", () => {
    expect(Object.keys(ANTICIPATION_CLIP_TO_SLOT)).toHaveLength(5);
    expect(ANTICIPATION_CLIP_TO_SLOT.prep_kick).toBe("prep_kick");
  });

  it("REACTION_CLIP_TO_SLOT has exactly 10 entries", () => {
    expect(Object.keys(REACTION_CLIP_TO_SLOT)).toHaveLength(10);
    expect(REACTION_CLIP_TO_SLOT.react_hype_peak).toBe("react_hype_peak");
  });

  it("PHASE_47_ALL_SLOTS combines all 4 families (23 unique slots)", () => {
    expect(PHASE_47_ALL_SLOTS).toHaveLength(23);
    expect(new Set(PHASE_47_ALL_SLOTS).size).toBe(23);
  });

  it("Phase 47 anticipation slots do NOT collide with legacy prep_* slots", () => {
    const newPrep = Object.values(ANTICIPATION_CLIP_TO_SLOT);
    for (const s of newPrep) {
      expect(LEGACY_PREP_SLOTS.has(s)).toBe(false);
    }
  });

  it("Existing MOOD_POOLS surface still references the legacy 5 prep_* slots", () => {
    const allMoodSlots = Object.values(MOOD_POOLS).flatMap((pool) =>
      pool.map((e) => e.slot),
    );
    for (const slot of LEGACY_PREP_SLOTS) {
      expect(allMoodSlots).toContain(slot);
    }
  });

  it("Existing MOOD_POOLS § VIS-05 invariant preserved (regression guard)", () => {
    expect(Object.keys(MOOD_POOLS).sort()).toEqual([
      "coach",
      "hype-man",
      "teacher",
    ]);
  });
});
