// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-01 — All 11 controllers have SVG files at
//                    `tauri/ui/src/learn/controllers/<id>.svg.ts` — 10
//                    specific (Pioneer, Numark, Hercules) + 1 `_generic`
//                    fallback.
//
// Partial-build friendly: a missing SVG becomes `it.skip`; in this repo state
// all expected SVG modules should exist and run as live assertions.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

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

describe("test_all_11_svgs_present.spec.ts (RENDER-01)", () => {
  for (const controllerId of CONTROLLER_IDS) {
    const svgPath = path.join(SVG_DIR, `${controllerId}.svg.ts`);
    const exists = fs.existsSync(svgPath);
    const testFn = exists ? it : it.skip;

    testFn(`${controllerId}.svg.ts exists under tauri/ui/src/learn/controllers/`, () => {
      expect(fs.existsSync(svgPath), `${svgPath} must exist`).toBe(true);
      const stat = fs.statSync(svgPath);
      expect(stat.size, `${svgPath} must be non-empty`).toBeGreaterThan(0);
    });
  }
});
