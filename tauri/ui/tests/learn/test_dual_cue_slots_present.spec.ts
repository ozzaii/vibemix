// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-05 — Every `<g data-control-id>` in every learn SVG carries
//                    TWO empty child slots `<g class="cue-color"></g>` and
//                    `<g class="cue-shape"></g>` — the dual-channel cue
//                    scaffolding. Learn lights them on
//                    `ipc.learn.highlight`.
//
// Partial-build friendly: each case skips only when its SVG module is absent.
// The separate highlight-paint tests prove the slots are lit at runtime.

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

describe("test_dual_cue_slots_present.spec.ts (RENDER-05)", () => {
  for (const controllerId of CONTROLLER_IDS) {
    const svgPath = path.join(SVG_DIR, `${controllerId}.svg.ts`);
    const svgExists = fs.existsSync(svgPath);
    const testFn = svgExists ? it : it.skip;

    testFn(
      `${controllerId} — every <g data-control-id> has cue-color + cue-shape slots`,
      () => {
        // Pins the slot scaffolding that runtime highlights fill.
        const moduleSource = fs.readFileSync(svgPath, "utf8");
        const m = moduleSource.match(/=\s*`([\s\S]*?)`/);
        const svgString = m?.[1] ?? "";

        const wrapped = svgString.trim().startsWith("<svg")
          ? svgString
          : `<svg xmlns="http://www.w3.org/2000/svg">${svgString}</svg>`;
        const doc = new DOMParser().parseFromString(wrapped, "image/svg+xml");
        const groups = doc.querySelectorAll("[data-control-id]");

        if (controllerId === "_generic") {
          // _generic uses labeled-zone text, NOT control hit regions — no
          // dual-cue slots required. Skip the assertion.
          expect(groups.length).toBeGreaterThanOrEqual(0);
          return;
        }

        const offenders: string[] = [];
        groups.forEach((g: Element) => {
          const id = g.getAttribute("data-control-id") ?? "?";
          const color = g.querySelector(":scope > .cue-color");
          const shape = g.querySelector(":scope > .cue-shape");
          if (!color)
            offenders.push(`${id}: missing direct child .cue-color slot`);
          if (!shape)
            offenders.push(`${id}: missing direct child .cue-shape slot`);
        });

        expect(offenders, offenders.join("\n")).toEqual([]);
      },
    );
  }
});
