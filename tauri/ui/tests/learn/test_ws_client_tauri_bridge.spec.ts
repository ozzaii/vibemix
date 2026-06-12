// SPDX-License-Identifier: Apache-2.0
// Learn should reuse the established Tauri IPC event bridge in production.
// Browser/dev harnesses that only shim invoke still fall back to ws:8765.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  subscribeIpc: vi.fn(),
  listenTauri: vi.fn(),
}));

vi.mock("../../src/ipc/client.js", () => ({
  subscribeIpc: mocks.subscribeIpc,
}));

vi.mock("../../src/tauri-runtime.js", () => ({
  listenTauri: mocks.listenTauri,
}));

import { LearnWsClient } from "../../src/learn/ws-client";

const REAL_WEBSOCKET = globalThis.WebSocket;

type LearnEnvelope = {
  type: string;
  ts: string;
  payload: Record<string, unknown>;
};

const EXPECTED_TAURI_SUBSCRIPTIONS = [
  "ipc.learn.controller_detected",
  "ipc.learn.midi_position",
  "ipc.learn.lesson_loaded",
  "ipc.learn.highlight",
  "ipc.learn.advance",
  "ipc.learn.complete_lesson",
  "ipc.learn.tutor_speak",
  "ipc.learn.live_grade",
  "ipc.learn.waveform_ready",
  "ipc.learn.playhead_tick",
  "ipc.learn.exemplar_play",
  "ipc.learn.exemplar_stop",
  "ipc.learn.progress_state",
  "ipc.status.tick",
].sort();

function installTauriEventBridge(): void {
  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    value: {},
    configurable: true,
  });
  Object.defineProperty(window, "__TAURI_EVENT_PLUGIN_INTERNALS__", {
    value: {},
    configurable: true,
  });
}

function installInvokeOnlyTauriShim(): void {
  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    value: {},
    configurable: true,
  });
  Reflect.deleteProperty(window, "__TAURI_EVENT_PLUGIN_INTERNALS__");
}

function clearTauriShims(): void {
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  Reflect.deleteProperty(window, "__TAURI_EVENT_PLUGIN_INTERNALS__");
}

describe("LearnWsClient Tauri bridge selection", () => {
  beforeEach(() => {
    clearTauriShims();
    mocks.subscribeIpc.mockReset();
    mocks.listenTauri.mockReset();
    mocks.listenTauri.mockImplementation(async () => () => undefined);
  });

  afterEach(() => {
    clearTauriShims();
    (globalThis as unknown as { WebSocket: typeof REAL_WEBSOCKET }).WebSocket =
      REAL_WEBSOCKET;
  });

  it("uses subscribeIpc in a real Tauri event-plugin runtime", async () => {
    installTauriEventBridge();

    const webSocketCtor = vi.fn();
    class ThrowingWebSocket {
      constructor(url: string) {
        webSocketCtor(url);
        throw new Error("Tauri bridge path must not open a browser WebSocket");
      }
    }
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = ThrowingWebSocket;

    const callbacks = new Map<string, (envelope: LearnEnvelope) => void>();
    const rawCallbacks = new Map<string, (event: { payload: unknown }) => void>();
    const unlisteners = new Map<string, ReturnType<typeof vi.fn>>();
    const course3LensUnlisten = vi.fn();
    const operatorActionUnlisten = vi.fn();
    mocks.subscribeIpc.mockImplementation(
      async (type: string, callback: (envelope: LearnEnvelope) => void) => {
        callbacks.set(type, callback);
        const unlisten = vi.fn();
        unlisteners.set(type, unlisten);
        return unlisten;
      },
    );
    mocks.listenTauri.mockImplementation(
      async (event: string, callback: (event: { payload: unknown }) => void) => {
        if (event === "learn-course3-lens") {
          rawCallbacks.set(event, callback);
          return course3LensUnlisten;
        }
        if (event === "learn-operator-action") {
          rawCallbacks.set(event, callback);
          return operatorActionUnlisten;
        }
        return () => undefined;
      },
    );

    const client = new LearnWsClient();
    const openSpy = vi.fn();
    const heard: CustomEvent[] = [];
    const heardGrade: CustomEvent[] = [];
    const heardCourse3: CustomEvent[] = [];
    const heardOperatorAction: CustomEvent[] = [];
    const onTutor = (event: Event): void => {
      heard.push(event as CustomEvent);
    };
    const onGrade = (event: Event): void => {
      heardGrade.push(event as CustomEvent);
    };
    const onCourse3 = (event: Event): void => {
      heardCourse3.push(event as CustomEvent);
    };
    const onOperatorAction = (event: Event): void => {
      heardOperatorAction.push(event as CustomEvent);
    };
    window.addEventListener("ipc.learn.tutor_speak", onTutor);
    window.addEventListener("ipc.learn.live_grade", onGrade);
    window.addEventListener("learn.course3_lens", onCourse3);
    window.addEventListener("learn.operator_action", onOperatorAction);
    client.addEventListener("open", openSpy);

    try {
      client.connect();
      await vi.waitFor(() => {
        expect([...callbacks.keys()].sort()).toEqual(EXPECTED_TAURI_SUBSCRIPTIONS);
      });
      await vi.waitFor(() => {
        expect(openSpy).toHaveBeenCalledTimes(1);
      });

      expect(webSocketCtor).not.toHaveBeenCalled();
      expect(mocks.listenTauri).toHaveBeenCalledWith(
        "learn-course3-lens",
        expect.any(Function),
      );
      expect(mocks.listenTauri).toHaveBeenCalledWith(
        "learn-operator-action",
        expect.any(Function),
      );

      callbacks.get("ipc.learn.tutor_speak")?.({
        type: "ipc.learn.tutor_speak",
        ts: "2026-05-28T00:00:00.000Z",
        payload: {
          text: "trim the highs",
          tts_marker: "L1.02.step1",
          citations: ["lesson:L1.02"],
          data_state: "active",
        },
      });
      callbacks.get("ipc.learn.live_grade")?.({
        type: "ipc.learn.live_grade",
        ts: "2026-05-28T00:00:00.000Z",
        payload: {
          verdict: "drifting",
          phase_error_beats: 0.125,
          score: 0.5,
          citation: null,
        },
      });
      const emitCourse3Lens = rawCallbacks.get("learn-course3-lens");
      expect(emitCourse3Lens).toBeTypeOf("function");
      if (!emitCourse3Lens) throw new Error("missing Course 3 lens listener");
      emitCourse3Lens({
        payload: {
          music: 0.6,
          course3_lens: {
            session_active: true,
            phrase_position_confidence: 0.88,
            next_phrase_at: 64,
            next_phrase_cue_id: "cue:track-a:phrase",
          },
        },
      });
      const emitOperatorAction = rawCallbacks.get("learn-operator-action");
      expect(emitOperatorAction).toBeTypeOf("function");
      if (!emitOperatorAction) throw new Error("missing operator-action listener");
      emitOperatorAction({
        payload: {
          prompt:
            "Set Rekordbox audio to BlackHole 16ch @ 48000Hz, then play a real library track with channel and master faders up.",
          route: "BlackHole 16ch @ 48000Hz",
          current_rekordbox_route: "DDJ-FLX4 @ 48000Hz",
          target_capture_route: "BlackHole 16ch @ 48000Hz",
          route_mismatch: true,
        },
      });

      expect(heard).toHaveLength(1);
      expect(heard[0]?.detail).toMatchObject({
        text: "trim the highs",
        data_state: "active",
      });
      expect(heardGrade).toHaveLength(1);
      expect(heardGrade[0]?.detail).toMatchObject({
        verdict: "drifting",
        phase_error_beats: 0.125,
        citation: null,
      });
      expect(heardCourse3).toHaveLength(1);
      expect(heardCourse3[0]?.detail).toMatchObject({
        session_active: true,
        phrase_position_confidence: 0.88,
        next_phrase_at: 64,
        next_phrase_cue_id: "cue:track-a:phrase",
      });
      expect(heardOperatorAction).toHaveLength(1);
      expect(heardOperatorAction[0]?.detail).toMatchObject({
        route: "BlackHole 16ch @ 48000Hz",
        current_rekordbox_route: "DDJ-FLX4 @ 48000Hz",
        target_capture_route: "BlackHole 16ch @ 48000Hz",
        route_mismatch: true,
      });

      client.close();
      expect(unlisteners.get("ipc.learn.tutor_speak")).toHaveBeenCalledTimes(1);
      expect(unlisteners.get("ipc.learn.live_grade")).toHaveBeenCalledTimes(1);
      expect(course3LensUnlisten).toHaveBeenCalledTimes(1);
      expect(operatorActionUnlisten).toHaveBeenCalledTimes(1);
    } finally {
      window.removeEventListener("ipc.learn.tutor_speak", onTutor);
      window.removeEventListener("ipc.learn.live_grade", onGrade);
      window.removeEventListener("learn.course3_lens", onCourse3);
      window.removeEventListener("learn.operator_action", onOperatorAction);
      client.close();
    }
  });

  it("falls back to direct ws:8765 when only invoke is shimmed", () => {
    installInvokeOnlyTauriShim();

    const urls: string[] = [];
    class CapturingWebSocket {
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      constructor(url: string) {
        urls.push(url);
      }
      close(): void {}
    }
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = CapturingWebSocket;

    const client = new LearnWsClient();
    try {
      client.connect();
      expect(mocks.subscribeIpc).not.toHaveBeenCalled();
      expect(urls).toEqual(["ws://127.0.0.1:8765"]);
    } finally {
      client.close();
    }
  });
});
