// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";

import {
  compactOperatorActionLabel,
  normalizeOperatorAction,
  operatorActionAriaLabel,
} from "../../src/learn/lesson/operator-action.js";

describe("learn operator action projection", () => {
  it("turns a routed Rekordbox proof action into one booth-sized phrase", () => {
    const action = normalizeOperatorAction({
      prompt:
        "Play a real Rekordbox library track through BlackHole 2ch @ 48000Hz with channel and master faders up.",
      route: "BlackHole 2ch @ 48000Hz",
      steps: [
        "Stop unrelated media or make Rekordbox the active playing source.",
        "Raise the playing channel fader and master until loopback capture has signal.",
      ],
      nowplaying_blocker: "macOS now-playing is Safari, not Rekordbox.",
    });

    expect(action).not.toBeNull();
    expect(compactOperatorActionLabel(action!)).toBe("play Rekordbox through BlackHole 2ch");
    expect(operatorActionAriaLabel(action!)).toContain(
      "Stop unrelated media",
    );
    expect(operatorActionAriaLabel(action!)).toContain(
      "loopback capture has signal",
    );
  });

  it("keeps exemplar ear-pass guidance short while preserving the output device", () => {
    const action = normalizeOperatorAction({
      prompt: "Listen to the four EQ exemplar loops on MacBook Pro Speakers.",
      recommended_output_devices: [
        { index: 4, name: "MacBook Pro Speakers", score: 102 },
      ],
      steps: [
        "uv run python scripts/audition_learn_exemplars.py --play --device-index 4",
      ],
    });

    expect(action).toMatchObject({
      recommended_output_devices: [{ index: 4, name: "MacBook Pro Speakers" }],
    });
    expect(compactOperatorActionLabel(action!)).toBe(
      "audition EQ examples on MacBook Pro Speakers",
    );
    expect(operatorActionAriaLabel(action!)).toContain("--device-index 4");
  });

  it("keeps a Rekordbox aggregate sample-rate fix as one precise booth phrase", () => {
    const action = normalizeOperatorAction({
      prompt:
        "Set Rekordbox's 'Aggregate Device' route, sampled as 'rekordbox Aggregate Device', from 44100Hz to 48000Hz in Audio MIDI Setup.",
      route: "rekordbox Aggregate Device @ 48000Hz",
      steps: [
        "Set Rekordbox's 'Aggregate Device' route, sampled as 'rekordbox Aggregate Device', from 44100Hz to 48000Hz in Audio MIDI Setup.",
        "Play a real Rekordbox library track through the routed master output.",
      ],
    });

    expect(action).not.toBeNull();
    expect(compactOperatorActionLabel(action!)).toBe("set aggregate route to 48k");
    expect(operatorActionAriaLabel(action!)).toContain(
      "rekordbox Aggregate Device @ 48000Hz",
    );
  });

  it("preserves route-mismatch evidence while keeping the booth phrase calm", () => {
    const action = normalizeOperatorAction({
      prompt:
        "Set Rekordbox audio to BlackHole 16ch @ 48000Hz, then play a real library track with channel and master faders up.",
      route: "BlackHole 16ch @ 48000Hz",
      current_rekordbox_route: "DDJ-FLX4 @ 48000Hz",
      target_capture_route: "BlackHole 16ch @ 48000Hz",
      route_mismatch: true,
      steps: [
        "In Rekordbox Audio preferences, set the audio output from DDJ-FLX4 @ 48000Hz to BlackHole 16ch @ 48000Hz.",
        "In Rekordbox, load and play a real library track through BlackHole 16ch @ 48000Hz.",
      ],
    });

    expect(action).toMatchObject({
      current_rekordbox_route: "DDJ-FLX4 @ 48000Hz",
      target_capture_route: "BlackHole 16ch @ 48000Hz",
      route_mismatch: true,
    });
    expect(compactOperatorActionLabel(action!)).toBe("route Rekordbox to BlackHole 16ch");
    expect(operatorActionAriaLabel(action!)).toContain(
      "current Rekordbox route: DDJ-FLX4 @ 48000Hz",
    );
    expect(operatorActionAriaLabel(action!)).toContain(
      "target capture route: BlackHole 16ch @ 48000Hz",
    );
    expect(operatorActionAriaLabel(action!)).toContain("route mismatch: yes");
  });

  it("rejects empty or non-string prompts", () => {
    expect(normalizeOperatorAction({ prompt: "   " })).toBeNull();
    expect(normalizeOperatorAction({ prompt: 42 })).toBeNull();
    expect(normalizeOperatorAction(null)).toBeNull();
  });
});
