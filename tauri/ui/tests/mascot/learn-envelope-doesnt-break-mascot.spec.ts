// SPDX-License-Identifier: Apache-2.0
// REQ-ID: P13 mitigation (92-RESEARCH §Pitfall 3) — the 13 ipc.learn.*
//                  envelopes must NOT break the mascot's dispatchEvent
//                  handler. The handler is intentionally lax (drops
//                  unknown types via `return null`), but a future
//                  schema-drift could regress that.
//
// Phase 92 Plan 02 — LIVE test. Exercises the existing
// `dispatchEvent(machine, message, now, snapshot)` from
// `tauri/ui/src/mascot/event-dispatcher.ts` against every learn.*
// envelope shape:
//
//   * 2 P91 envelopes: ipc.learn.controller_detected,
//                      ipc.learn.midi_position
//   * 11 P92 envelopes: ipc.learn.start_course / start_lesson /
//                       complete_lesson / lesson_loaded / highlight /
//                       advance / ack / tutor_speak / exemplar_play /
//                       exemplar_stop / progress_state
//
// For each shape, the dispatcher MUST:
//   1. NOT throw.
//   2. Return null (the "unknown type, drop silently" path).
//   3. NOT mutate the machine state (returning null means no
//      DispatchResult, so the caller leaves the machine untouched).
//
// After all 13 are dispatched, a known-good event (PHASE → groove)
// MUST still produce a valid DispatchResult — confirming the handler
// stayed functional through the 13-envelope volley.

import { describe, expect, it } from "vitest";
import {
  dispatchEvent,
} from "../../src/mascot/event-dispatcher.js";
import { initialMachineState } from "../../src/mascot/state-machine.js";

const NOW_BASE = 1_700_000_000_000;

const SNAPSHOT = {
  bpm: 124,
  bpm_confidence: 0.8,
  downbeat_phase: 0.25,
  mood: "hype-man",
  music: 0.05,
  voice: 0.01,
};

const ISO_TS = "2026-05-28T00:00:00Z";

// Every Learn envelope payload Plan 92-01 ratified. Each is a minimum-
// valid shape per the schema — the mascot handler should drop them all
// silently via `return null`.
const LEARN_ENVELOPES: readonly Record<string, unknown>[] = [
  // P91 — landed in Plan 91-02
  {
    type: "ipc.learn.controller_detected",
    ts: ISO_TS,
    payload: {
      connected: true,
      controller_id: "pioneer_ddj_flx4",
      display_name: "Pioneer DDJ-FLX4",
      port_name: "DDJ-FLX4 USB MIDI Input",
    },
  },
  {
    type: "ipc.learn.midi_position",
    ts: ISO_TS,
    payload: {
      controller_id: "pioneer_ddj_flx4",
      positions: { "eq_hi:A": 64, xfader: 64 },
    },
  },
  // P92 — landed in Plan 92-01
  {
    type: "ipc.learn.start_course",
    ts: ISO_TS,
    payload: { course_id: "course_0", controller_id: "pioneer_ddj_flx4" },
  },
  {
    type: "ipc.learn.start_lesson",
    ts: ISO_TS,
    payload: { lesson_id: "L0.00-press-play", level: "fresh" },
  },
  {
    type: "ipc.learn.complete_lesson",
    ts: ISO_TS,
    payload: { lesson_id: "L0.00-press-play", reason: "completed" },
  },
  {
    type: "ipc.learn.lesson_loaded",
    ts: ISO_TS,
    payload: {
      course_id: "course_0",
      lesson_id: "L0.00-press-play",
      title: "press play",
      controller_id: "pioneer_ddj_flx4",
      progress_dots: [
        { lesson_id: "L0.00-press-play", status: "current" },
      ],
    },
  },
  {
    type: "ipc.learn.highlight",
    ts: ISO_TS,
    payload: {
      control_id: "play",
      deck: "A",
      cue_color: "amber",
      cue_shape: "pulse-ring",
      annotation: "press play",
      expected_action: {
        type: "button",
        control: "play",
        deck: "A",
        direction: "down",
      },
    },
  },
  {
    type: "ipc.learn.advance",
    ts: ISO_TS,
    payload: { lesson_id: "L0.00-press-play", reason: "action_matched" },
  },
  {
    type: "ipc.learn.ack",
    ts: ISO_TS,
    payload: {
      control_id: "play:A",
      source: "midi",
      value: 127,
      direction: "down",
    },
  },
  {
    type: "ipc.learn.tutor_speak",
    ts: ISO_TS,
    payload: {
      text: "find deck A play button",
      tts_marker: "L000.beat0",
      citations: [],
      data_state: "active",
    },
  },
  {
    type: "ipc.learn.exemplar_play",
    ts: ISO_TS,
    payload: { track_id: "track_0001", duration_s: 30.0, gain_db: -12.0 },
  },
  {
    type: "ipc.learn.exemplar_stop",
    ts: ISO_TS,
    payload: { track_id: "track_0001", reason: "completed" },
  },
  {
    type: "ipc.learn.progress_state",
    ts: ISO_TS,
    payload: { action: "reset" },
  },
];

describe("learn envelopes do not break the mascot handler (P13 mitigation)", () => {
  it("dispatchEvent returns null for every learn.* envelope without throwing", () => {
    const machine = initialMachineState(NOW_BASE);
    expect(LEARN_ENVELOPES.length).toBe(13);
    for (const env of LEARN_ENVELOPES) {
      // The contract is: dispatchEvent returns null for unknown types.
      // If a future refactor breaks that (e.g. an exception is thrown
      // on an `ipc.learn.*` type) the mascot subscription would crash.
      const result = dispatchEvent(machine, env, NOW_BASE + 1, SNAPSHOT);
      expect(
        result,
        `dispatchEvent on ${String(env.type)} must return null (drop silently)`,
      ).toBeNull();
    }
  });

  it("after 13 learn envelopes, a known-good PHASE event still produces a result", () => {
    let machine = initialMachineState(NOW_BASE);
    let now = NOW_BASE;

    for (const env of LEARN_ENVELOPES) {
      now += 33;
      const result = dispatchEvent(machine, env, now, SNAPSHOT);
      expect(result, `${String(env.type)} should drop to null`).toBeNull();
      // Machine stays unchanged because result is null (caller does
      // not update machine on null returns — that's the dispatcher's
      // contract per mascot/index.ts:231).
    }

    // The handler must still respond to a valid event after the volley.
    const phaseEvent = {
      type: "event",
      subtype: "PHASE",
      payload: { from: "groove", to: "groove" },
    };
    now += 33;
    const result = dispatchEvent(machine, phaseEvent, now, SNAPSHOT);
    expect(
      result,
      "after the 13-envelope volley, PHASE event must still produce a DispatchResult",
    ).not.toBeNull();
    expect(result?.machine).toBeDefined();
    machine = result!.machine;
    expect(machine.current).toBeDefined();
  });
});
