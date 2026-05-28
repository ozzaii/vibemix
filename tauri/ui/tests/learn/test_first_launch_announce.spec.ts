// SPDX-License-Identifier: Apache-2.0
//
// REQ-ID: ONBOARD-02 — First-launch tutor announce-by-name.
//
// Pins the verbatim greeting "I see your <controller name> — let's go." on
// the FIRST controller-connect event of an app run, then a fall-back to
// the standard "<name> connected." text on subsequent reconnects. The
// greeting carries the SECOND permitted "let's go." exception in the
// v9.0 slop blocklist (the first was L1.01's iconic closer).
//
// Test surface is the aria-live region (#learn-sr-announcement) — same
// surface RENDER-03 verifies.

import { describe, it, expect, beforeEach, beforeAll, afterAll } from "vitest";
import { mountLearnWindow } from "../../src/learn/learn-window";

// LearnWsClient auto-connects in mountLearnWindow(); stub WebSocket to
// keep the test hermetic. Mirrors test_controller_detected_mounts_svg.test.ts.
const RealWebSocket = globalThis.WebSocket;
class StubWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  readyState = StubWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  constructor(_url: string) {}
  send(): void {}
  close(): void {
    this.readyState = StubWebSocket.CLOSED;
  }
  addEventListener(): void {}
  removeEventListener(): void {}
  dispatchEvent(): boolean {
    return true;
  }
}

function fireControllerDetected(
  connected: boolean,
  display_name: string,
  controller_id: string = "pioneer_ddj_flx4",
): void {
  window.dispatchEvent(
    new CustomEvent("ipc.learn.controller_detected", {
      detail: {
        connected,
        controller_id,
        display_name,
        port_name: `${display_name} MIDI 1`,
      },
    }),
  );
}

describe("first-launch tutor announce-by-name (ONBOARD-02)", () => {
  beforeAll(() => {
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = StubWebSocket;
  });
  afterAll(() => {
    (globalThis as unknown as { WebSocket: typeof RealWebSocket }).WebSocket =
      RealWebSocket;
  });
  beforeEach(() => {
    document.body.innerHTML = `<div id="learn-root"></div>`;
  });

  it("first connect emits the verbatim 'I see your <name> — let's go.' greeting", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    mountLearnWindow(root);
    fireControllerDetected(true, "Pioneer DDJ-FLX4");
    const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;
    expect(sr).not.toBeNull();
    // Exact verbatim — em-dash, lowercase "let's go.", trailing period.
    expect(sr.textContent).toBe("I see your Pioneer DDJ-FLX4 — let's go.");
  });

  it("subsequent reconnects fall back to '<name> connected.' (no re-greeting)", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    mountLearnWindow(root);
    // First connect — greeting fires.
    fireControllerDetected(true, "Pioneer DDJ-FLX4");
    const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;
    expect(sr.textContent).toBe("I see your Pioneer DDJ-FLX4 — let's go.");
    // Simulate disconnect → reconnect.
    fireControllerDetected(false, "Pioneer DDJ-FLX4");
    expect(sr.textContent).toBe("controller disconnected.");
    // Second connect — NO greeting, just the standard text.
    fireControllerDetected(true, "Pioneer DDJ-FLX4");
    expect(sr.textContent).toBe("Pioneer DDJ-FLX4 connected.");
  });

  it("greets with the LIVE display_name (not a hardcoded literal)", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    mountLearnWindow(root);
    fireControllerDetected(
      true,
      "Hercules DJControl Inpulse 300 MK2",
      "hercules_inpulse_300_mk2",
    );
    const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;
    expect(sr.textContent).toBe(
      "I see your Hercules DJControl Inpulse 300 MK2 — let's go.",
    );
  });

  it("aria-live region carries polite + atomic attributes (a11y contract)", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    mountLearnWindow(root);
    fireControllerDetected(true, "Pioneer DDJ-FLX4");
    const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;
    expect(sr.getAttribute("aria-live")).toBe("polite");
    expect(sr.getAttribute("aria-atomic")).toBe("true");
  });

  it("greeting fires only once even on a second 'first' connection mid-run", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    mountLearnWindow(root);
    // Two consecutive connect events without an intervening disconnect.
    fireControllerDetected(true, "Pioneer DDJ-FLX4");
    fireControllerDetected(true, "Pioneer DDJ-FLX4");
    const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;
    // The SECOND event overwrites to the standard text since the greeting
    // has already been used this run.
    expect(sr.textContent).toBe("Pioneer DDJ-FLX4 connected.");
  });
});
