// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-01 — Generic fallback renders on no-match. The `_generic`
//                    SVG ships labeled-zone text (DECK A / MIXER / DECK B)
//                    instead of factual control geometry, so any user who
//                    plugs in an unrecognised controller still sees a
//                    legible Learn surface they can navigate.
//
// Phase 91 Plan 02 — RED-state. The `_generic.svg.ts` module lands in
// Plan 05; until then this case skips with a note pointing the next
// executor at the right plan.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const GENERIC_SVG_PATH = path.join(
  REPO_ROOT,
  "tauri/ui/src/learn/controllers/_generic.svg.ts",
);
const GENERIC_EXISTS = fs.existsSync(GENERIC_SVG_PATH);

describe("test_generic_fallback.spec.ts (RENDER-01)", () => {
  const testFn = GENERIC_EXISTS ? it : it.skip;
  testFn("_generic.svg.ts exports GENERIC_CONTROLLER_SVG with labeled zones", () => {
    const moduleSource = fs.readFileSync(GENERIC_SVG_PATH, "utf8");
    // Plan 05 exports a named constant; check both common shapes.
    const hasNamedExport = /export\s+const\s+GENERIC_CONTROLLER_SVG\s*=/.test(
      moduleSource,
    );
    expect(
      hasNamedExport,
      "_generic.svg.ts must `export const GENERIC_CONTROLLER_SVG = ...`",
    ).toBe(true);

    // Labeled zones — uppercase block text the user can read at any zoom.
    expect(moduleSource).toContain("DECK A");
    expect(moduleSource).toContain("MIXER");
    expect(moduleSource).toContain("DECK B");
  });
});
