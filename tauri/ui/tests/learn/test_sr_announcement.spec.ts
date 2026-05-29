// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-03 — Screen-reader polite announcement on
//                    `ipc.learn.controller_detected` arrival. Shape:
//                    `<aria-live="polite">${display_name} connected.</aria-live>`
//                    so VoiceOver / NVDA read the controller name without
//                    interrupting the user's current focus.
// Regression: the Learn window owns the aria-live region and mutates it from
// the controller-detected envelope.

import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

import { mountLearnWindow } from "../../src/learn/learn-window";

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

function fireControllerDetected(displayName: string): void {
  window.dispatchEvent(
    new CustomEvent("ipc.learn.controller_detected", {
      detail: {
        connected: true,
        controller_id: "pioneer_ddj_flx4",
        display_name: displayName,
        port_name: `${displayName} MIDI 1`,
      },
    }),
  );
}

describe("test_sr_announcement.spec.ts (RENDER-03)", () => {
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

  it("aria-live polite region receives standard connected text on reconnect", () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      fireControllerDetected("Pioneer DDJ-FLX4");
      fireControllerDetected("Pioneer DDJ-FLX4");

      const sr = root.querySelector<HTMLElement>('[data-sr-region="tutor"]');
      expect(sr?.getAttribute("aria-live")).toBe("polite");
      expect(sr?.textContent).toBe("Pioneer DDJ-FLX4 connected.");
    } finally {
      ws.close();
    }
  });
});
