// @ts-nocheck — Wave 0 scaffolding stub. The actual session component
// signatures are still in flux (Wave 2 / Plan 14-03 rewrites this file
// in full when it unskips). Typecheck suppressed here so the wizard-wave
// `npm run build` gate stays green while this spec is dormant.
/* Phase 14 Wave 0 — session-surface migration spec.
 *
 * Currently `describe.skip(...)` — Wave 2 (Plan 14-03) unskips after
 * the live-session migration commits land. Once green, stays green.
 *
 * Imports the session SessionLayout composer plus the titlebar + meter
 * components (the three files with the heaviest legacy-ref counts in
 * the session surface per PATTERNS.md), renders each, and asserts
 * zero legacy shim references in the combined html + stylesheet text.
 *
 * Detector reused from tokens.legacy-detect.test.ts to stay byte-aligned
 * with the bash gate.
 */

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

function renderedHtmlPlusStyles(rendered: HTMLElement): string {
  const styles = Array.from(document.head.querySelectorAll("style"))
    .map((s) => s.textContent ?? "")
    .join("\n");
  return `${rendered.outerHTML}\n${styles}`;
}

// SKIP — Wave 2 (Plan 14-03 session migration) will unskip.
describe.skip("session surface tokens (wave 2 will green this)", () => {
  it("SessionLayout renders without legacy token refs", async () => {
    const { renderSessionFrame, defaultState } = await import(
      "../src/session/SessionLayout.js"
    );
    const rendered = renderSessionFrame(defaultState());
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("Titlebar renders without legacy token refs", async () => {
    const { renderTitlebar } = await import("../src/session/components/titlebar.js");
    const rendered = renderTitlebar({ session: 1, deck: "A", genre: "tech-house" });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("Meter renders without legacy token refs", async () => {
    const { renderMeter } = await import("../src/session/components/meter.js");
    const rendered = renderMeter({ label: "music" });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });
});
