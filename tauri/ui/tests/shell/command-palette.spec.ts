/**
 * @vitest-environment jsdom
 *
 * The Cmd+K palette is the keyboard-first way to reach any surface or command.
 * A premium palette (Raycast, Linear, Things) TEACHES its shortcuts: every row
 * surfaces its accelerator, right-aligned, so the palette doubles as the
 * shortcut cheat-sheet. This contract locks two things the first cut muddled:
 *   1. the surface "Go to …" rows expose their 1–5 accelerator (they dropped it
 *      before — the sidebar showed it, the palette didn't), and
 *   2. the descriptive subtitle and the accelerator live in SEPARATE slots
 *      (before, a description and a keybind shared one overloaded `hint` slot).
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";
import { SURFACES } from "../../src/shell/surfaces.js";

let shell: MountedShell | null = null;
let host: HTMLElement;

function openPalette(): HTMLElement {
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }));
  return host.querySelector<HTMLElement>(".shell-palette")!;
}

function rowFor(palette: HTMLElement, label: string): HTMLElement {
  const rows = Array.from(palette.querySelectorAll<HTMLElement>(".palette-item"));
  const row = rows.find((r) => r.querySelector(".pi-label")?.textContent?.trim() === label);
  if (!row) throw new Error(`no palette row labeled "${label}"`);
  return row;
}

beforeEach(() => {
  globalThis.localStorage?.clear();
  host = document.createElement("div");
  document.body.append(host);
});

afterEach(() => {
  shell?.teardown();
  shell = null;
  host.remove();
});

describe("command palette — accelerators teach the shortcuts", () => {
  it("renders a compact shell status strip when opened", () => {
    shell = mountDesktopShell(host);
    shell.store.setConnection("connected");
    shell.store.setActivation("live");

    const palette = openPalette();
    const summary = palette.querySelector<HTMLElement>(".palette-summary")!;
    expect(summary.textContent).toContain("Surface");
    expect(summary.textContent).toContain("Deck");
    expect(summary.textContent).toContain("State");
    expect(summary.textContent).toContain("Live");
    // Bus (connection) and Proof (panel open/closed) were dev-dashboard telemetry
    // on palette open; only navigational context (Surface, State) remains.
    expect(summary.textContent).not.toContain("Bus");
    expect(summary.textContent).not.toContain("Proof");
  });

  it("groups navigation above controls and marks the current surface", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();

    const sections = Array.from(palette.querySelectorAll(".palette-section")).map((el) =>
      el.textContent?.trim(),
    );
    expect(sections).toEqual(["Surfaces", "Controls"]);

    const deck = rowFor(palette, "Go to Deck");
    expect(deck.querySelector(".pi-state")?.textContent?.trim()).toBe("current");

    const togglePanel = rowFor(palette, "Toggle grounding panel");
    expect(togglePanel.querySelector(".pi-state")?.textContent?.trim()).toBe("closed");
  });

  it("surfaces every Go-to row's 1–5 accelerator, matching the sidebar", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();
    for (const surface of SURFACES) {
      const row = rowFor(palette, `Go to ${surface.label}`);
      const accel = row.querySelector<HTMLElement>(".pi-accel");
      expect(accel, `Go to ${surface.label} must show an accelerator`).toBeTruthy();
      expect(accel!.textContent?.trim()).toBe(surface.kbd);
    }
  });

  it("renders the description and the accelerator in separate slots (not one overloaded hint)", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();
    const deck = rowFor(palette, "Go to Deck");
    // Description is the surface hint, in its own slot.
    expect(deck.querySelector(".pi-desc")?.textContent?.trim()).toBe("the live co-host");
    // Accelerator is the bare digit, in its own slot — never co-mingled.
    expect(deck.querySelector(".pi-accel")?.textContent?.trim()).toBe("1");
    expect(deck.querySelector(".pi-hint")).toBeNull(); // the overloaded slot is gone
  });

  it("shows command rows' chords in the accelerator slot", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();
    const toggle = rowFor(palette, "Toggle grounding panel");
    expect(toggle.querySelector(".pi-accel")?.textContent).toContain("]");
  });

  it("does not expose fake live-state simulation commands", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();
    const labels = Array.from(palette.querySelectorAll(".pi-label")).map((e) =>
      e.textContent?.trim(),
    );
    expect(labels).not.toContain("Go live");
    expect(labels).not.toContain("Return to idle");
  });

  it("still filters by the description text, not just the label", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();
    const input = palette.querySelector<HTMLInputElement>(".palette-input")!;
    input.value = "co-host"; // appears in Deck's description, not its label
    input.dispatchEvent(new Event("input"));
    const labels = Array.from(palette.querySelectorAll(".pi-label")).map((e) => e.textContent?.trim());
    expect(labels).toContain("Go to Deck");
  });

  it("filters by product aliases such as Viber and proof", () => {
    shell = mountDesktopShell(host);
    const palette = openPalette();
    const input = palette.querySelector<HTMLInputElement>(".palette-input")!;

    input.value = "viber";
    input.dispatchEvent(new Event("input"));
    let labels = Array.from(palette.querySelectorAll(".pi-label")).map((e) => e.textContent?.trim());
    expect(labels).toEqual(["Go to Viber"]);

    input.value = "proof";
    input.dispatchEvent(new Event("input"));
    labels = Array.from(palette.querySelectorAll(".pi-label")).map((e) => e.textContent?.trim());
    expect(labels).toContain("Go to Debrief");
    expect(labels).toContain("Toggle grounding panel");
  });
});
