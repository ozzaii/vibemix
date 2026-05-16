/* Impeccable Wave 5.A — shortcuts overlay component coverage.
 *
 * Asserts:
 *   - Mounts a single panel with the expected KEYBOARD header.
 *   - Idempotent: mounting when already mounted returns the same handle
 *     and does NOT stack a second panel in the DOM.
 *   - The returned unmount function tears the overlay back down.
 *   - Renders the expected shortcut rows (mute / esc / back / `?`).
 *
 * Vitest env: jsdom (routed via vitest.config.ts `tests/**\/*.spec.ts`). */

import { afterEach, describe, expect, it } from "vitest";

import {
  getShortcutsOverlayHandle,
  isShortcutsOverlayMounted,
  mountShortcutsOverlay,
} from "../../../src/session/components/shortcuts-overlay.js";

afterEach(() => {
  // Tear down any lingering overlay between cases.
  getShortcutsOverlayHandle()?.unmount();
  document.body.replaceChildren();
});

describe("mountShortcutsOverlay", () => {
  it("mounts a panel with the KEYBOARD header", () => {
    const handle = mountShortcutsOverlay();
    expect(handle.root.isConnected).toBe(true);
    const header = handle.root.querySelector<HTMLElement>(
      ".vmx-shortcuts-panel__header",
    );
    expect(header).not.toBeNull();
    expect(header?.textContent).toBe("KEYBOARD");
  });

  it("uses the .vmx-tile utility with data-tile=hero", () => {
    const handle = mountShortcutsOverlay();
    const panel = handle.root.querySelector<HTMLElement>(".vmx-shortcuts-panel");
    expect(panel).not.toBeNull();
    expect(panel?.classList.contains("vmx-tile")).toBe(true);
    expect(panel?.getAttribute("data-tile")).toBe("hero");
  });

  // Critique pass 2 (2026-05-14): the "press ? again or esc to close"
  // footnote was redundant — the kbd-key list above already shows both
  // shortcuts. Cut for restraint. This spec pins the removal so a
  // future regression can't reintroduce the duplicate hint.
  it("has NO redundant dismissal-hint footnote", () => {
    const handle = mountShortcutsOverlay();
    const foot = handle.root.querySelector(".vmx-shortcuts-panel__footnote");
    expect(foot).toBeNull();
  });

  it("renders the expected shortcut rows (mute, esc, back, ?)", () => {
    const handle = mountShortcutsOverlay();
    const rows = handle.root.querySelectorAll(".vmx-shortcuts-panel__row");
    expect(rows.length).toBe(4);
    const descs = Array.from(rows).map((r) =>
      r.querySelector(".vmx-shortcuts-panel__desc")?.textContent,
    );
    expect(descs).toContain("show / hide this panel");
    expect(descs).toContain("mute the co-host");
    expect(descs).toContain("close any open panel or dialog");
    expect(descs).toContain("back one step (wizard only)");
  });

  it("is idempotent — a second mount returns the same handle and does NOT stack panels", () => {
    const h1 = mountShortcutsOverlay();
    const h2 = mountShortcutsOverlay();
    expect(h1).toBe(h2);
    const backdrops = document.querySelectorAll(".vmx-shortcuts-backdrop");
    expect(backdrops.length).toBe(1);
  });

  it("unmount removes the overlay from the DOM", () => {
    const handle = mountShortcutsOverlay();
    expect(isShortcutsOverlayMounted()).toBe(true);
    handle.unmount();
    expect(isShortcutsOverlayMounted()).toBe(false);
    expect(document.querySelector(".vmx-shortcuts-backdrop")).toBeNull();
  });

  it("unmount is idempotent (calling twice is a no-op)", () => {
    const handle = mountShortcutsOverlay();
    handle.unmount();
    expect(() => handle.unmount()).not.toThrow();
    expect(isShortcutsOverlayMounted()).toBe(false);
  });

  it("after unmount, a fresh mount produces a new handle", () => {
    const h1 = mountShortcutsOverlay();
    h1.unmount();
    const h2 = mountShortcutsOverlay();
    expect(h1).not.toBe(h2);
    expect(h2.root.isConnected).toBe(true);
  });
});

describe("shortcuts overlay — dismissal behavior", () => {
  // These tests live under session-shortcuts wiring (the component itself
  // is dismissal-passive). We assert here that the overlay does NOT
  // self-bind keyboard events — the parent owns Esc / ? toggling.

  it("does NOT add its own document keydown listener", () => {
    // We can't observe the listener list directly in jsdom, but we CAN
    // assert that firing keydown directly against document doesn't auto-
    // dismiss the overlay (the parent wiring is responsible).
    const handle = mountShortcutsOverlay();
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    // Overlay should still be mounted — only mountSessionShortcuts wires
    // the esc dismissal.
    expect(handle.root.isConnected).toBe(true);
  });
});
