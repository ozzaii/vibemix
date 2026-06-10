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

import { describe, expect, it, vi } from "vitest";

// The SettingsDrawer mounts the staleness banner + profile panel, which call
// the real Tauri event/IPC APIs. In jsdom `window.__TAURI_INTERNALS__` is
// undefined, so the real `listen` throws an unhandled rejection
// ("Cannot read properties of undefined (reading 'transformCallback')").
// Mock the IPC layer (and the Tauri primitives the drawer imports directly)
// to a noop — same pattern as tests/settings/drawer.spec.ts.
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => undefined),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));
vi.mock("../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async () => undefined),
  subscribeIpc: vi.fn(async () => () => {}),
  sendIpcRequest: vi.fn(() => new Promise(() => undefined)),
}));

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

  it("PerformanceGroup off-state renders the OFF|ON rocker with OFF active", async () => {
    const { PerformanceGroup } = await import(
      "../src/settings/components/performance-group.js"
    );
    const el = PerformanceGroup(false);
    document.body.append(el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(el))).toBe(false);
    // One boolean vocabulary across the drawer: the recessed rocker, not a
    // bespoke chip whose label IS the state.
    const rocker = el.querySelector<HTMLElement>('.vmx-rocker[aria-label="lighter blur"]');
    expect(rocker).not.toBeNull();
    const active = rocker?.querySelector<HTMLElement>('.vmx-rocker__seg[data-active="true"]');
    expect(active?.dataset.id).toBe("off");
    expect(active?.getAttribute("aria-checked")).toBe("true");
  });

  it("PerformanceGroup on-state lights the ON segment; clicking OFF applies locally", async () => {
    const { PerformanceGroup } = await import(
      "../src/settings/components/performance-group.js"
    );
    const el = PerformanceGroup(true);
    document.body.append(el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(el))).toBe(false);
    const activeOn = el.querySelector<HTMLElement>('.vmx-rocker__seg[data-active="true"]');
    expect(activeOn?.dataset.id).toBe("on");
    // Optimistic repaint + local-first apply: clicking OFF flips the lit
    // segment and clears data-blur-perf on <html> before any ipc ack.
    document.documentElement.setAttribute("data-blur-perf", "on");
    el.querySelector<HTMLButtonElement>('.vmx-rocker__seg[data-id="off"]')?.click();
    expect(
      el.querySelector<HTMLElement>('.vmx-rocker__seg[data-active="true"]')?.dataset.id,
    ).toBe("off");
    expect(document.documentElement.getAttribute("data-blur-perf")).toBeNull();
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
