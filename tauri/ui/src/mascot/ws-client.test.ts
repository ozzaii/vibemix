/* Phase 13 Plan 06 — ws-client.ts vitest spec (Task 1 RED, 7 tests).
 *
 * Strategy: replace the global WebSocket constructor with a fake that
 * exposes hooks to drive onopen / onmessage / onclose synchronously.
 * Combined with `vi.useFakeTimers()` this gives full deterministic
 * control over reconnect backoff math without any real network or
 * real wall clock.
 *
 * The reconnect schedule under test: 1s / 2s / 4s / 8s (cap). On a
 * successful connect, backoff resets to 1s. After `close()` is called,
 * no further reconnects fire.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { connectMascotBus } from "./ws-client.js";

// ── Fake WebSocket ────────────────────────────────────────────────────────

/**
 * A controllable WebSocket double. Each new construction is recorded in
 * `FakeWebSocket.instances` so tests can drive open/message/close on the
 * latest instance. The constructor URL is captured for assertion.
 */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static lastUrl: string | null = null;
  static reset(): void {
    FakeWebSocket.instances = [];
    FakeWebSocket.lastUrl = null;
  }

  readonly url: string;
  onopen: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  readyState = 0; // CONNECTING

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.lastUrl = url;
    FakeWebSocket.instances.push(this);
  }

  // ── Test hooks ─────────────────────────────────────────────────────────
  triggerOpen(): void {
    this.readyState = 1;
    if (this.onopen) this.onopen({});
  }
  triggerMessage(data: unknown): void {
    if (this.onmessage) this.onmessage({ data });
  }
  triggerClose(): void {
    this.readyState = 3;
    if (this.onclose) this.onclose({});
  }

  close(): void {
    this.readyState = 3;
    // mimic real WebSocket: close() does NOT fire onclose synchronously
    // unless the implementation does. We let the client manage its own
    // state via the close() it received.
  }
}

const originalWebSocket = globalThis.WebSocket;

beforeEach(() => {
  FakeWebSocket.reset();
  // @ts-expect-error — replacing the global constructor under test.
  globalThis.WebSocket = FakeWebSocket;
  vi.useFakeTimers();
});

afterEach(() => {
  // @ts-expect-error — restore the original WebSocket.
  globalThis.WebSocket = originalWebSocket;
  vi.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────

describe("connectMascotBus", () => {
  it("Test 1: opens a WebSocket to the supplied URL", () => {
    const client = connectMascotBus("ws://127.0.0.1:8765");
    expect(FakeWebSocket.lastUrl).toBe("ws://127.0.0.1:8765");
    expect(FakeWebSocket.instances).toHaveLength(1);
    client.close();
  });

  it("Test 2: onopen fires statusListener with 'connected'", () => {
    const client = connectMascotBus();
    const statusFn = vi.fn();
    client.addStatusListener(statusFn);
    const ws = FakeWebSocket.instances[0]!;
    ws.triggerOpen();
    expect(statusFn).toHaveBeenCalledWith("connected");
    client.close();
  });

  it("Test 3: onmessage with valid JSON delivers the parsed object to messageListener", () => {
    const client = connectMascotBus();
    const msgFn = vi.fn();
    client.addMessageListener(msgFn);
    const ws = FakeWebSocket.instances[0]!;
    ws.triggerOpen();
    ws.triggerMessage(JSON.stringify({ type: "snapshot", music: { rms: 0.5, peak: 0.8 } }));
    expect(msgFn).toHaveBeenCalledTimes(1);
    expect(msgFn).toHaveBeenCalledWith({ type: "snapshot", music: { rms: 0.5, peak: 0.8 } });
    client.close();
  });

  it("Test 4: onmessage with non-JSON does NOT throw and does NOT call messageListener", () => {
    const client = connectMascotBus();
    const msgFn = vi.fn();
    client.addMessageListener(msgFn);
    const ws = FakeWebSocket.instances[0]!;
    ws.triggerOpen();
    expect(() => ws.triggerMessage("not-json-{garbage")).not.toThrow();
    expect(msgFn).not.toHaveBeenCalled();
    client.close();
  });

  it("Test 5: onclose schedules reconnect with doubling backoff capped at 8000ms", () => {
    const client = connectMascotBus();
    // initial connect: instance #0
    expect(FakeWebSocket.instances).toHaveLength(1);
    // 1st close → reconnect after 1000ms
    FakeWebSocket.instances[0]!.triggerClose();
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(999);
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(2);

    // 2nd close (without successful open) → reconnect after 2000ms
    FakeWebSocket.instances[1]!.triggerClose();
    vi.advanceTimersByTime(1999);
    expect(FakeWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(3);

    // 3rd close → 4000ms
    FakeWebSocket.instances[2]!.triggerClose();
    vi.advanceTimersByTime(3999);
    expect(FakeWebSocket.instances).toHaveLength(3);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(4);

    // 4th close → 8000ms (cap)
    FakeWebSocket.instances[3]!.triggerClose();
    vi.advanceTimersByTime(7999);
    expect(FakeWebSocket.instances).toHaveLength(4);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(5);

    // 5th close → still 8000ms (cap, not 16000)
    FakeWebSocket.instances[4]!.triggerClose();
    vi.advanceTimersByTime(8000);
    expect(FakeWebSocket.instances).toHaveLength(6);

    client.close();
  });

  it("Test 6: successful reconnect resets backoff to 1000ms", () => {
    const client = connectMascotBus();
    // close → reconnect at 1000ms
    FakeWebSocket.instances[0]!.triggerClose();
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances).toHaveLength(2);
    // close → reconnect at 2000ms (escalated)
    FakeWebSocket.instances[1]!.triggerClose();
    vi.advanceTimersByTime(2000);
    expect(FakeWebSocket.instances).toHaveLength(3);
    // Successful open on instance #2 → backoff resets
    FakeWebSocket.instances[2]!.triggerOpen();
    FakeWebSocket.instances[2]!.triggerClose();
    // Next reconnect should fire at 1000ms (reset), not 4000ms.
    vi.advanceTimersByTime(999);
    expect(FakeWebSocket.instances).toHaveLength(3);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(4);
    client.close();
  });

  it("Test 7: close() prevents further auto-reconnects", () => {
    const client = connectMascotBus();
    client.close();
    // The WS instance is gone — even if a close event fires, no
    // reconnect timer should be queued.
    FakeWebSocket.instances[0]!.triggerClose();
    vi.advanceTimersByTime(60_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
