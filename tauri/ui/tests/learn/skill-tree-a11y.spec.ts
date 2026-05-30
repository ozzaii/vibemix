// SPDX-License-Identifier: Apache-2.0
// SURF-04 — the skill-tree surface honors v9.0 accessibility: a DUAL-channel cue
// (color + SHAPE, not amber-only — deuteranopia/protanopia/tritanopia distinguishable),
// FULL keyboard-nav for browsing the tree without hardware, and NO time-pressure on
// advancement (motor-impaired-safe). Browsable ≠ activatable: every row is focusable
// to read, but only Mastered rows are buttons.
import { describe, it, expect } from "vitest";
import { renderSkillWall, type SkillWallRow } from "../../src/learn/SkillWall.js";

function row(over: Partial<SkillWallRow>): SkillWallRow {
  return {
    skill_id: "deck_control",
    stage: "locked",
    learn_fill: 0,
    competent: false,
    live_proof_count: 0,
    mastered: false,
    first_mastered_at: null,
    what_remains: "Finish the lessons to reach Competent",
    ...over,
  };
}

const MIX: SkillWallRow[] = [
  row({ skill_id: "deck_control", stage: "locked" }),
  row({ skill_id: "eq_mixing", stage: "competent", competent: true, learn_fill: 1, what_remains: "2 more cited live demos to Master" }),
  row({
    skill_id: "harmonic_mixing", stage: "mastered", mastered: true, competent: true,
    learn_fill: 1, live_proof_count: 3, first_mastered_at: "2026-05-30T11:00:00Z", what_remains: "",
  }),
];

describe("SURF-04 — dual-channel cue (color + shape)", () => {
  it("every row carries a non-color SHAPE glyph AND a text stage label", () => {
    const rows = Array.from(
      renderSkillWall(MIX).querySelectorAll<HTMLElement>(".skill-wall__row"),
    );
    for (const r of rows) {
      const glyph = r.querySelector(".skill-wall__glyph");
      const stage = r.querySelector(".skill-wall__stage");
      expect(glyph, "missing shape glyph").not.toBeNull();
      expect(glyph?.textContent?.trim()).toBeTruthy();
      expect(stage?.textContent?.trim()).toBeTruthy(); // redundant non-color word
    }
  });

  it("the glyph SHAPE differs by stage — readable with zero color perception", () => {
    const glyphs = Array.from(
      renderSkillWall(MIX).querySelectorAll<HTMLElement>(".skill-wall__glyph"),
    ).map((g) => g.textContent);
    expect(new Set(glyphs).size).toBe(3); // locked / competent / mastered = 3 distinct shapes
  });

  it("the glyph is decorative (aria-hidden) — the text label carries the semantic", () => {
    const glyph = renderSkillWall(MIX).querySelector(".skill-wall__glyph");
    expect(glyph?.getAttribute("aria-hidden")).toBe("true");
  });
});

describe("SURF-04 — full keyboard-nav, no time-pressure", () => {
  it("every row is keyboard-focusable for browsing, with a descriptive aria-label", () => {
    const rows = Array.from(
      renderSkillWall(MIX).querySelectorAll<HTMLElement>(".skill-wall__row"),
    );
    for (const r of rows) {
      expect(r.getAttribute("tabindex")).toBe("0");
      const label = r.getAttribute("aria-label") ?? "";
      expect(label.length).toBeGreaterThan(0);
    }
  });

  it("browsable ≠ activatable: only Mastered rows are buttons", () => {
    const rows = Array.from(
      renderSkillWall(MIX).querySelectorAll<HTMLElement>(".skill-wall__row"),
    );
    const locked = rows.find((r) => r.dataset.stage === "locked")!;
    const competent = rows.find((r) => r.dataset.stage === "competent")!;
    const mastered = rows.find((r) => r.dataset.stage === "mastered")!;
    expect(mastered.getAttribute("role")).toBe("button");
    expect(locked.getAttribute("role")).toBeNull();
    expect(competent.getAttribute("role")).toBeNull();
    // ...but all three are still browsable by keyboard.
    expect(locked.getAttribute("tabindex")).toBe("0");
    expect(competent.getAttribute("tabindex")).toBe("0");
  });

  it("no time-pressure — nothing in the tree is disabled or timer-gated", () => {
    const el = renderSkillWall(MIX);
    expect(el.querySelectorAll("[disabled]").length).toBe(0);
    expect(el.querySelectorAll("[aria-disabled='true']").length).toBe(0);
  });
});
