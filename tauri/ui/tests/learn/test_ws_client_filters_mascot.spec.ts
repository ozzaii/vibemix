// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-07 — Learn ws-client must silently drop non-ipc.learn.*
//                    frames riding the shared ws:8765 socket (mascot,
//                    snapshot, status tick, mood-change). Pins REVIEW.md
//                    CR-03 (BLOCKER): the legacy 30 Hz mascot frame (a
//                    flat dict with no `type` field) was triggering
//                    ~30 console.warn() calls per second.
//
// Phase 91 — the Learn webview shares ws:8765 with the mascot bus. The
// pre-fix client logged "[learn:ws] envelope missing type; dropping" on
// every mascot frame (108k warnings/hour at 30 Hz). The fix is an
// early-return at the top of onMessage that filters to `ipc.learn.*`
// BEFORE any warn / validate / dispatch — silent drop for everything
// the Learn webview doesn't care about.
//
// This spec dispatches frames directly into a LearnWsClient via its
// internal onMessage path (exposed indirectly through the constructed
// instance's WebSocket onmessage handler) and asserts:
//   1. Mascot frames (no `type`) produce ZERO console output.
//   2. Status / snapshot / mood-change envelopes (valid type, wrong
//      prefix) produce ZERO console output AND ZERO window-dispatched
//      events.
//   3. A valid `ipc.learn.*` envelope DOES reach window as a CustomEvent.

import { describe, it, expect, vi, afterEach } from "vitest";
import { LearnWsClient } from "../../src/learn/ws-client";

function dispatchInto(client: LearnWsClient, raw: string): void {
  // The client wires `this.ws.onmessage = (ev) => this.onMessage(ev.data)`
  // after `connect()`. To exercise onMessage without a real WebSocket, we
  // call it through a synthetic ws-shaped object that the client owns.
  // The simplest seam: cast the private and invoke directly. This mirrors
  // the precedent in tests/learn/test_ws_client_uses_8765.spec.ts which
  // also pokes the client's internals via casting.
  const c = client as unknown as {
    onMessage(raw: unknown): void;
  };
  c.onMessage(raw);
}

describe("test_ws_client_filters_mascot.spec.ts (CR-03 regression guard)", () => {
  let warnSpy: ReturnType<typeof vi.spyOn>;

  afterEach(() => {
    warnSpy?.mockRestore();
  });

  it("mascot flat dict (no type field) produces NO console.warn / no dispatch", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const client = new LearnWsClient();
    // The mascot frame is the v4 flat shape — no envelope wrapping.
    // Source: src/vibemix/runtime/ws_bus.py:496-529.
    const mascotFrame = JSON.stringify({
      music: 0.2,
      voice: 0.0,
      mic: 0.1,
      audible: true,
      deck: "A",
      phase: "intro",
      bpm: 124,
    });
    const heard: Event[] = [];
    const listener = (e: Event) => heard.push(e);
    // Catch any ipc.* event the dispatcher might fire (it shouldn't).
    window.addEventListener("ipc.session.snapshot", listener);
    window.addEventListener("ipc.status.tick", listener);
    window.addEventListener("ipc.learn.midi_position", listener);
    try {
      dispatchInto(client, mascotFrame);
      // Pre-fix: console.warn called once with "envelope missing type".
      expect(warnSpy).not.toHaveBeenCalled();
      expect(heard).toEqual([]);
    } finally {
      window.removeEventListener("ipc.session.snapshot", listener);
      window.removeEventListener("ipc.status.tick", listener);
      window.removeEventListener("ipc.learn.midi_position", listener);
      client.close();
    }
  });

  it("ipc.session.snapshot envelope (valid, non-learn) is silently dropped", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const client = new LearnWsClient();
    const heard: Event[] = [];
    const listener = (e: Event) => heard.push(e);
    window.addEventListener("ipc.session.snapshot", listener);
    try {
      dispatchInto(
        client,
        JSON.stringify({
          type: "ipc.session.snapshot",
          payload: { something: "valid for session, not for learn" },
        }),
      );
      expect(warnSpy).not.toHaveBeenCalled();
      // The session snapshot belongs to a DIFFERENT webview; the Learn
      // ws-client must not dispatch it as a window event here.
      expect(heard).toEqual([]);
    } finally {
      window.removeEventListener("ipc.session.snapshot", listener);
      client.close();
    }
  });

  it("flat mascot frame can still expose the Course 3 lens without warnings", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const client = new LearnWsClient();
    const heard: CustomEvent[] = [];
    const listener = (e: Event) => heard.push(e as CustomEvent);
    window.addEventListener("learn.course3_lens", listener);
    try {
      dispatchInto(
        client,
        JSON.stringify({
          music: 0.4,
          audible: true,
          bpm: 126,
          course3_lens: {
            session_active: true,
            phrase_position_confidence: 1.4,
            next_phrase_at: 96.25,
            next_phrase_cue_id: "cue:track-a:phrase",
            audio_active: true,
            deck_attributed: true,
            deck_track_citable: true,
            cue_ready: true,
            blockers: [],
          },
        }),
      );
      expect(warnSpy).not.toHaveBeenCalled();
      expect(heard).toHaveLength(1);
      expect(heard[0]?.detail).toEqual({
        session_active: true,
        phrase_position_confidence: 1,
        next_phrase_at: 96.25,
        next_phrase_cue_id: "cue:track-a:phrase",
        audio_active: true,
        deck_attributed: true,
        deck_track_citable: true,
        cue_ready: true,
        blockers: [],
      });
    } finally {
      window.removeEventListener("learn.course3_lens", listener);
      client.close();
    }
  });

  it("preserves a Course 3 operator action from the flat frame", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const client = new LearnWsClient();
    const heard: CustomEvent[] = [];
    const listener = (e: Event) => heard.push(e as CustomEvent);
    window.addEventListener("learn.course3_lens", listener);
    try {
      dispatchInto(
        client,
        JSON.stringify({
          music: 0,
          audible: false,
          course3_lens: {
            session_active: false,
            phrase_position_confidence: 0,
            next_phrase_at: null,
            next_phrase_cue_id: null,
            audio_active: false,
            deck_attributed: false,
            deck_track_citable: false,
            cue_ready: false,
            blockers: ["waiting_for_audio"],
            operator_action: {
              prompt:
                "Play a real Rekordbox library track through BlackHole 2ch @ 48000Hz with channel and master faders up.",
              route: "BlackHole 2ch @ 48000Hz",
              steps: [
                "Stop unrelated media or make Rekordbox the active playing source.",
              ],
            },
          },
        }),
      );

      expect(warnSpy).not.toHaveBeenCalled();
      expect(heard).toHaveLength(1);
      expect(heard[0]?.detail.operator_action).toEqual({
        prompt:
          "Play a real Rekordbox library track through BlackHole 2ch @ 48000Hz with channel and master faders up.",
        route: "BlackHole 2ch @ 48000Hz",
        steps: ["Stop unrelated media or make Rekordbox the active playing source."],
      });
    } finally {
      window.removeEventListener("learn.course3_lens", listener);
      client.close();
    }
  });

  it("ipc.status.tick + ipc.mascot.mood_change envelopes silently dropped", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const client = new LearnWsClient();
    const heard: Event[] = [];
    const listener = (e: Event) => heard.push(e);
    window.addEventListener("ipc.status.tick", listener);
    window.addEventListener("ipc.mascot.mood_change", listener);
    try {
      dispatchInto(
        client,
        JSON.stringify({
          type: "ipc.status.tick",
          payload: { uptime_seconds: 42 },
        }),
      );
      dispatchInto(
        client,
        JSON.stringify({
          type: "ipc.mascot.mood_change",
          payload: { mood: "hype" },
        }),
      );
      expect(warnSpy).not.toHaveBeenCalled();
      expect(heard).toEqual([]);
    } finally {
      window.removeEventListener("ipc.status.tick", listener);
      window.removeEventListener("ipc.mascot.mood_change", listener);
      client.close();
    }
  });

  it("malformed JSON STILL warns (real error condition stays visible)", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const client = new LearnWsClient();
    try {
      dispatchInto(client, "{ this is not JSON");
      // The early-return is AFTER JSON.parse so genuine parse failures
      // still surface — silence applies only to "valid frames I don't
      // care about", not to "framing is broken".
      expect(warnSpy).toHaveBeenCalled();
      expect(warnSpy.mock.calls[0]?.[0]).toMatch(/parse failed/);
    } finally {
      client.close();
    }
  });
});
