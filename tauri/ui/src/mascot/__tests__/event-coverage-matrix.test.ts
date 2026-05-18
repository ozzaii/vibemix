/* Phase 47 / MASCOT-05 — 4-layer × 15-event coverage matrix vitest spec.
 *
 * Proves every shipped event class hits at least one of
 * {Base / Emotion / Anticipation / Reaction} via EVENT_LAYER_PRIORITY_MAP.
 * KAAN_SPOKE is the explicit exception (talk-block rule per Phase 13
 * STATE_PRIORITY — mascot stays on Base during user speech).
 */

import { describe, expect, it, vi } from "vitest";

import type {
  EventClass,
  MascotLayerBundle47,
} from "../event-dispatcher.js";
import {
  EVENT_LAYER_PRIORITY_MAP,
  dispatchEvent47,
} from "../event-dispatcher.js";

const ALL_EVENT_CLASSES: EventClass[] = [
  "TRACK_CHANGE",
  "PHASE",
  "LAYER_ARRIVAL",
  "MIX_MOVE",
  "HEARTBEAT",
  "KAAN_SPOKE",
  "MANUAL",
  "DISTORTION_CLIMB",
  "ACID_LINE_ENTRY",
  "KICK_SWAP",
  "SUB_LAYER_ARRIVAL",
  "BREAKDOWN_KICK_KILL",
  "REENTRY_KICK_LAND",
  "KICK_DENSITY_SHIFT",
  "PHRASE_BOUNDARY",
];

function buildMockBundle(): MascotLayerBundle47 {
  return {
    base: { schedule: vi.fn() },
    emotion: { update: vi.fn() },
    anticipation: { update: vi.fn() },
    reaction: { fire: vi.fn() },
  };
}

describe("Phase 47 / MASCOT-05 — event-coverage matrix", () => {
  it("EVENT_LAYER_PRIORITY_MAP has exactly 15 event classes", () => {
    expect(Object.keys(EVENT_LAYER_PRIORITY_MAP)).toHaveLength(15);
  });

  it("every event class except KAAN_SPOKE hits at least one layer", () => {
    for (const event of ALL_EVENT_CLASSES) {
      const bundle = buildMockBundle();
      const fired = dispatchEvent47(event, bundle, 1_000);
      if (event === "KAAN_SPOKE") {
        expect(fired).toEqual([]);
      } else {
        expect(
          fired.length,
          `${event} must hit ≥1 layer; got 0 (MASCOT-05 acceptance gate)`,
        ).toBeGreaterThan(0);
      }
    }
  });

  it("KAAN_SPOKE explicit no-op (talk-block rule)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("KAAN_SPOKE", bundle, 1_000);
    expect(fired).toEqual([]);
    expect(bundle.base.schedule).not.toHaveBeenCalled();
    expect(bundle.emotion.update).not.toHaveBeenCalled();
    expect(bundle.anticipation.update).not.toHaveBeenCalled();
    expect(bundle.reaction.fire).not.toHaveBeenCalled();
  });

  it("TRACK_CHANGE fires emotion + anticipation + reaction (3-layer fanout)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("TRACK_CHANGE", bundle, 1_000);
    expect(new Set(fired)).toEqual(
      new Set(["emotion", "anticipation", "reaction"]),
    );
    expect(bundle.emotion.update).toHaveBeenCalledWith("emotion_focus", 1_000);
    expect(bundle.anticipation.update).toHaveBeenCalledWith("prep_mix", 1_000);
    expect(bundle.reaction.fire).toHaveBeenCalledWith("react_mix_in", 1_000);
  });

  it("BREAKDOWN_KICK_KILL fires anticipation + reaction (2-layer fanout)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("BREAKDOWN_KICK_KILL", bundle, 1_000);
    expect(new Set(fired)).toEqual(new Set(["anticipation", "reaction"]));
    expect(bundle.anticipation.update).toHaveBeenCalledWith(
      "prep_breakdown",
      1_000,
    );
    expect(bundle.reaction.fire).toHaveBeenCalledWith("react_breakdown", 1_000);
  });

  it("HEARTBEAT fires Base only (low-priority idle rotation)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("HEARTBEAT", bundle, 1_000);
    expect(fired).toEqual(["base"]);
    expect(bundle.base.schedule).toHaveBeenCalledWith("base_breathe", 1_000);
  });

  it("each Hard Tek detector maps to its dedicated reaction clip", () => {
    const mappings: Array<[EventClass, string]> = [
      ["DISTORTION_CLIMB", "react_distortion_climb"],
      ["ACID_LINE_ENTRY", "react_acid_line"],
      ["KICK_SWAP", "react_kick_swap"],
      ["SUB_LAYER_ARRIVAL", "react_sub_layer"],
      ["REENTRY_KICK_LAND", "react_reentry"],
      ["PHRASE_BOUNDARY", "react_phrase_boundary"],
    ];
    for (const [event, expectedClip] of mappings) {
      const bundle = buildMockBundle();
      dispatchEvent47(event, bundle, 1_000);
      expect(bundle.reaction.fire).toHaveBeenCalledWith(expectedClip, 1_000);
    }
  });

  it("MANUAL defaults to react_hype_peak", () => {
    const bundle = buildMockBundle();
    dispatchEvent47("MANUAL", bundle, 1_000);
    expect(bundle.reaction.fire).toHaveBeenCalledWith("react_hype_peak", 1_000);
  });

  it("LAYER_ARRIVAL fires emotion + reaction (2-layer fanout)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("LAYER_ARRIVAL", bundle, 1_000);
    expect(new Set(fired)).toEqual(new Set(["emotion", "reaction"]));
  });

  it("PHASE fires emotion + anticipation (2-layer fanout)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("PHASE", bundle, 1_000);
    expect(new Set(fired)).toEqual(new Set(["emotion", "anticipation"]));
  });

  it("MIX_MOVE fires reaction only", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("MIX_MOVE", bundle, 1_000);
    expect(fired).toEqual(["reaction"]);
  });

  it("KICK_DENSITY_SHIFT fires emotion only (focus shift)", () => {
    const bundle = buildMockBundle();
    const fired = dispatchEvent47("KICK_DENSITY_SHIFT", bundle, 1_000);
    expect(fired).toEqual(["emotion"]);
  });

  it("coverage matrix is total — no event class is undefined in the map", () => {
    for (const event of ALL_EVENT_CLASSES) {
      expect(EVENT_LAYER_PRIORITY_MAP[event]).toBeDefined();
    }
  });

  it("EVENT_LAYER_PRIORITY_MAP is frozen at module load", () => {
    expect(Object.isFrozen(EVENT_LAYER_PRIORITY_MAP)).toBe(true);
  });
});
