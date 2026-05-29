import { describe, expect, test } from "vitest";

import {
  PILL_DEMO_REACTION_KEYS,
  PILL_DEMO_REACTION_TEXT,
  PILL_MOVE_GRADE_COPY_GRAMMAR,
  PILL_MOVE_GRADE_SLUGS,
  PILL_MOVE_GRADE_VOCABULARY,
  normalizePillMoveGradeSlug,
} from "./move-grade-vocabulary.js";

describe("pill move-grade vocabulary", () => {
  test("pins the backend-aligned grade ladder used by the pill and new-pill transfer", () => {
    expect(PILL_MOVE_GRADE_SLUGS).toEqual([
      "negative",
      "mid",
      "clean",
      "sexy",
      "bomb",
      "lit_aff",
    ]);
    expect(PILL_MOVE_GRADE_VOCABULARY).toMatchObject({
      negative: { label: "NEG", xp: 0, intensity: 0, deserved: false, overdrive: false },
      mid: { label: "MID", xp: 8, intensity: 24, deserved: false, overdrive: false },
      clean: { label: "CLEAN", xp: 28, intensity: 48, deserved: true, overdrive: false },
      sexy: { label: "SEXY", xp: 48, intensity: 66, deserved: true, overdrive: false },
      bomb: { label: "BOMB", xp: 72, intensity: 84, deserved: true, overdrive: false },
      lit_aff: { label: "LIT AFF", xp: 100, intensity: 100, deserved: true, overdrive: true },
    });
  });

  test("normalizes only supported backend slugs", () => {
    expect(normalizePillMoveGradeSlug(" SEXY ")).toBe("sexy");
    expect(normalizePillMoveGradeSlug("lit_aff")).toBe("lit_aff");
    expect(normalizePillMoveGradeSlug("lit aff")).toBeNull();
    expect(normalizePillMoveGradeSlug("perfect")).toBeNull();
  });

  test("keeps demo reaction copy tied to the same grade labels", () => {
    expect(PILL_DEMO_REACTION_KEYS).toEqual([
      "clean",
      "sexy",
      "mid",
      "bomb",
      "lit_aff",
      "negative",
    ]);

    for (const key of PILL_DEMO_REACTION_KEYS) {
      const label = PILL_MOVE_GRADE_VOCABULARY[key].label;
      expect(PILL_DEMO_REACTION_TEXT[key].toUpperCase().startsWith(label)).toBe(true);
      expect(PILL_DEMO_REACTION_TEXT[key].length).toBeLessThanOrEqual(68);
    }
  });

  test("ships transfer grammar for evidence-shaped new-pill copy", () => {
    const banned = ["perfect", "flawless", "guaranteed"];

    for (const slug of PILL_MOVE_GRADE_SLUGS) {
      const grammar = PILL_MOVE_GRADE_COPY_GRAMMAR[slug];
      expect(grammar.role.length).toBeGreaterThan(3);
      expect(grammar.evidenceWords.length).toBeGreaterThanOrEqual(4);
      expect(grammar.operatorVerbs.length).toBeGreaterThanOrEqual(4);
      for (const word of banned) {
        expect(grammar.avoidWords).toContain(word);
      }
    }

    expect(PILL_MOVE_GRADE_COPY_GRAMMAR.negative.role).toBe("risk reset");
    expect(PILL_MOVE_GRADE_COPY_GRAMMAR.lit_aff.role).toBe("overdrive");
  });
});
