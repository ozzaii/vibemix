/**
 * @vitest-environment jsdom
 *
 * The grounding panel is the product's signature "shows its receipt" surface
 * (cardinal invariant #2 — the anti-slop gate). This contract keeps it honest at
 * idle and ALIVE when live: a materialized receipt with an armed indicator and
 * real placeholder copy, never a dead em-dash.
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
  it("is honest prose at idle (no receipt slots, no armed cue)", () => {
    shell = mountDesktopShell(host);
    const body = host.querySelector<HTMLElement>(".panel-body");
    expect(body?.textContent).toContain("Nothing to ground yet");
    expect(host.querySelector(".panel-section")).toBeNull();
    expect(host.querySelector(".panel-armed")).toBeNull();
  });

  it("materializes an ALIVE armed receipt when live", () => {
    shell = mountDesktopShell(host);
    shell.store.setActivation("live");

    // Two labeled slots — the receipt the co-host fills as it reacts.
    const labels = Array.from(host.querySelectorAll(".panel-label")).map((e) => e.textContent);
    expect(labels.some((l) => l?.includes("Cited"))).toBe(true);
    expect(labels.some((l) => l?.toLowerCase().includes("next"))).toBe(true);

    // The Cited slot carries a static armed indicator: grounding is live and
    // listening, so the receipt reads alive even before the first citation.
    expect(host.querySelector(".panel-section .panel-armed")).toBeTruthy();

    // No dead em-dash placeholder — every empty slot speaks in the co-host voice.
    const placeholders = Array.from(host.querySelectorAll(".panel-placeholder")).map(
      (e) => e.textContent?.trim(),
    );
    expect(placeholders).not.toContain("—");
    expect(placeholders.every((p) => (p?.length ?? 0) > 1)).toBe(true);
  });
});
