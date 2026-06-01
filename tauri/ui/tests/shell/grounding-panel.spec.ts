/**
 * @vitest-environment jsdom
 *
 * The grounding panel must not pretend to hold citations before it has a real
 * citation feed. Activation can open it, but the empty state stays explicit.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";

let shell: MountedShell | null = null;
let host: HTMLElement;

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

describe("grounding panel receipt", () => {
  it("is honest prose at idle with no receipt slots", () => {
    shell = mountDesktopShell(host);
    const body = host.querySelector<HTMLElement>(".panel-body");
    expect(body?.textContent).toContain("Nothing to ground yet");
    expect(host.querySelector(".panel-section")).toBeNull();
  });

  it("keeps live slots honest until real citations and suggestions are wired", () => {
    shell = mountDesktopShell(host);
    shell.store.setActivation("live");

    const labels = Array.from(host.querySelectorAll(".panel-label")).map((e) => e.textContent);
    expect(labels).toContain("Evidence");
    expect(labels.some((l) => l?.toLowerCase().includes("next"))).toBe(true);
    expect(labels.some((l) => l?.includes("Cited"))).toBe(false);
    expect(host.querySelector(".panel-section .panel-armed")).toBeNull();

    // No dead em-dash placeholder — every empty slot speaks in the co-host voice.
    const placeholders = Array.from(host.querySelectorAll(".panel-placeholder")).map(
      (e) => e.textContent?.trim(),
    );
    expect(placeholders).not.toContain("—");
    expect(placeholders).toContain("No cited move yet.");
    expect(placeholders).toContain("No suggestion yet.");
    expect(placeholders.every((p) => (p?.length ?? 0) > 1)).toBe(true);
  });

  it("prints the receipt in ONLY on the live transition, not on re-renders while live", () => {
    shell = mountDesktopShell(host);
    shell.store.setActivation("live");
    // Going live: the receipt slots carry the one-shot entry class (they
    // materialize/print in as the drawer arrives).
    const printed = Array.from(host.querySelectorAll(".panel-section"));
    expect(printed.length).toBe(2);
    expect(printed.every((s) => s.classList.contains("panel-section--enter"))).toBe(true);

    // A later re-render while STILL live (e.g. switching surfaces) rebuilds the
    // receipt but must NOT replay the entry — it was already on screen.
    shell.store.setActiveSurface("crate");
    const rerendered = Array.from(host.querySelectorAll(".panel-section"));
    expect(rerendered.length).toBe(2);
    expect(rerendered.some((s) => s.classList.contains("panel-section--enter"))).toBe(false);
  });
});
