/**
 * @vitest-environment jsdom
 *
 * The activation bridge maps the live session's state onto the shell's
 * self-arranging activation + connection (the shell store has no knowledge of
 * the ws bus; this is the one-way feed). The pure mappers are the contract; the
 * observer must be transition-gated so its low-frequency poll never fights a
 * user who opened the grounding panel by hand at idle.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShellStore } from "../../src/shell/shell-store.js";
import {
  activationForCohost,
  connectionForWsState,
  wireActivation,
} from "../../src/shell/activation-bridge.js";
import { setSessionState } from "../../src/session/state.js";

describe("activation bridge — pure mappers", () => {
  it("maps cohost status to shell activation 1:1", () => {
    expect(activationForCohost("TALKING")).toBe("live");
    expect(activationForCohost("LISTENING")).toBe("listening");
    expect(activationForCohost("IDLE")).toBe("idle");
  });

  it("maps ws-state to an honest connection (unknown/unreachable is disconnected, not faulted)", () => {
    expect(connectionForWsState("connected")).toBe("connected");
    expect(connectionForWsState("reconnecting")).toBe("reconnecting");
    expect(connectionForWsState("connecting")).toBe("reconnecting");
    expect(connectionForWsState("unreachable")).toBe("disconnected");
    expect(connectionForWsState("whatever")).toBe("disconnected");
  });
});

describe("activation bridge — observer", () => {
  let stop: (() => void) | null = null;

  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    stop?.();
    stop = null;
    vi.useRealTimers();
  });

  it("reflects the live cohost status onto the store activation", () => {
    setSessionState({ cohostStatus: "IDLE" });
    const store = new ShellStore();
    stop = wireActivation(store, { intervalMs: 10 });
    expect(store.getState().activation).toBe("idle");

    setSessionState({ cohostStatus: "TALKING" });
    vi.advanceTimersByTime(15);
    expect(store.getState().activation).toBe("live");
    expect(store.getState().panelOpen).toBe(true); // live self-opens the receipt
  });

  it("is transition-gated: a stable status never re-fires setActivation, so a user-opened panel survives the poll", () => {
    setSessionState({ cohostStatus: "IDLE" });
    const store = new ShellStore();
    stop = wireActivation(store, { intervalMs: 10 });
    expect(store.getState().activation).toBe("idle");

    // User opens the grounding panel by hand while idle.
    store.setPanelOpen(true);
    expect(store.getState().panelOpen).toBe(true);

    // Several polls pass with the status UNCHANGED — the panel must not be
    // slammed shut by a re-applied setActivation("idle").
    vi.advanceTimersByTime(50);
    expect(store.getState().panelOpen).toBe(true);
    expect(store.getState().activation).toBe("idle");
  });
});
