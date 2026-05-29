// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-03 — Every `<g data-control-id>` in every learn SVG carries
//                    `role="button"` AND a non-empty `aria-label`. Pins the
//                    a11y scaffolding the keyboard-nav + screen-reader tests
//                    depend on.
// Partial-build friendly: each case skips only when its SVG module is absent.
// In this repo state, all 11 controller SVGs should run as live assertions.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

// vitest's `environmentMatchGlobs` maps tests/**/*.spec.ts → jsdom, so
// `document` + `DOMParser` are both available here without importing
// jsdom directly.
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
  "_generic",
];

describe("test_aria_labels_present.spec.ts (RENDER-03)", () => {
  for (const controllerId of CONTROLLER_IDS) {
    const svgPath = path.join(SVG_DIR, `${controllerId}.svg.ts`);
    const svgExists = fs.existsSync(svgPath);
    const testFn = svgExists ? it : it.skip;

    testFn(`${controllerId} — every <g data-control-id> has role + aria-label`, () => {
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
        const id = g.getAttribute("data-control-id") ?? "?";
        const role = g.getAttribute("role");
        const ariaLabel = g.getAttribute("aria-label");
        if (role !== "button") {
          offenders.push(`${id}: role=${JSON.stringify(role)} (want "button")`);
        }
        if (!ariaLabel || ariaLabel.trim() === "") {
          offenders.push(`${id}: aria-label is missing or empty`);
        }
      });

      expect(offenders, offenders.join("\n")).toEqual([]);
    });
  }
});
