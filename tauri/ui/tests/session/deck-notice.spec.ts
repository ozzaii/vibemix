/* deck-notice.spec.ts — THE user-visible ipc.error surface (lanes B+D).
 *
 * Pins:
 *   - ipc.error(original_type ipc.session.start) reverts the optimistic
 *     runState to "armed" AND writes deckNotice with the cause.
 *   - ipc.session.stop failure surfaces a notice but keeps the running deck.
 *   - audio.capture (the sidecar's existing capture-fail emit) surfaces.
 *   - non-whitelisted types stay log-only (no deck state write).
 *   - SessionLayout renders notice into .vmx-deck__notice (hidden when null).
 *   - render-loop projects deckNotice → notice and Start clears it.
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
  renderSessionFrame,
} from "../../src/session/SessionLayout.js";
import { _internals } from "../../src/session/render-loop.js";

beforeEach(() => {
  _resetSessionStateForTests();
  vi.spyOn(console, "log").mockImplementation(() => {});
});
afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe("applyIpcError → deck notice", () => {
  it("session.start failure reverts the optimistic deck and names the cause", () => {
    setSessionState({ runState: "running" });
    applyIpcError({
      original_type: "ipc.session.start",
      reason: "session.start failed: RuntimeError: proxy setup failed: no route",
    });
    const s = getSessionState();
    expect(s.runState).toBe("armed");
    expect(s.deckNotice?.tone).toBe("error");
    expect(s.deckNotice?.text).toContain("couldn't go live");
    expect(s.deckNotice?.text).toContain("proxy setup failed");
  });

  it("session.stop failure keeps the running deck (backend still live) but surfaces", () => {
    setSessionState({ runState: "running" });
    applyIpcError({
      original_type: "ipc.session.stop",
      reason: "session.stop failed: RuntimeError: teardown wedged",
    });
    expect(getSessionState().runState).toBe("running");
    expect(getSessionState().deckNotice?.text).toContain("teardown wedged");
  });

  it("audio.capture (sidecar's existing capture-fail emit) surfaces on the deck", () => {
    applyIpcError({
      original_type: "audio.capture",
      reason: "input capture failed: PortAudioError",
    });
    expect(getSessionState().deckNotice?.text).toContain("input capture failed");
  });

  it("non-whitelisted errors stay log-only", () => {
    applyIpcError({ original_type: "ipc.settings.set", reason: "bad value" });
    expect(getSessionState().deckNotice ?? null).toBeNull();
  });
});

describe("SessionLayout notice render", () => {
  it("renders the notice text, sets tone, hides when null", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const mounted = mountSessionLayout(host, defaultState());
    const el = host.querySelector<HTMLElement>(".vmx-deck__notice");
    expect(el).toBeTruthy();
    expect(el!.hidden).toBe(true);

    renderSessionFrame(mounted, {
      ...defaultState(),
      notice: { text: "couldn't go live — proxy setup failed", tone: "error" },
    });
    expect(el!.hidden).toBe(false);
    expect(el!.textContent).toContain("couldn't go live");
    expect(el!.dataset.tone).toBe("error");

    renderSessionFrame(mounted, { ...defaultState(), notice: null });
    expect(el!.hidden).toBe(true);
  });
});

describe("render-loop projection + clears", () => {
  it("projects deckNotice → notice; Start click clears it for the retry", () => {
    setSessionState({
      runState: "armed",
      deckNotice: { text: "couldn't go live — x", tone: "error", ts: 1 },
    });
    const layout = _internals.projectToLayoutState(getSessionState());
    expect(layout.notice?.text).toContain("couldn't go live");

    layout.onStart?.(); // sessionStartHandler
    expect(getSessionState().runState).toBe("running");
    expect(getSessionState().deckNotice ?? null).toBeNull();
  });
});
