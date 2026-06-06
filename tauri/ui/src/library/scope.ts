// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — radial "vibe scope" SVG renderer.
 *
 * An instrument scope, not a chart: concentric range rings (0.30 / 0.60 / 0.90
 * vibe distance), a crosshair, the query/seed at the origin with a sonar ping,
 * and each pulled track plotted by distance = (1 − score) along a deterministic
 * angle (index-fanned so the same result set always lays out the same way).
 *
 * Pure string-building of SVG inner markup (no DOM mutation here) so it's
 * trivially testable; index.ts assigns the returned string to `svg.innerHTML`.
 * Colors come from tokens.css CSS vars (no hardcoded hexes) — the renderer only
 * positions geometry.
 */

import type { SearchResult, TrackResult } from "./api.js";
import type { LibraryMode } from "./state-machine.js";

const CX = 150;
const CY = 150;

const RINGS: ReadonlyArray<{ r: number; label: string }> = [
  { r: 42, label: "0.30" },
  { r: 84, label: "0.60" },
  { r: 126, label: "0.90" },
];

const RADIUS_MIN = 30;
const RADIUS_MAX = 132;
/** How many of the nearest plotted tracks get the brightest rose treatment. */
const NEAR_COUNT = 3;

/** Map a track's score → a plotted radius from the origin.
 *
 * distance = 1 − score (closer = more similar). The two modes occupy different
 * score bands (search ~0.7 → dist ~0.25; centered-similar ~0.3 → dist ~0.7), so
 * the radius scale is per-mode (matching the mock) to keep both legible.
 */
export function plotRadius(score: number, mode: LibraryMode): number {
  const dist = 1 - score;
  const base = mode === "similar" ? 0.6 : 0.2;
  const gain = mode === "similar" ? 210 : 330;
  const r = 42 + (dist - base) * gain;
  return Math.max(RADIUS_MIN, Math.min(RADIUS_MAX, r));
}

/** Deterministic angle for the i-th neighbour (even fan + a small parity jitter
 *  so neighbours never collinearly overlap). Top of the dial is −π/2. */
export function plotAngle(i: number, count: number): number {
  const step = count > 0 ? (2 * Math.PI) / count : 0;
  return -Math.PI / 2 + i * step + (i % 2 ? 0.18 : -0.18);
}

/** Build the scope SVG inner markup for a result set. */
export function renderScope(result: SearchResult, mode: LibraryMode): string {
  const rows: TrackResult[] = result.results;
  let h = "";

  // Concentric range rings + ring labels (instrument dial).
  for (const rg of RINGS) {
    h += `<circle cx="${CX}" cy="${CY}" r="${rg.r}" fill="none" stroke="var(--silk-12)"/>`;
    h += `<text class="vmx-lib-ringlabel" x="${CX + 4}" y="${CY - rg.r + 11}">${rg.label}</text>`;
  }

  // Crosshair.
  h += `<line x1="${CX}" y1="14" x2="${CX}" y2="286" stroke="var(--silk-12)" stroke-opacity="0.5"/>`;
  h += `<line x1="14" y1="${CY}" x2="286" y2="${CY}" stroke="var(--silk-12)" stroke-opacity="0.5"/>`;

  // Neighbours — radial spokes + dots.
  rows.forEach((r, i) => {
    const rr = plotRadius(r.score, mode);
    const ang = plotAngle(i, rows.length);
    const x = CX + Math.cos(ang) * rr;
    const y = CY + Math.sin(ang) * rr;
    const near = i < NEAR_COUNT;
    const spoke = near ? "var(--brand-22)" : "var(--brand-08)";
    h += `<line x1="${CX}" y1="${CY}" x2="${x.toFixed(2)}" y2="${y.toFixed(2)}" stroke="${spoke}"/>`;
    if (near) {
      h += `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="4.8" fill="var(--brand-glow)" class="vmx-lib-dot-near"/>`;
    } else {
      h += `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="3.7" fill="var(--brand-40)" class="vmx-lib-dot-far"/>`;
    }
  });

  // Origin (query/seed) with sonar ping.
  h += `<circle class="vmx-lib-seed-ping" cx="${CX}" cy="${CY}" r="3" fill="none" stroke="var(--brand)"/>`;
  h += `<circle cx="${CX}" cy="${CY}" r="4.8" fill="var(--brand)" class="vmx-lib-dot-origin"/>`;

  return h;
}
