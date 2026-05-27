// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-03 — single source of truth for aria-labels (parity gate).
//
// Phase 91 REVIEW.md WR-02: `src/learn/controllers/_aria-labels.ts` exports
// the ARIA_LABELS table and the file docstring claims it's the "single
// source of truth" for SVG `aria-label` attributes — but no SVG file
// imports it. Each of the 11 SVGs hardcodes its own aria-label strings.
// A future SKU adding a control or renaming a deck would update one side
// only and nothing would fail the build.
//
// This spec closes the loop: for every `<g data-control-id>` in every
// shipped SVG, the rendered aria-label MUST equal ARIA_LABELS[control-id]
// (or, for the jog-touch family, either the `jog_touch:<deck>` or
// `jog_touched:<deck>` variant — both spellings land in the table to
// match the wire-shape vs SVG-id divergence). Any SVG-side hardcoded
// string that drifts from the table fails this gate.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";
import { ARIA_LABELS } from "../../src/learn/controllers/_aria-labels";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const SVG_DIR = path.join(REPO_ROOT, "tauri/ui/src/learn/controllers");

const CONTROLLER_IDS: readonly string[] = [
  "pioneer_ddj_flx4",
  "pioneer_ddj_flx6",
  "pioneer_ddj_flx10",
  "pioneer_ddj_400",
  "pioneer_ddj_1000",
  "pioneer_ddj_sx3",
  "pioneer_xdj_rx3",
  "numark_party_mix_live",
  "hercules_inpulse_300",
  "hercules_inpulse_500",
  // The `_generic` fallback has no data-control-id groups; it's pure
  // labeled-zone text. Skip it in this gate.
];

describe("test_aria_labels_match_table.spec.ts (WR-02 — ARIA_LABELS is the source of truth)", () => {
  for (const controllerId of CONTROLLER_IDS) {
    const svgPath = path.join(SVG_DIR, `${controllerId}.svg.ts`);
    const svgExists = fs.existsSync(svgPath);
    const testFn = svgExists ? it : it.skip;

    testFn(`${controllerId} — every aria-label matches ARIA_LABELS[control-id]`, () => {
      const moduleSource = fs.readFileSync(svgPath, "utf8");
      const m = moduleSource.match(/=\s*`([\s\S]*?)`/);
      const svgString = m?.[1] ?? "";
      const wrapped = svgString.trim().startsWith("<svg")
        ? svgString
        : `<svg xmlns="http://www.w3.org/2000/svg">${svgString}</svg>`;
      const doc = new DOMParser().parseFromString(wrapped, "image/svg+xml");
      const groups = doc.querySelectorAll("[data-control-id]");

      const offenders: string[] = [];
      groups.forEach((g: Element) => {
        const id = g.getAttribute("data-control-id");
        const svgLabel = g.getAttribute("aria-label");
        if (!id) return;
        const tableLabel = ARIA_LABELS[id];
        if (tableLabel === undefined) {
          offenders.push(
            `${id}: SVG has aria-label=${JSON.stringify(
              svgLabel,
            )} but no entry in ARIA_LABELS table`,
          );
          return;
        }
        if (svgLabel !== tableLabel) {
          offenders.push(
            `${id}: SVG aria-label=${JSON.stringify(
              svgLabel,
            )} drifts from ARIA_LABELS=${JSON.stringify(tableLabel)}`,
          );
        }
      });

      expect(offenders, offenders.join("\n")).toEqual([]);
    });
  }
});
