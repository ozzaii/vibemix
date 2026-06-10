/* capture-error.spec.ts — Audit B-audio-firstrun (F3), on lane D's shared
 * deck-notice surface (lanes B+D contract, deck-notice.spec.ts).
 *
 * The capture-open path makes ipc.session.start SUCCEED before the stream
 * binds (__main__._set_input_stream_error sets started_event BEFORE
 * run_stop_event), so the only wire signal of a dead Start is
 * ipc.error{original_type:"audio.capture"} — arriving while the deck is
 * optimistically "running". Lane D pre-whitelisted the type for the notice
 * text; this lane pins that it ALSO parks the deck: runState flips back to
 * "armed" and the notice carries the standby/retry guidance. Do NOT route
 * this through status.livekit — the 1Hz status tick hard-codes livekit="ok"
 * and would clear it within a second.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  emitIpc: vi.fn(async (_t: string, _p?: unknown) => undefined),
  subscribeIpc: vi.fn(async () => () => {}),
  invoke: vi.fn(async () => undefined),
}));
vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: mocks.emitIpc,
  subscribeIpc: mocks.subscribeIpc,
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));

import { applyIpcError } from "../../src/session/ws-bridge.js";
import {
  _resetSessionStateForTests,
  getSessionState,
  setSessionState,
} from "../../src/session/state.js";
import {
  defaultState,
  mountSessionLayout,
} from "../../src/session/SessionLayout.js";
import { _internals } from "../../src/session/render-loop.js";

beforeEach(() => {
  _resetSessionStateForTests();
  mocks.emitIpc.mockClear();
  vi.spyOn(console, "log").mockImplementation(() => {});
});
afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe("capture-failure surfacing (audit B-audio-firstrun)", () => {
  it("audio.capture ipc.error flips the running deck back to armed with a cause", () => {
    setSessionState({ runState: "running" });
    applyIpcError({
      original_type: "audio.capture",
      reason: "input capture failed: PortAudioError",
    });
    const s = getSessionState();
    expect(s.runState).toBe("armed");
    expect(s.deckNotice?.tone).toBe("error");
    expect(s.deckNotice?.text).toContain("input capture failed");
    expect(s.deckNotice?.text).toContain("Go live to retry");
  });

  it("ipc.session.start failure parks the deck the same way (lane D, regression guard)", () => {
    setSessionState({ runState: "running" });
    applyIpcError({
      original_type: "ipc.session.start",
      reason: "session.start failed: RuntimeError",
    });
    expect(getSessionState().runState).toBe("armed");
    expect(getSessionState().deckNotice?.text).toContain("couldn't go live");
  });

  it("unrelated ipc.error stays log-only (no state flip)", () => {
    setSessionState({ runState: "running" });
    applyIpcError({
      original_type: "ipc.settings.set",
      reason: "settings.set rejected",
    });
    expect(getSessionState().runState).toBe("running");
    expect(getSessionState().deckNotice ?? null).toBeNull();
  });

  it("Start clears the notice (recovery action — lane D, regression guard)", () => {
    setSessionState({
      runState: "armed",
      deckNotice: { text: "boom", tone: "error", ts: 1 },
    });
    _internals.projectToLayoutState(getSessionState()).onStart?.();
    expect(getSessionState().runState).toBe("running");
    expect(getSessionState().deckNotice ?? null).toBeNull();
  });

  it("SessionLayout shows the notice on the ARMED gate and hides it when null", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const s = defaultState();
    s.runState = "armed";
    s.notice = {
      text: "input capture failed: PortAudioError. The deck is back on standby. Go live to retry.",
      tone: "error",
    };
    mountSessionLayout(host, s);
    const notice = host.querySelector<HTMLElement>(".vmx-deck__notice");
    expect(notice).not.toBeNull();
    expect(notice!.hidden).toBe(false);
    expect(notice!.textContent).toContain("capture failed");

    const calm = document.createElement("div");
    document.body.append(calm);
    const s2 = defaultState();
    s2.runState = "armed";
    s2.notice = null;
    mountSessionLayout(calm, s2);
    expect(calm.querySelector<HTMLElement>(".vmx-deck__notice")!.hidden).toBe(
      true,
    );
  });
});
