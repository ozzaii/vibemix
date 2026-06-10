// SPDX-License-Identifier: Apache-2.0
// The debrief sidecar binds 127.0.0.1:8766 only after PyInstaller boot
// (and first-time generation). The client must keep retrying across that
// window instead of declaring "sidecar crashed" after ~1.4s.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DebriefWsClient } from "../ws-client.js";

class AlwaysRefusingWebSocket {
  constructor() {
    throw new Error("ECONNREFUSED");
  }
}

describe("DebriefWsClient reconnect budget", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
    vi.stubGlobal(
      "WebSocket",
      AlwaysRefusingWebSocket as unknown as typeof WebSocket,
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("keeps retrying (no sidecar_crashed) while the budget lasts", () => {
    const client = new DebriefWsClient(8766);
    const errors: { reason?: string }[] = [];
    const connecting: unknown[] = [];
    client.addEventListener("error", (e) =>
      errors.push((e as CustomEvent).detail as { reason?: string }),
    );
    client.addEventListener("connecting", (e) =>
      connecting.push((e as CustomEvent).detail),
    );

    client.connect();
    vi.advanceTimersByTime(60_000); // long first generation, inside budget

    expect(errors.filter((d) => d?.reason === "sidecar_crashed")).toEqual([]);
    expect(connecting.length).toBeGreaterThan(10);
  });

  it("declares sidecar_crashed only after the budget is spent", () => {
    const client = new DebriefWsClient(8766);
    const errors: { reason?: string }[] = [];
    client.addEventListener("error", (e) =>
      errors.push((e as CustomEvent).detail as { reason?: string }),
    );

    client.connect();
    vi.advanceTimersByTime(125_000);

    expect(errors.some((d) => d?.reason === "sidecar_crashed")).toBe(true);
  });
});
