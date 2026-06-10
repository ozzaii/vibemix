/* ws-bridge.runstate.spec.ts — SHIP-WIRE START-gate run-state reconciliation.
 *
 * Pins:
 *   - run_state:"armed" on the wire reverts a stale optimistic "running"
 *     (the restarted-sidecar strand: UI running, backend armed forever).
 *   - run_state:"running" confirms the optimistic repaint (no-op write).
 *   - run_state null/absent never touches runState (standalone emitters).
 *   - the click-hold: within RUN_STATE_HOLD_MS of holdRunStateReconciliation()
 *     a conflicting wire value loses; after it expires the wire wins.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_t: string, _p?: unknown) => undefined),
  subscribeIpc: vi.fn(async () => () => {}),
}));
vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
  subscribeIpc: mocks.subscribeIpc,
}));

import {
  _resetBridgeForTests,
  applySnapshot,
  holdRunStateReconciliation,
  RUN_STATE_HOLD_MS,
} from "../../src/session/ws-bridge.js";
import {
  _resetSessionStateForTests,
  getSessionState,
  setSessionState,
} from "../../src/session/state.js";

function snap(overrides: Record<string, unknown> = {}): never {
  return {
    meters: {
      music: { rms: 0.2, peak: 0.3 },
      voice: { rms: 0, peak: 0 },
      mic: { rms: 0, peak: 0 },
    },
    phase: [],
    phase_now_pct: 0,
    bpm: null,
    drop_pred_bars: null,
    transcript_delta: [],
    midi_events: [],
    track: null,
    cohost_status: "IDLE",
    latency_ms: null,
    grounded: false,
    ...overrides,
  } as never;
}

beforeEach(() => {
  _resetSessionStateForTests();
  _resetBridgeForTests();
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("applySnapshot run_state reconciliation", () => {
  it("armed on the wire reverts a stranded optimistic running deck", () => {
    setSessionState({ runState: "running" });
    applySnapshot(snap({ run_state: "armed" }));
    expect(getSessionState().runState).toBe("armed");
  });

  it("running on the wire confirms the live deck", () => {
    setSessionState({ runState: "armed" });
    applySnapshot(snap({ run_state: "running" }));
    expect(getSessionState().runState).toBe("running");
  });

  it("null / absent run_state never touches the optimistic value", () => {
    setSessionState({ runState: "running" });
    applySnapshot(snap({ run_state: null }));
    expect(getSessionState().runState).toBe("running");
    applySnapshot(snap());
    expect(getSessionState().runState).toBe("running");
  });

  it("the click-hold lets the optimistic repaint win, then the wire wins", () => {
    const now = vi.spyOn(Date, "now").mockReturnValue(100_000);
    holdRunStateReconciliation();
    setSessionState({ runState: "running" }); // optimistic Start
    applySnapshot(snap({ run_state: "armed" })); // raced pre-click frame
    expect(getSessionState().runState).toBe("running");

    now.mockReturnValue(100_000 + RUN_STATE_HOLD_MS + 1);
    applySnapshot(snap({ run_state: "armed" })); // backend truly never started
    expect(getSessionState().runState).toBe("armed");
  });
});
