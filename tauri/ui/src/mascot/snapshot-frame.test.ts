import { describe, expect, it } from "vitest";

import { isSnapshotFrame } from "./snapshot-frame.js";

// The REAL wire shape — field names lifted from ws_bus.py's mascot_frame
// (flat, no `type` key; meter keys guaranteed by the BRINGUP-04 guard).
const liveFlatFrame = {
  music: 0.42,
  voice: 0.0,
  mic: 0.01,
  live_context_schema_version: 3,
  audible: true,
  deck: "A",
  phase: "build",
  bpm: 128.0,
  mood: "hype-man",
  bpm_confidence: 0.82,
  downbeat_phase: 0.25,
  beat_phase: 0.25,
  active_genre: "unknown",
  detected_genre: "unknown",
  genre_confidence: 0,
  emotion: null,
  reaction_intent: null,
  reaction_intent_seq: 0,
  deck_state: {},
};

describe("isSnapshotFrame", () => {
  it("accepts the real flat 30Hz live frame (no type key)", () => {
    expect(isSnapshotFrame(liveFlatFrame)).toBe(true);
  });

  it("accepts the legacy/fixture typed shape", () => {
    expect(isSnapshotFrame({ type: "snapshot", bpm: 120 })).toBe(true);
  });

  it("rejects typed ipc envelopes", () => {
    expect(
      isSnapshotFrame({ type: "ipc.learn.teaching_focus", payload: {} }),
    ).toBe(false);
    expect(
      isSnapshotFrame({ type: "ipc.mascot.mood_change", payload: {} }),
    ).toBe(false);
  });

  it("rejects event envelopes and partial frames", () => {
    expect(isSnapshotFrame({ type: "event", subtype: "track_change" })).toBe(
      false,
    );
    expect(isSnapshotFrame({ music: 0.5, voice: 0.1 })).toBe(false); // no mic
    expect(isSnapshotFrame(null)).toBe(false);
    expect(isSnapshotFrame("snapshot")).toBe(false);
  });
});
