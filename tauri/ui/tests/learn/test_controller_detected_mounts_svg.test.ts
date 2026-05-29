// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-01 — Plug FLX4 → SVG mounts within 2 s. A synthetic
//                    `ipc.learn.controller_detected` envelope dispatched
//                    into a mountLearnWindow instance must cause the
//                    matching SVG to mount at `#learn-root` within
//                    2000 ms (jsdom synthetic; production Tauri webview
//                    measurement is the §LEARN-LATENCY-CONTINGENCY gate).
//
// Phase 91 — WR-05 fix from REVIEW.md: the prior test body was a
// TODO sketch asserting `expect(real).toBe(true)` (i.e. "is the real
// renderer present in source?"). CI green was misleading; the
// 2-second mount-time contract was NOT under test. This implementation
// mounts the window, dispatches the synthetic envelope, awaits the
// dynamic-import settle, and asserts the FLX4-specific `<g data-control-id>`
// landed in the stage element.

import { describe, it, expect, beforeEach, beforeAll, afterAll } from "vitest";
import { mountLearnWindow } from "../../src/learn/learn-window";

const MOUNT_TIMEOUT_MS = 2000;
// The dynamic-import settle in jsdom is normally <10ms; 50ms is a
// safety margin without inflating the test runtime. The 2000ms RENDER-01
// contract is the wall-clock budget, NOT this poll interval.
const SETTLE_INITIAL_DELAY_MS = 20;
const SETTLE_POLL_INTERVAL_MS = 10;

// LearnWsClient falls back to ws://127.0.0.1:8765 in plain jsdom.
// There is no real server; the undici-backed WebSocket fires a
// connect-failed error AFTER the test completes (Uncaught Exception in
// vitest). Stub WebSocket with a no-op double for this file so we test
// the mount path purely, not the network seam (which is exercised by
// test_ws_client_uses_8765 + test_ws_client_filters_mascot already).
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
  constructor(_url: string) {
    /* never resolves — keeps the connection in CONNECTING forever */
  }
  send(): void {
    /* no-op */
  }
  close(): void {
    this.readyState = StubWebSocket.CLOSED;
  }
  addEventListener(): void {
    /* no-op */
  }
  removeEventListener(): void {
    /* no-op */
  }
  dispatchEvent(): boolean {
    return true;
  }
}

async function waitForMountedControl(
  root: HTMLElement,
  controlId: string,
  budgetMs: number,
): Promise<{ found: boolean; elapsedMs: number }> {
  const startedAt = performance.now();
  await new Promise((r) => setTimeout(r, SETTLE_INITIAL_DELAY_MS));
  while (performance.now() - startedAt < budgetMs) {
    const hit = root.querySelector(`[data-control-id="${controlId}"]`);
    if (hit) {
      return { found: true, elapsedMs: performance.now() - startedAt };
    }
    await new Promise((r) => setTimeout(r, SETTLE_POLL_INTERVAL_MS));
  }
  return { found: false, elapsedMs: performance.now() - startedAt };
}

describe("test_controller_detected_mounts_svg.test.ts (RENDER-01)", () => {
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

  it("ipc.learn.controller_detected mounts the matching SVG within 2000 ms", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    expect(root).not.toBeNull();
    const { ws } = mountLearnWindow(root);
    try {
      window.dispatchEvent(
        new CustomEvent("ipc.learn.controller_detected", {
          detail: {
            connected: true,
            controller_id: "pioneer_ddj_flx4",
            display_name: "Pioneer DDJ-FLX4",
            port_name: "DDJ-FLX4",
          },
        }),
      );
      // Mount happens async (the renderer dynamic-imports the SVG). Poll
      // for the FLX4-specific eq_hi:A group landing in the stage.
      const { found, elapsedMs } = await waitForMountedControl(
        root,
        "eq_hi:A",
        MOUNT_TIMEOUT_MS,
      );
      expect(found, `eq_hi:A did not mount within ${MOUNT_TIMEOUT_MS}ms`).toBe(
        true,
      );
      expect(elapsedMs).toBeLessThanOrEqual(MOUNT_TIMEOUT_MS);
    } finally {
      ws.close();
    }
  });

  it("ipc.learn.controller_detected{connected:false} falls back to the on-screen deck", async () => {
    const root = document.getElementById("learn-root") as HTMLElement;
    const { ws } = mountLearnWindow(root);
    try {
      // First connect → mount the FLX4 SVG.
      window.dispatchEvent(
        new CustomEvent("ipc.learn.controller_detected", {
          detail: {
            connected: true,
            controller_id: "pioneer_ddj_flx4",
            display_name: "Pioneer DDJ-FLX4",
            port_name: "DDJ-FLX4",
          },
        }),
      );
      const mounted = await waitForMountedControl(
        root,
        "eq_hi:A",
        MOUNT_TIMEOUT_MS,
      );
      expect(mounted.found).toBe(true);
      // Then disconnect → physical mirror clears, but practice remains usable.
      window.dispatchEvent(
        new CustomEvent("ipc.learn.controller_detected", {
          detail: {
            connected: false,
            controller_id: "pioneer_ddj_flx4",
            display_name: "Pioneer DDJ-FLX4",
            port_name: "DDJ-FLX4",
          },
        }),
      );
      // Settle one microtask so the fallback deck render runs.
      await new Promise((r) => setTimeout(r, 20));
      expect(root.querySelector('[data-control-id="eq_hi:A"]')).not.toBeNull();
      expect(root.textContent).toContain("on-screen deck");
    } finally {
      ws.close();
    }
  });
});
