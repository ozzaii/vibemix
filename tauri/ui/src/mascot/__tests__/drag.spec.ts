/* Phase 57 / POLISH-02a — regression pin for the mascot JS-API drag fallback.
 *
 * VERIFY-AND-HARDEN, not re-implement. The fix pinned here was closed in
 * commit `fac4c4a` and is intact in src/mascot/index.ts.
 *
 * Why a JS fallback exists (per 57-RESEARCH Pattern 3): the HTML
 * `data-tauri-drag-region` attribute is unreliable on transparent +
 * decorations:false macOS windows, so mascot/index.ts attaches an explicit
 * `document` mousedown handler that calls `tauriWin.startDragging()`. This
 * spec fs-reads index.ts and asserts the handler is wired with its two
 * load-bearing guards intact:
 *   - left-click only (`button !== 0` early-return) — drag must NOT fire on
 *     right-click (reserved for a future context menu)
 *   - `[data-no-drag]` opt-out — interactive regions must be exempt
 *
 * Static source-text assertion (no app execution); the real-window drag
 * confirm on Kaan's Mac is KAAN-ACTION (57-01 must_haves.kaan_action).
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const MASCOT_INDEX_TS_PATH = resolve(__dirname, "..", "index.ts");

describe("mascot drag fallback (POLISH-02a — fac4c4a)", () => {
  const src = readFileSync(MASCOT_INDEX_TS_PATH, "utf-8");

  it("registers a document mousedown listener", () => {
    expect(src).toMatch(/document\.addEventListener\(\s*["']mousedown["']/);
  });

  it("calls startDragging() inside the drag handler", () => {
    expect(src).toMatch(/startDragging\(\)/);
  });

  it("guards left-click only (button !== 0 early return)", () => {
    // Without this, right-click would start a drag — the right button is
    // reserved for a future context menu.
    expect(src).toMatch(/\.button\s*!==\s*0/);
  });

  it("honours the [data-no-drag] opt-out for interactive regions", () => {
    expect(src).toMatch(/closest\(\s*["']\[data-no-drag\]["']\s*\)/);
  });
});
