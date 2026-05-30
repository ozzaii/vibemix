// SPDX-License-Identifier: Apache-2.0
// SURF-02 — the Competent-stage fill renders with a QUIET, satisfying cue: no
// slop, no spam, no constant celebration. The fill animates once and settles; it
// does NOT fire a co-host vocal or pop a loud modal. This pin regression-locks the
// Earned Wall as a read-only render (the co-host voice is reserved for the single,
// rare, grounded Mastered unlock — SURF-03 — which lives in the Python credit site,
// never here).
import { describe, it, expect, vi } from "vitest";
import {
  renderSkillWall,
  mountSkillWall,
  type SkillWallRow,
} from "../../src/learn/SkillWall.js";

function row(over: Partial<SkillWallRow>): SkillWallRow {
  return {
    skill_id: "eq_mixing",
    stage: "locked",
    learn_fill: 0,
    competent: false,
    live_proof_count: 0,
    mastered: false,
    first_mastered_at: null,
    what_remains: "",
    ...over,
  };
}

describe("SURF-02 — quiet Competent-fill cue", () => {
  it("a Competent fill is a bar width only — no modal, no dialog, no celebration node", () => {
    const el = renderSkillWall([
      row({ skill_id: "eq_mixing", stage: "competent", competent: true, learn_fill: 0.7 }),
    ]);
    const bar = el.querySelector<HTMLElement>(".skill-wall__fill > i");
    expect(bar?.style.width).toBe("70%"); // the cue IS the fill, nothing louder
    expect(el.querySelector("[role=dialog]")).toBeNull();
    expect(el.querySelector(".modal")).toBeNull();
    expect(el.querySelector(".celebration")).toBeNull();
    expect(el.querySelector(".skill-wall__vocal")).toBeNull();
  });

  it("rendering/advancing a Competent row dispatches NO cohost-reaction event", () => {
    const reaction = vi.fn();
    window.addEventListener("cohost-reaction", reaction);
    const host = document.createElement("div");
    const handle = mountSkillWall(host, {
      initialRows: [row({ stage: "competent", competent: true, learn_fill: 0.6 })],
    });
    // a later snapshot advances the fill — still silent (no spam on every notch)
    handle.update([row({ stage: "competent", competent: true, learn_fill: 1 })]);
    expect(reaction).not.toHaveBeenCalled();
    window.removeEventListener("cohost-reaction", reaction);
    handle.teardown();
  });

  it("a Competent row is NOT an activatable button (only Mastered earns that)", () => {
    const el = renderSkillWall([
      row({ skill_id: "eq_mixing", stage: "competent", competent: true, learn_fill: 1 }),
    ]);
    const competent = el.querySelector<HTMLElement>(".skill-wall__row")!;
    expect(competent.getAttribute("role")).toBeNull();
    expect(competent.getAttribute("aria-expanded")).toBeNull();
  });
});
