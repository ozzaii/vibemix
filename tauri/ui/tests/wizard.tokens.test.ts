/* Phase 14 Wave 0 — wizard-surface migration spec.
 *
 * Currently `describe.skip(...)` — Wave 1 (Plan 14-02) unskips after
 * the wizard surface migration commits land. Once green, this spec
 * stays green for the rest of the phase.
 *
 * Renders the two heaviest-token-reference wizard components
 * (primary-panel and window-picker — together they hold ~40 of the
 * wizard's 139 legacy refs) and asserts the rendered HTML +
 * registered stylesheet text is free of legacy shim tokens.
 *
 * Detector reused from tokens.legacy-detect.test.ts so the bash gate
 * and the vitest gate stay byte-aligned.
 */

import { describe, expect, it } from "vitest";

import { containsLegacyToken } from "./tokens.legacy-detect.test.js";

/** Concat the rendered subtree's outerHTML with every <style> block
 * the test harness registered. registerStyle() in src/wizard/components/
 * appends a `<style>` to document.head; reading all those bodies surfaces
 * the CSS strings that components actually consume at runtime. */
function renderedHtmlPlusStyles(rendered: HTMLElement): string {
  const styles = Array.from(document.head.querySelectorAll("style"))
    .map((s) => s.textContent ?? "")
    .join("\n");
  return `${rendered.outerHTML}\n${styles}`;
}

// SKIP — Wave 1 (Plan 14-02 wizard migration) will remove the `.skip` to
// activate this gate. Until then it would FAIL because the current wizard
// components legitimately consume shim aliases via the cascade.
describe.skip("wizard surface tokens (wave 1 will green this)", () => {
  it("PrimaryPanel renders without legacy token refs", async () => {
    const { PrimaryPanel } = await import("../src/wizard/components/primary-panel.js");
    const child = document.createElement("div");
    child.textContent = "child";
    const rendered = PrimaryPanel({ header: "TEST", children: child });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("WindowPicker renders without legacy token refs", async () => {
    const { WindowPicker } = await import("../src/wizard/components/window-picker.js");
    const rendered = WindowPicker({
      mode: "hint",
      onPick: () => {},
    } as Parameters<typeof WindowPicker>[0]);
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });
});
