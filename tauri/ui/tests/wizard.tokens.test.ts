/* Phase 14 Wave 1 — wizard-surface migration spec (active).
 *
 * Unskipped by Plan 14-02 once the wizard surface migrated to v5
 * primitives. The spec stays green for the rest of the phase.
 *
 * Renders the heaviest-token-reference wizard components (primary-panel,
 * window-picker, controller-probe, dropdown-device) and asserts the
 * rendered HTML + registered stylesheet text is free of legacy shim
 * tokens.
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

describe("wizard surface tokens (wave 1)", () => {
  it("PrimaryPanel renders without legacy token refs", async () => {
    const { PrimaryPanel } = await import("../src/wizard/components/primary-panel.js");
    const child = document.createElement("div");
    child.textContent = "child";
    const rendered = PrimaryPanel({ header: "TEST", children: child });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  // Critique 2026-05-14: PrimaryPanel no longer carries `.border-anim`.
  // The "one CDJ, one breathing light" rule restricts the perimeter
  // sweep to the session deck only (cohost wraps it via SessionLayout
  // — see session.tokens.test.ts). Wizard panels read quiet.
  it("PrimaryPanel has NO .border-anim (sign-of-life restricted to session deck)", async () => {
    const { PrimaryPanel } = await import("../src/wizard/components/primary-panel.js");
    const child = document.createElement("div");
    child.textContent = "child";
    const rendered = PrimaryPanel({ children: child });
    expect(rendered.querySelector(".border-anim")).toBeNull();
  });

  it("PrimaryPanel composes the shared .vmx-tile glass-tile shell with hero density", async () => {
    const { PrimaryPanel } = await import("../src/wizard/components/primary-panel.js");
    const child = document.createElement("div");
    child.textContent = "child";
    const rendered = PrimaryPanel({ children: child });
    expect(rendered.classList.contains("vmx-tile")).toBe(true);
    expect(rendered.dataset.tile).toBe("hero");
  });

  it("WindowPicker renders without legacy token refs", async () => {
    const { WindowPicker } = await import("../src/wizard/components/window-picker.js");
    const rendered = WindowPicker({
      mode: "hint",
      detectedHint: { appName: "djay Pro", windowTitle: "main" },
      onSelect: () => {},
      onPickDifferent: () => {},
    });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("ControllerProbe renders without legacy token refs", async () => {
    const { ControllerProbe } = await import("../src/wizard/components/controller-probe.js");
    const rendered = ControllerProbe({
      state: "listening",
      secondsLeft: 10,
      onListenAgain: () => {},
      onSkip: () => {},
    });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });

  it("DropdownDevice renders without legacy token refs", async () => {
    const { DropdownDevice } = await import("../src/wizard/components/dropdown-device.js");
    const rendered = DropdownDevice({
      devices: [{ id: "dev1", name: "Built-in Output", isSpeaker: true }],
      onSelect: () => {},
    });
    document.body.append(rendered);
    expect(containsLegacyToken(renderedHtmlPlusStyles(rendered))).toBe(false);
  });
});
