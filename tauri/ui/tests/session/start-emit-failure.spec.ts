/* start-emit-failure.spec.ts — wave-2 go-live P1: an emitIpc FAILURE on
 * Start/Stop must return the deck to the truth, not strand the optimistic
 * flip.
 *
 * Before this pin, sessionStartHandler's catch only console.warn'd: the
 * optimistic runState="running" stayed forever even though the backend
 * never heard the start (no wire would ever correct it) — a permanently
 * fake LIVE deck. The stop path mirrored it: a lost stop emit showed the
 * armed deck while the session genuinely kept running (which also
 * disarmed the quit guard mid-set).
 *
 * Pins:
 *   - Start emit rejection → runState parks back to "armed" + an error
 *     deck notice naming the recovery ("try again").
 *   - Stop emit rejection → runState returns to "running" + an error
 *     deck notice.
 *   - Successful emits keep the optimistic value and set NO notice.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_t: string, _p?: unknown) => undefined),
  invoke: vi.fn(async () => undefined),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));

import { _internals } from "../../src/session/render-loop.js";
import {
  _resetSessionStateForTests,
  getSessionState,
  setSessionState,
} from "../../src/session/state.js";

function flushMicrotasks(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(() => {
  _resetSessionStateForTests();
  mocks.emitIpc.mockClear();
  mocks.emitIpc.mockImplementation(async () => undefined);
});

describe("session start/stop emit-failure honesty", () => {
  it("Start emit failure parks the deck back to armed with a notice", async () => {
    mocks.emitIpc.mockImplementation(async () => {
      throw new Error("bridge dead");
    });
    setSessionState({ runState: "armed" });
    _internals.projectToLayoutState(getSessionState()).onStart?.();
    expect(getSessionState().runState).toBe("running"); // optimistic flip first
    await flushMicrotasks();
    expect(getSessionState().runState).toBe("armed");
    expect(getSessionState().deckNotice?.tone).toBe("error");
    expect(getSessionState().deckNotice?.text).toContain("couldn't go live");
    expect(getSessionState().deckNotice?.text).toContain("try again");
  });

  it("Stop emit failure returns the deck to running with a notice", async () => {
    mocks.emitIpc.mockImplementation(async () => {
      throw new Error("bridge dead");
    });
    setSessionState({ runState: "running" });
    _internals.projectToLayoutState(getSessionState()).onStop?.();
    expect(getSessionState().runState).toBe("armed"); // optimistic flip first
    await flushMicrotasks();
    expect(getSessionState().runState).toBe("running");
    expect(getSessionState().deckNotice?.tone).toBe("error");
    expect(getSessionState().deckNotice?.text).toContain("couldn't stop cleanly");
  });

  it("successful Start keeps running and sets no notice", async () => {
    setSessionState({ runState: "armed" });
    _internals.projectToLayoutState(getSessionState()).onStart?.();
    await flushMicrotasks();
    expect(getSessionState().runState).toBe("running");
    expect(getSessionState().deckNotice ?? null).toBeNull();
  });

  it("successful Stop keeps armed and sets no notice", async () => {
    setSessionState({ runState: "running" });
    _internals.projectToLayoutState(getSessionState()).onStop?.();
    await flushMicrotasks();
    expect(getSessionState().runState).toBe("armed");
    expect(getSessionState().deckNotice ?? null).toBeNull();
  });
});
