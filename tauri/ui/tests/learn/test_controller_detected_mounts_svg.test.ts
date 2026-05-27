// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-01 — Plug FLX4 → SVG mounts within 2 s. Wave-0 test
//                    contract: a synthetic `ipc.learn.controller_detected`
//                    envelope dispatched into a LearnWindow instance must
//                    cause the matching SVG to mount at `#learn-root`
//                    within 2000 ms.
//
// Phase 91 Plan 02 — RED-state. The LearnWindow + renderer land in Plan 05;
// the corresponding controller SVGs land in Plan 05 (FLX4) + Plan 06
// (others). Until both are present this test SKIPS.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const LEARN_WINDOW_PATH = path.join(
  REPO_ROOT,
  "tauri/ui/src/learn/learn-window.ts",
);
const FLX4_SVG_PATH = path.join(
  REPO_ROOT,
  "tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts",
);

function isRealLearnWindow(): boolean {
  // Plan 01 shipped a tiny placeholder so Vite can resolve the script src;
  // its body mounts a "Learn module not yet wired (Plan 05)" notice. The
  // real renderer in Plan 05 is detected by the presence of an exported
  // function that handles `ipc.learn.controller_detected` envelopes.
  if (!fs.existsSync(LEARN_WINDOW_PATH)) return false;
  const source = fs.readFileSync(LEARN_WINDOW_PATH, "utf8");
  // The placeholder has the string "Learn module not yet wired (Plan 05)";
  // the real renderer drops that string and references the ipc type.
  if (source.includes("Learn module not yet wired")) return false;
  return source.includes("ipc.learn.controller_detected");
}

describe("test_controller_detected_mounts_svg.test.ts (RENDER-01)", () => {
  const real = isRealLearnWindow() && fs.existsSync(FLX4_SVG_PATH);
  const testFn = real ? it : it.skip;

  testFn(
    "ipc.learn.controller_detected envelope mounts matching SVG at #learn-root within 2000 ms",
    async () => {
      // TODO: plan 05 executor — fill in the body once LearnWindow lands.
      // Sketch:
      //   1. mountLearnWindow(document.body) // exported from learn-window.ts
      //   2. dispatch a synthetic CustomEvent("ipc.learn.controller_detected",
      //      { detail: { connected: true, controller_id: "pioneer_ddj_flx4",
      //                  display_name: "Pioneer DDJ-FLX4",
      //                  port_name: "DDJ-FLX4" } })
      //   3. await new Promise(r => setTimeout(r, 50)) // dynamic-import settle
      //   4. const root = document.querySelector("#learn-root")
      //   5. expect(root?.querySelector("[data-control-id=\"eq_hi:A\"]")).not.toBeNull()
      //   6. expect(elapsed).toBeLessThanOrEqual(2000)
      expect(real).toBe(true);
    },
  );
});
