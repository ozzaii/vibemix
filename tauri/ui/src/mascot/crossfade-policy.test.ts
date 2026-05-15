/* Phase 31 Plan 01 — Crossfade policy vitest spec.
 *
 * Pure-function tests of the per-layer crossfade timing table.
 */

import { describe, expect, it } from "vitest";

import {
  cancelTransition,
  STAGGER_MS,
  transition,
} from "./crossfade-policy.js";

describe("crossfade-policy.transition", () => {
  it("returns base timing 300/300", () => {
    const t = transition("base", null, "idle_breathe");
    expect(t.fade_in_ms).toBe(300);
    expect(t.fade_out_ms).toBe(300);
    expect(t.stagger_ms).toBe(STAGGER_MS);
  });

  it("returns emotion timing 200/200", () => {
    const t = transition("emotion", "neutral", "hyped");
    expect(t.fade_in_ms).toBe(200);
    expect(t.fade_out_ms).toBe(200);
  });

  it("returns anticipation timing 100/100 (v2.0 Phase 22 lock)", () => {
    const t = transition("anticipation", null, "prep_lean_in_neutral");
    expect(t.fade_in_ms).toBe(100);
    expect(t.fade_out_ms).toBe(100);
  });

  it("returns reaction timing 80/120 (sharp entry, gentle exit)", () => {
    const t = transition("reaction", null, "react_yes");
    expect(t.fade_in_ms).toBe(80);
    expect(t.fade_out_ms).toBe(120);
  });

  it("STAGGER_MS is locked to 100 (Pitfall P62)", () => {
    expect(STAGGER_MS).toBe(100);
  });
});

describe("crossfade-policy.cancelTransition (priority-999 path)", () => {
  it("returns zero fade + zero stagger (instant cut)", () => {
    const t = cancelTransition();
    expect(t.fade_in_ms).toBe(0);
    expect(t.fade_out_ms).toBe(0);
    expect(t.stagger_ms).toBe(0);
  });
});
