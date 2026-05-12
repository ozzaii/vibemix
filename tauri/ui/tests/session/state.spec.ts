/* Phase 12 Wave 3 — SessionState merge + ring-cap semantics (Plan 12-04 §Tests).
 *
 * Asserts:
 *   - getSessionState returns the singleton's current frozen reference.
 *   - setSessionState replaces top-level keys (shallow merge — nested objects
 *     are NOT deep-merged).
 *   - appendTranscript caps at 200 (oldest entries drop off the head).
 *   - appendMidiEvents caps at 12.
 *   - Unrelated top-level keys preserve their identity (===) across patches
 *     so the render-loop's ref-equality fast-path can short-circuit.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  _resetSessionStateForTests,
  appendMidiEvents,
  appendTranscript,
  getSessionState,
  MIDI_EVENT_RING_CAP,
  setSessionState,
  TRANSCRIPT_RING_CAP,
} from "../../src/session/state.js";

beforeEach(() => {
  _resetSessionStateForTests();
});

describe("getSessionState / setSessionState", () => {
  it("returns the default snapshot with every field populated", () => {
    const s = getSessionState();
    expect(s.meters.music.rms).toBe(0);
    expect(s.meters.voice.peak).toBe(0);
    expect(s.transcript).toEqual([]);
    expect(s.midiEvents).toEqual([]);
    expect(s.status.livekit).toBeNull();
    expect(s.settings.push_to_mute_hotkey).toBe("cmd+shift+m");
    expect(s.cohostStatus).toBe("IDLE");
    expect(s.grounded).toBe(false);
  });

  it("setSessionState shallow-merges top-level keys", () => {
    const before = getSessionState();
    setSessionState({ bpm: 128 });
    const after = getSessionState();
    expect(after.bpm).toBe(128);
    // Unrelated top-level objects preserved by REFERENCE (===) — the
    // render-loop relies on this for the ref-equality fast path.
    expect(after.meters).toBe(before.meters);
    expect(after.transcript).toBe(before.transcript);
    expect(after.settings).toBe(before.settings);
  });

  it("setSessionState replaces (does NOT deep-merge) nested objects", () => {
    setSessionState({
      meters: {
        music: { rms: 0.5, peak: 0.8 },
        voice: { rms: 0.1, peak: 0.2 },
        mic: { rms: 0, peak: 0 },
      },
    });
    const s = getSessionState();
    expect(s.meters.music.rms).toBe(0.5);
    expect(s.meters.voice.peak).toBe(0.2);
    // Sanity: callers must pass the full triple — partial nested patches
    // would drop sibling fields. (This is the React-style contract.)
    setSessionState({
      meters: {
        music: { rms: 1, peak: 1 },
        voice: { rms: 0, peak: 0 },
        mic: { rms: 0, peak: 0 },
      },
    });
    expect(getSessionState().meters.music.rms).toBe(1);
  });

  it("returns the new state from setSessionState for convenience", () => {
    const next = setSessionState({ muted: true });
    expect(next.muted).toBe(true);
    expect(next).toBe(getSessionState());
  });
});

describe("appendTranscript ring cap", () => {
  it("appends entries up to 200 without trimming", () => {
    const lines = Array.from({ length: 150 }, (_, i) => ({
      role: "ai" as const,
      text: `line ${i}`,
      ts: `2026-05-12T00:00:${i.toString().padStart(2, "0")}Z`,
    }));
    const result = appendTranscript(lines);
    expect(result.length).toBe(150);
    expect(getSessionState().transcript.length).toBe(150);
  });

  it("trims the oldest entries when over 200", () => {
    const first = Array.from({ length: 150 }, (_, i) => ({
      role: "ai" as const,
      text: `first ${i}`,
      ts: `2026-05-12T00:00:00Z`,
    }));
    appendTranscript(first);
    const more = Array.from({ length: 100 }, (_, i) => ({
      role: "user" as const,
      text: `more ${i}`,
      ts: `2026-05-12T00:01:00Z`,
    }));
    appendTranscript(more);
    const state = getSessionState();
    expect(state.transcript.length).toBe(TRANSCRIPT_RING_CAP);
    // Oldest 50 were dropped; head should now be "first 50".
    expect(state.transcript[0]?.text).toBe("first 50");
    // Tail is the last "more 99".
    expect(state.transcript[199]?.text).toBe("more 99");
  });

  it("returns the same transcript ref when given an empty delta", () => {
    setSessionState({
      transcript: [{ role: "ai", text: "hi", ts: "2026-05-12T00:00:00Z" }],
    });
    const before = getSessionState().transcript;
    const after = appendTranscript([]);
    expect(after).toBe(before);
  });
});

describe("appendMidiEvents ring cap", () => {
  it("trims to MIDI_EVENT_RING_CAP (12) on overflow", () => {
    const events = Array.from({ length: 15 }, (_, i) => ({
      id: `e-${i}`,
      label: `ev${i}`,
      ageMs: i * 100,
    }));
    const result = appendMidiEvents(events);
    expect(result.length).toBe(MIDI_EVENT_RING_CAP);
    expect(MIDI_EVENT_RING_CAP).toBe(12);
    // The oldest 3 dropped; head is ev3.
    expect(result[0]?.label).toBe("ev3");
    expect(result[11]?.label).toBe("ev14");
  });

  it("accumulates across multiple appends", () => {
    appendMidiEvents([{ id: "a", label: "a", ageMs: 0 }]);
    appendMidiEvents([{ id: "b", label: "b", ageMs: 0 }]);
    appendMidiEvents([{ id: "c", label: "c", ageMs: 0 }]);
    expect(getSessionState().midiEvents.map((e) => e.label)).toEqual([
      "a",
      "b",
      "c",
    ]);
  });

  it("returns the same midiEvents ref when given an empty array", () => {
    setSessionState({ midiEvents: [{ id: "x", label: "x", ageMs: 0 }] });
    const before = getSessionState().midiEvents;
    const after = appendMidiEvents([]);
    expect(after).toBe(before);
  });
});
