/* cohost.muted.spec.ts — impeccable Wave 6 (closes H3 "user control &
 * freedom").
 *
 * Pins:
 *   - muted=true renders the .vmx-cohost__muted-pill inside the header
 *   - muted=false removes the pill (or never mounts it)
 *   - setCohost mounts/unmounts the pill in place — no panel rebuild
 *   - SessionLayout's diff path forwards the status.muted flag into the
 *     cohost props so a state flip surfaces immediately. */

import { afterEach, describe, expect, it } from "vitest";

import {
  renderCohostPanel,
  setCohost,
} from "../../src/session/components/cohost.js";
import {
  defaultState,
  mountSessionLayout,
  renderSessionFrame,
} from "../../src/session/SessionLayout.js";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("cohost MUTED pill — Wave 6 H3", () => {
  it("muted=true renders the MUTED pill inside the header", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      muted: true,
    });
    host().append(panel);
    const pill = panel.querySelector<HTMLElement>(".vmx-cohost__muted-pill");
    expect(pill).toBeTruthy();
    expect(pill?.textContent).toContain("MUTED");
    // Sits inside the cohost header next to the status row (not in a separate slot).
    expect(pill?.closest(".vmx-cohost__header")).toBeTruthy();
  });

  it("muted=false (default) hides the MUTED pill", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      muted: false,
    });
    host().append(panel);
    expect(panel.querySelector(".vmx-cohost__muted-pill")).toBeNull();
  });

  it("muted prop omitted → defaults to no pill (back-compat with existing callers)", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
    });
    host().append(panel);
    expect(panel.querySelector(".vmx-cohost__muted-pill")).toBeNull();
  });

  it("setCohost mounts the pill on muted flip true → no panel rebuild", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      muted: false,
    });
    host().append(panel);
    const headerEl = panel.querySelector(".vmx-cohost__header");
    expect(panel.querySelector(".vmx-cohost__muted-pill")).toBeNull();

    setCohost(panel, {
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      muted: true,
    });
    expect(panel.querySelector(".vmx-cohost__muted-pill")).toBeTruthy();
    // Same header node — diff render, not panel rebuild.
    expect(panel.querySelector(".vmx-cohost__header")).toBe(headerEl);
  });

  it("setCohost unmounts the pill on muted flip true → false", () => {
    const panel = renderCohostPanel({
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      muted: true,
    });
    host().append(panel);
    expect(panel.querySelector(".vmx-cohost__muted-pill")).toBeTruthy();

    setCohost(panel, {
      status: "LISTENING",
      transcript: [],
      latencyMs: null,
      grounded: true,
      muted: false,
    });
    expect(panel.querySelector(".vmx-cohost__muted-pill")).toBeNull();
  });

  // "The Deck Speaks" rebuild (2026-05-26): mute is no longer a cohost-panel
  // pill — it's the deck rail's mute control (data-on + label flip).
  it("SessionLayout reflects status.muted on the deck mute control", () => {
    const root = host();
    const initial = defaultState();
    initial.status.muted = true;
    mountSessionLayout(root, initial);
    const mute = root.querySelector<HTMLElement>('[data-action="mute"]');
    expect(mute?.dataset.on).toBe("true");
    expect(mute?.textContent).toBe("muted");
  });

  it("renderSessionFrame flips the deck mute control on status.muted change", () => {
    const root = host();
    const initial = defaultState();
    const mounted = mountSessionLayout(root, initial);
    const mute = root.querySelector<HTMLElement>('[data-action="mute"]');
    expect(mute?.dataset.on).toBe("false");

    const muted = { ...defaultState(), status: { ...initial.status, muted: true } };
    renderSessionFrame(mounted, muted);
    expect(mute?.dataset.on).toBe("true");
    expect(mute?.textContent).toBe("muted");

    const unmuted = { ...defaultState(), status: { ...initial.status, muted: false } };
    renderSessionFrame(mounted, unmuted);
    expect(mute?.dataset.on).toBe("false");
    expect(mute?.textContent).toBe("mute");
  });
});
