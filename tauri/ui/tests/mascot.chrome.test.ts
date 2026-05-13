/* Phase 14 Wave 0 — mascot overlay window chrome spec.
 *
 * Currently `describe.skip(...)` — Wave 4 (Plan 14-05) unskips after
 * the mascot overlay v5 chrome lands. Once green, stays green.
 *
 * Reads tauri/ui/mascot.html via fs.readFileSync, parses with the
 * jsdom-provided DOMParser, and asserts:
 *   (a) <body> contains a `.mascot-window` element
 *   (b) `.mascot-window > .border-anim.slow.rev` is the first child
 *   (c) mascot.html references tokens.css via <link rel="stylesheet">
 *       OR inlines the v5 vars in a <style> block
 *   (d) the parsed HTML is free of legacy shim tokens
 *
 * Detector reused from tokens.legacy-detect.test.ts.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

const MASCOT_HTML_PATH = resolve(__dirname, "..", "mascot.html");

// SKIP — Wave 4 (Plan 14-05 mascot chrome) will unskip.
describe.skip("mascot overlay chrome (wave 4 will green this)", () => {
  it("contains a .mascot-window root", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    document.documentElement.innerHTML = src;
    const window = document.querySelector(".mascot-window");
    expect(window).toBeTruthy();
  });

  it("has .border-anim.slow.rev as the first child of .mascot-window", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    document.documentElement.innerHTML = src;
    const window = document.querySelector(".mascot-window");
    expect(window).toBeTruthy();
    const firstChild = window!.firstElementChild;
    expect(firstChild?.classList.contains("border-anim")).toBe(true);
    expect(firstChild?.classList.contains("slow")).toBe(true);
    expect(firstChild?.classList.contains("rev")).toBe(true);
  });

  it("references tokens.css via <link> OR inlines v5 vars in <style>", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    const hasLink = /<link[^>]+href=["'][^"']*tokens\.css["']/.test(src);
    const hasInlineV5 =
      /--glass-3\s*:/.test(src) &&
      /--amber\s*:/.test(src) &&
      /--silk-40\s*:/.test(src);
    expect(hasLink || hasInlineV5).toBe(true);
  });

  it("is free of legacy shim tokens", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    expect(containsLegacyToken(src)).toBe(false);
  });
});
