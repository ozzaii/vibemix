/* Phase 14 Plan 14-05 (Wave 4) — mascot overlay window chrome spec.
 *
 * Wave 0 (Plan 14-01) seeded this file as describe.skip. Wave 4 (this
 * plan) unskips after the chrome wrapper lands on mascot.html +
 * src/mascot/chrome.css + the resolveCssColor migration on
 * src/mascot/index.ts.
 *
 * Reads tauri/ui/mascot.html + tauri/ui/src/mascot/chrome.css +
 * tauri/ui/src/mascot/index.ts via fs.readFileSync, parses HTML with
 * jsdom's DOMParser, and asserts:
 *   (a) <body> contains a `.mascot-window` element
 *   (b) `.mascot-window > .border-anim.slow.rev` is the first child
 *   (c) mascot.html references tokens.css via <link rel="stylesheet">
 *       OR inlines the v5 vars in a <style> block (acceptable per the
 *       Wave-0 spec sketch — current Wave 4 implementation uses <link>)
 *   (d) inline <style> overrides body background to transparent !important
 *   (e) the parsed HTML is free of legacy shim tokens
 *   (f) chrome.css uses --glass-3 + --blur-glass-display + --glass-edge
 *       + border-radius: 8px (the wrapper anatomy from 14-PATTERNS.md
 *       Surface 4)
 *   (g) mascot/index.ts contains the 3 v5 resolveCssColor calls and the
 *       3 v5 hex fallbacks, and carries zero legacy --phosphor / #ffa12e
 *       strings (audit gate — the 3 hex literals at the resolveCssColor
 *       sites are the only hex literals permitted outside tokens.css)
 *
 * Detector reused from tokens.legacy-detect.test.ts. */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

const TAURI_UI_ROOT = resolve(__dirname, "..");
const MASCOT_HTML_PATH = resolve(TAURI_UI_ROOT, "mascot.html");
const MASCOT_CHROME_CSS_PATH = resolve(
  TAURI_UI_ROOT,
  "src",
  "mascot",
  "chrome.css",
);
const MASCOT_INDEX_TS_PATH = resolve(
  TAURI_UI_ROOT,
  "src",
  "mascot",
  "index.ts",
);

describe("mascot overlay chrome (Wave 4 — 14-05)", () => {
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

  it("overrides body background to transparent !important", () => {
    // Phase 13 transparent-overlay invariant: tokens.css ships a v5
    // cinematic body background that would opaque-out the desktop
    // composition path. mascot.html MUST override.
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    expect(src).toMatch(/background:\s*transparent\s*!important/);
  });

  it("disables body::before film-grain layer (no full-rect overlay)", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    expect(src).toMatch(/body::before\s*\{[^}]*display:\s*none\s*!important/);
  });

  it("renders top + bottom silkscreen caption mounts", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    document.documentElement.innerHTML = src;
    expect(document.querySelector(".mascot-window__caption")).toBeTruthy();
    expect(document.querySelector(".mascot-window__state-caption")).toBeTruthy();
  });

  it("is free of legacy shim tokens", () => {
    const src = readFileSync(MASCOT_HTML_PATH, "utf-8");
    expect(containsLegacyToken(src)).toBe(false);
  });

  describe("src/mascot/chrome.css — wrapper anatomy", () => {
    // v0.1.0-rc1 dev session 2026-05-13 stripped the mascot chrome
    // rectangle entirely (background: transparent, no border, no
    // box-shadow). The mascot is now a bare 3D character floating
    // over the desktop — Kaan's feedback was that the chrome read as
    // a generic "video preview window" overlay. The previous test
    // pinned the old chrome anatomy; this version pins the bare
    // shape the de-chrome left behind.
    it("declares a transparent .mascot-window with no chrome border", () => {
      const css = readFileSync(MASCOT_CHROME_CSS_PATH, "utf-8");
      const block = css.match(/\.mascot-window\s*\{[^}]+\}/);
      expect(block).toBeTruthy();
      expect(block![0]).toMatch(/background:\s*transparent/);
      expect(block![0]).toMatch(/border:\s*none/);
      expect(block![0]).toMatch(/box-shadow:\s*none/);
    });

    it("declares .mascot-window with position: relative + overflow: hidden", () => {
      // Position required for absolute-positioned canvas child; overflow
      // bounds the scene.
      const css = readFileSync(MASCOT_CHROME_CSS_PATH, "utf-8");
      const block = css.match(/\.mascot-window\s*\{[^}]+\}/);
      expect(block).toBeTruthy();
      expect(block![0]).toMatch(/position:\s*relative/);
      expect(block![0]).toMatch(/overflow:\s*hidden/);
    });

    it("is free of legacy shim tokens", () => {
      const css = readFileSync(MASCOT_CHROME_CSS_PATH, "utf-8");
      expect(containsLegacyToken(css)).toBe(false);
    });
  });

  describe("src/mascot/index.ts — resolveCssColor v5 migration", () => {
    it("calls resolveCssColor with v5 token names (--amber, --silk)", () => {
      // WR-02 in 14-REVIEW.md: coach mood no longer routes through
      // resolveCssColor("--silk-40", ...). --silk-40 carries an alpha
      // channel that THREE.Color silently drops, collapsing coach's
      // particle puff to the same RGB as teacher's --silk. The coach
      // branch now constructs `new Color("#3d424c")` directly. We still
      // assert the two well-behaved token resolutions here.
      const ts = readFileSync(MASCOT_INDEX_TS_PATH, "utf-8");
      expect(ts).toMatch(/resolveCssColor\(["']--amber["']/);
      expect(ts).toMatch(/resolveCssColor\(["']--silk["']/);
    });

    it("uses v5 hex literals (#ff8a3d, #d6cfc7, #3d424c) — the only 3 hex literals outside tokens.css", () => {
      // #ff8a3d + #d6cfc7 are resolveCssColor fallbacks (CSS-resolution
      // failure path). #3d424c is the coach-branch direct constructor
      // argument — load-bearing for visual distinction from teacher.
      const ts = readFileSync(MASCOT_INDEX_TS_PATH, "utf-8");
      expect(ts).toContain("#ff8a3d");
      expect(ts).toContain("#d6cfc7");
      expect(ts).toContain("#3d424c");
    });

    it("carries zero stale --phosphor references or #ffa12e hex", () => {
      const ts = readFileSync(MASCOT_INDEX_TS_PATH, "utf-8");
      expect(ts).not.toMatch(/--phosphor/);
      expect(ts).not.toContain("#ffa12e");
    });

    it("is free of legacy shim tokens", () => {
      const ts = readFileSync(MASCOT_INDEX_TS_PATH, "utf-8");
      expect(containsLegacyToken(ts)).toBe(false);
    });
  });
});
