// SPDX-License-Identifier: Apache-2.0
// The Earned Wall (v11.0) — the visible face of the mastery spine. Renders the
// six REQ-locked DJ skills, each half-lit Competent from lessons, Mastered only
// from a CITED live demo. `mastered`/`first_mastered_at` is set ONLY by a
// citation-gated live demo (Invariant #2/#3), so the wall literally proves
// nothing was given — a real trophy case, not a pitch.
import { describe, it, expect } from "vitest";
import {
  renderSkillWall,
  mountSkillWall,
  type SkillWallRow,
} from "../../src/learn/SkillWall.js";

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

const SIX: SkillWallRow[] = [
  row({ skill_id: "deck_control", stage: "competent", competent: true, learn_fill: 1 }),
  row({ skill_id: "beatmatching" }),
  row({ skill_id: "eq_mixing", stage: "competent", competent: true, learn_fill: 0.7 }),
  row({
    skill_id: "harmonic_mixing", stage: "mastered", mastered: true, competent: true,
    learn_fill: 1, live_proof_count: 3, first_mastered_at: "2026-05-30T11:00:00Z",
  }),
  row({ skill_id: "transitions" }),
  row({ skill_id: "phrasing_performance" }),
];

describe("renderSkillWall — the Earned Wall", () => {
  it("renders one row per skill, in input order, with display labels", () => {
    const el = renderSkillWall(SIX);
    const rows = el.querySelectorAll<HTMLElement>(".skill-wall__row");
    expect(rows.length).toBe(6);
    expect(rows[0]!.dataset.skill).toBe("deck_control");
    expect(rows[0]!.querySelector(".skill-wall__name")?.textContent).toBe("Deck Control");
    expect(rows[3]!.querySelector(".skill-wall__name")?.textContent).toBe("Harmonic Mixing");
  });

  it("stamps each row with its stage", () => {
    const rows = renderSkillWall(SIX).querySelectorAll<HTMLElement>(".skill-wall__row");
    expect(rows[0]!.dataset.stage).toBe("competent");
    expect(rows[1]!.dataset.stage).toBe("locked");
    expect(rows[3]!.dataset.stage).toBe("mastered");
  });

  it("a Mastered skill shows its cited proof and is tappable", () => {
    const mastered = renderSkillWall(SIX).querySelectorAll<HTMLElement>(".skill-wall__row")[3]!;
    const proof = mastered.querySelector(".skill-wall__proof");
    expect(proof).not.toBeNull();
    expect(proof?.textContent).toContain("3"); // live_proof_count
    // tappable → its cited demo (focusable button semantics)
    expect(mastered.getAttribute("role")).toBe("button");
    expect(mastered.getAttribute("tabindex")).toBe("0");
  });

  it("a non-Mastered skill shows NO proof and is not a button (nothing given)", () => {
    const locked = renderSkillWall(SIX).querySelectorAll<HTMLElement>(".skill-wall__row")[1]!;
    expect(locked.querySelector(".skill-wall__proof")).toBeNull();
    // not an activatable button (only Mastered earns that)...
    expect(locked.getAttribute("role")).toBeNull();
    expect(locked.getAttribute("aria-expanded")).toBeNull();
    // ...but SURF-04 makes it keyboard-browsable to read the skill.
    expect(locked.getAttribute("tabindex")).toBe("0");
  });

  it("reflects learn_fill as a proportional bar width", () => {
    const rows = renderSkillWall(SIX).querySelectorAll<HTMLElement>(".skill-wall__row");
    const fill = rows[2]!.querySelector<HTMLElement>(".skill-wall__fill > i");
    expect(fill?.style.width).toBe("70%"); // eq_mixing learn_fill 0.7
  });

  it("with no skills yet, shows an honest empty line, not a blank list", () => {
    const el = renderSkillWall([]);
    expect(el.querySelectorAll(".skill-wall__row").length).toBe(0);
    expect(el.querySelector(".skill-wall__empty")).not.toBeNull();
  });

  it("collapses an all-locked zero-fill snapshot into the same quiet empty state", () => {
    const el = renderSkillWall([
      row({ skill_id: "deck_control" }),
      row({ skill_id: "beatmatching" }),
      row({ skill_id: "eq_mixing" }),
      row({ skill_id: "harmonic_mixing" }),
      row({ skill_id: "transitions" }),
      row({ skill_id: "phrasing_performance" }),
    ]);
    expect(el.querySelectorAll(".skill-wall__row").length).toBe(0);
    expect(el.querySelector(".skill-wall__empty")?.textContent).toContain(
      "Nothing earned yet",
    );
  });

  it("paints the SURF-01 what_remains line on an unfinished skill, none on Mastered", () => {
    const rows = renderSkillWall(SIX).querySelectorAll<HTMLElement>(".skill-wall__row");
    expect(rows[1]!.querySelector(".skill-wall__remains")?.textContent).toBe(
      "Finish the lessons to reach Competent",
    );
    // Mastered carries its proof line, not a "what remains" line (empty string).
    const mastered = renderSkillWall([
      row({ skill_id: "harmonic_mixing", stage: "mastered", mastered: true, what_remains: "" }),
    ]).querySelector<HTMLElement>(".skill-wall__row");
    expect(mastered?.querySelector(".skill-wall__remains")).toBeNull();
  });
});

describe("mountSkillWall — live progress_state subscription", () => {
  it("paints initial rows and repaints on a pushed snapshot", () => {
    const host = document.createElement("div");
    let push: (rows: SkillWallRow[]) => void = () => {};
    const handle = mountSkillWall(host, {
      initialRows: SIX,
      subscribe: (onRows) => {
        push = onRows;
        return () => {};
      },
    });
    expect(host.querySelectorAll(".skill-wall__row").length).toBe(6);

    // a later snapshot flips beatmatching to mastered → repaint reflects it
    push([row({ skill_id: "beatmatching", stage: "mastered", mastered: true, live_proof_count: 3 })]);
    const only = host.querySelectorAll<HTMLElement>(".skill-wall__row");
    expect(only.length).toBe(1);
    expect(only[0]!.dataset.stage).toBe("mastered");

    handle.teardown();
  });
});
