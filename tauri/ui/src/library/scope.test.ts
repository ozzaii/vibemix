// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — radial scope geometry vitest spec.
 *
 * Pure SVG string-building; assert the geometry math (distance = 1−score
 * mapped to radius, deterministic fanned angles, clamping) + the structural
 * contract (range rings + origin ping + one dot per result). No DOM.
 */

import { describe, expect, it } from "vitest";

import type { SearchResult } from "./api.js";
import { plotAngle, plotRadius, renderScope, renderSequenceScope } from "./scope.js";

const RESULT: SearchResult = {
  centered: true,
  corpus_size: 142,
  results: [
    { track_id: "a", title: "A", score: 0.764, meta: "m" },
    { track_id: "b", title: "B", score: 0.4, meta: "m" },
    { track_id: "c", title: "C", score: 0.1, meta: "m" },
  ],
};

describe("plotRadius — closer score = smaller radius", () => {
  it("clamps to the dial bounds [30, 132]", () => {
    expect(plotRadius(1.0, "search")).toBeGreaterThanOrEqual(30);
    expect(plotRadius(0.0, "search")).toBeLessThanOrEqual(132);
    expect(plotRadius(0.0, "similar")).toBeLessThanOrEqual(132);
  });

  it("a higher score plots nearer the origin than a lower one", () => {
    expect(plotRadius(0.764, "search")).toBeLessThan(plotRadius(0.6, "search"));
  });
});

describe("plotAngle — deterministic fan from top of dial", () => {
  it("is stable for the same (i, count)", () => {
    expect(plotAngle(0, 6)).toBe(plotAngle(0, 6));
  });

  it("alternates the parity jitter", () => {
    // even index jitters -0.18, odd +0.18 → distinct angles even at same step base
    expect(plotAngle(0, 6)).not.toBe(plotAngle(1, 6));
  });
});

describe("renderScope — structural contract", () => {
  const svg = renderScope(RESULT, "search");

  it("draws the three range rings with labels", () => {
    expect(svg).toContain(">0.30<");
    expect(svg).toContain(">0.60<");
    expect(svg).toContain(">0.90<");
  });

  it("draws the origin ping + origin dot", () => {
    expect(svg).toContain("vmx-lib-seed-ping");
    expect(svg).toContain("vmx-lib-dot-origin");
  });

  it("plots one near dot for the top neighbour and uses only token colors", () => {
    expect(svg).toContain("vmx-lib-dot-near");
    // no raw hex colors leaked — all geometry references CSS vars / opacity
    expect(svg).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });

  it("handles an empty result set without throwing", () => {
    const empty = renderScope(
      { centered: false, corpus_size: 0, results: [] },
      "search",
    );
    expect(empty).toContain("vmx-lib-dot-origin");
    expect(empty).not.toContain("vmx-lib-dot-near");
  });
});

describe("renderSequenceScope — honest set-order map", () => {
  const svg = renderSequenceScope([
    { track_id: "a", title: "A", meta: "m" },
    { track_id: "b", title: "B", meta: "m" },
    { track_id: "c", title: "C", meta: "m" },
  ]);

  it("plots sequence points without similarity-only rose near dots", () => {
    expect(svg).toContain("vmx-lib-dot-sequence");
    expect(svg).toContain("vmx-lib-sequence-line");
    expect(svg).not.toContain("vmx-lib-dot-near");
    expect(svg).not.toContain("vmx-lib-dot-far");
  });

  it("does not render the query origin or sonar ping for a set", () => {
    expect(svg).not.toContain("vmx-lib-seed-ping");
    expect(svg).not.toContain("vmx-lib-dot-origin");
  });

  it("uses token colors only", () => {
    expect(svg).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });
});
