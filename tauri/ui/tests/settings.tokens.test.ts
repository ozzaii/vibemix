/* Phase 14 Wave 3 — settings-surface migration spec (active).
 *
 * Unskipped by Plan 14-04 once the settings drawer migration to v5
 * primitives landed. Asserts every settings consumer renders free of
 * legacy shim tokens, that the SettingsDrawer ships WITHOUT a
 * .border-anim (2026-05-19 /impeccable critique — sweep is restricted
 * to the session deck only), and that the NEW PerformanceGroup
 * component renders the off/on toggle states with the v5 amber
 * backlight in the on state.
 *
 * Detector reused from tokens.legacy-detect.test.ts so the bash gate and
 * the vitest gate stay byte-aligned (Pitfall 6 — RESEARCH.md).
 */

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

/** Concat the rendered subtree's outerHTML with every <style> block
 * registered on document.head. registerStyle() in src/settings/components/
 * appends a <style> per module; reading all those bodies surfaces the
 * actual CSS strings each component consumes at runtime. */
function renderedHtmlPlusStyles(rendered: HTMLElement): string {
  const styles = Array.from(document.head.querySelectorAll("style"))
    .map((s) => s.textContent ?? "")
    .join("\n");
  return `${rendered.outerHTML}\n${styles}`;
}

describe("settings surface tokens (wave 3)", () => {
  it("SettingsDrawer mount produces no legacy token refs", async () => {
    const { mountSettingsDrawer, _resetDrawerForTests } = await import(
      "../src/settings/SettingsDrawer.js"
    );
    _resetDrawerForTests();
    const host = document.createElement("div");
    document.body.append(host);
    mountSettingsDrawer(host);
    expect(containsLegacyToken(renderedHtmlPlusStyles(host))).toBe(false);
  });

  it("SettingsDrawer ships WITHOUT a .border-anim sweep (one-amber rule)", async () => {
    // 2026-05-19 /impeccable critique fix: DESIGN.md §5 restricts the
    // amber border sweep to the session deck only. Opening the drawer
    // over the session view previously put two concurrent sweeps in the
    // same field plus the drop-chip beat-pulse, the cohost LED, and the
    // meter peak — six+ amber elements competing for attention. The
    // drawer now reads as quiet glass; the only amber on it is the
    // PerformanceGroup toggle on-state.
    const { mountSettingsDrawer, _resetDrawerForTests } = await import(
      "../src/settings/SettingsDrawer.js"
    );
    _resetDrawerForTests();
    const host = document.createElement("div");
    document.body.append(host);
    mountSettingsDrawer(host);
    const drawer = host.querySelector<HTMLElement>("aside.vmx-settings-drawer");
    expect(drawer).not.toBeNull();
    // No descendant carries the border-anim class anywhere in the drawer.
    expect(drawer?.querySelector(".border-anim")).toBeNull();
  });

  it("retention-slider renders without legacy token refs", async () => {
    const { renderRetentionSlider } = await import(
      "../src/settings/components/retention-slider.js"
    );
    const handle = renderRetentionSlider({
      value: 7,
      onChange: () => {},
    });
    document.body.append(handle.root);
    expect(containsLegacyToken(renderedHtmlPlusStyles(handle.root))).toBe(false);
  });

  it("hotkey-capture renders without legacy token refs", async () => {
    const { renderHotkeyCapture } = await import(
      "../src/settings/components/hotkey-capture.js"
    );
    const handle = renderHotkeyCapture({
      value: "cmd+shift+m",
      onCapture: () => {},
    });
    document.body.append(handle.root);
    expect(containsLegacyToken(renderedHtmlPlusStyles(handle.root))).toBe(false);
  });

  it("mascot-group renders without legacy token refs", async () => {
    const { renderMascotGroup } = await import(
      "../src/settings/components/mascot-group.js"
    );
    const el = renderMascotGroup();
    document.body.append(el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(el))).toBe(false);
  });

  it("PerformanceGroup off-state renders without legacy refs + carries off markers", async () => {
    const { PerformanceGroup } = await import(
      "../src/settings/components/performance-group.js"
    );
    const el = PerformanceGroup(false);
    document.body.append(el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(el))).toBe(false);
    const toggle = el.querySelector<HTMLButtonElement>(".vmx-perf-toggle");
    expect(toggle).not.toBeNull();
    expect(toggle?.dataset.on).toBe("false");
    expect(toggle?.getAttribute("aria-checked")).toBe("false");
    expect(toggle?.textContent).toBe("OFF");
  });

  it("PerformanceGroup on-state carries the on markers (amber backlight via data-on)", async () => {
    const { PerformanceGroup } = await import(
      "../src/settings/components/performance-group.js"
    );
    const el = PerformanceGroup(true);
    document.body.append(el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(el))).toBe(false);
    const toggle = el.querySelector<HTMLButtonElement>(".vmx-perf-toggle");
    expect(toggle).not.toBeNull();
    expect(toggle?.dataset.on).toBe("true");
    expect(toggle?.getAttribute("aria-checked")).toBe("true");
    expect(toggle?.textContent).toBe("ON");
    // CSS rule for data-on="true" must reference --amber tokens (mock-
    // verbatim amber backlight gradient) — proves the on-state styling
    // is wired even though jsdom doesn't compute it.
    const styles = Array.from(document.head.querySelectorAll("style"))
      .map((s) => s.textContent ?? "")
      .join("\n");
    expect(styles).toMatch(/\.vmx-perf-toggle\[data-on="true"\][\s\S]*--amber/);
  });

  it("applyBlurPerfPreference writes/clears data-blur-perf on <html>", async () => {
    const { applyBlurPerfPreference } = await import(
      "../src/settings/components/performance-group.js"
    );
    applyBlurPerfPreference(true);
    expect(document.documentElement.getAttribute("data-blur-perf")).toBe("on");
    applyBlurPerfPreference(false);
    expect(document.documentElement.getAttribute("data-blur-perf")).toBeNull();
  });
});
