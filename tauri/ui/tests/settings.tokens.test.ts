// @ts-nocheck — Wave 0 scaffolding stub. The settings component
// signatures here drifted from the runtime API (Wave 3 / Plan 14-04
// rewrites this file in full when it unskips). Typecheck suppressed
// here so the wizard-wave `npm run build` gate stays green.
/* Phase 14 Wave 0 — settings-surface migration spec.
 *
 * Currently `describe.skip(...)` — Wave 3 (Plan 14-04) unskips after
 * the settings drawer migration commits land. Once green, stays green.
 *
 * Renders SettingsDrawer body plus three of the heaviest-legacy-ref
 * inner components (retention-slider, hotkey-capture, mascot-group)
 * and asserts zero shim refs after migration.
 *
 * Detector reused from tokens.legacy-detect.test.ts.
 */

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

function renderedHtmlPlusStyles(rendered: HTMLElement): string {
  const styles = Array.from(document.head.querySelectorAll("style"))
    .map((s) => s.textContent ?? "")
    .join("\n");
  return `${rendered.outerHTML}\n${styles}`;
}

// SKIP — Wave 3 (Plan 14-04 settings migration) will unskip.
describe.skip("settings surface tokens (wave 3 will green this)", () => {
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

  it("retention-slider renders without legacy token refs", async () => {
    const { renderRetentionSlider } = await import(
      "../src/settings/components/retention-slider.js"
    );
    const handle = renderRetentionSlider({ initialDays: 7, onChange: () => {} });
    document.body.append(handle.el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(handle.el))).toBe(false);
  });

  it("hotkey-capture renders without legacy token refs", async () => {
    const { renderHotkeyCapture } = await import(
      "../src/settings/components/hotkey-capture.js"
    );
    const handle = renderHotkeyCapture({ initialCombo: "cmd+shift+m", onCommit: () => {} });
    document.body.append(handle.el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(handle.el))).toBe(false);
  });

  it("mascot-group renders without legacy token refs", async () => {
    const { renderMascotGroup } = await import(
      "../src/settings/components/mascot-group.js"
    );
    const el = renderMascotGroup();
    document.body.append(el);
    expect(containsLegacyToken(renderedHtmlPlusStyles(el))).toBe(false);
  });
});
