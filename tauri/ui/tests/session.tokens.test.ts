/* Phase 14 Wave 2 — session-surface migration spec (active).
 *
 * Unskipped by Plan 14-03 once the live-session migration to v5 primitives
 * landed. Asserts every session consumer renders free of legacy shim
 * tokens AND that SessionLayout has `.border-anim` as its first child
 * (the load-bearing structural invariant per UI-SPEC §Surface 2).
 *
 * Detector reused from tokens.legacy-detect.test.ts so the bash gate and
 * the vitest gate stay byte-aligned (Pitfall 6 — RESEARCH.md).
 */

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

/** Concat the rendered subtree's outerHTML with every <style> block
 * registered on document.head. registerStyle() in src/session/components/
 * appends a <style> per module; reading all those bodies surfaces the
 * actual CSS strings each component consumes at runtime. */
function renderedHtmlPlusStyles(rendered: HTMLElement): string {
  const styles = Array.from(document.head.querySelectorAll("style"))
    .map((s) => s.textContent ?? "")
    .join("\n");
  return `${rendered.outerHTML}\n${styles}`;
}

describe("session surface tokens (wave 2)", () => {
  it("SessionLayout renders without legacy token refs", async () => {
    const { mountSessionLayout } = await import(
      "../src/session/SessionLayout.js"
    );
    const host = document.createElement("div");
    document.body.append(host);
    const mounted = mountSessionLayout(host);
    expect(containsLegacyToken(renderedHtmlPlusStyles(mounted.root))).toBe(
      false,
    );
  });

  it("SessionLayout has .border-anim as its first child", async () => {
    const { mountSessionLayout } = await import(
      "../src/session/SessionLayout.js"
    );
    const host = document.createElement("div");
    document.body.append(host);
    const mounted = mountSessionLayout(host);
    expect(mounted.root.firstElementChild?.classList.contains("border-anim"))
      .toBe(true);
  });

  it("Titlebar renders without legacy token refs", async () => {
    const { renderTitlebar } = await import(
      "../src/session/components/titlebar.js"
    );
    const rendered = renderTitlebar({
      live: "ok",
      rec: "off",
      sys: "ok",
      clock: "00:00:00",
    });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("Meter renders without legacy token refs", async () => {
    const { renderMeter } = await import(
      "../src/session/components/meter.js"
    );
    const rendered = renderMeter({ label: "music" });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("CohostPanel renders without legacy token refs", async () => {
    const { renderCohostPanel } = await import(
      "../src/session/components/cohost.js"
    );
    const rendered = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: false,
    });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("DropChip renders without legacy token refs", async () => {
    const { renderDropChip } = await import(
      "../src/session/components/drop-chip.js"
    );
    const rendered = renderDropChip({ bars: 4, bpmPeriodMs: 500 });
    expect(rendered).not.toBeNull();
    if (!rendered) return;
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });
});
