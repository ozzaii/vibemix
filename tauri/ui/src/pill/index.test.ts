/**
 * @vitest-environment jsdom
 *
 * Phase 62 Plan 04 — pill index.ts frame→state contract (Task 2).
 *
 * Asserts the reader/writer frame fan-out (62-PATTERNS "Frame fan-out") via
 * the pure exported helpers `toPillFrame` + `reduceFrame` — no bus, no boot:
 *   - snapshot cohost_status TALKING/LISTENING/IDLE → speaking/listening/idle
 *   - defensive voice read: flat `voice` OR nested `meters.voice.rms` (LIVE-05a)
 *   - cohost-reaction (bare + ipc-prefixed) → expand with the VERBATIM text
 *   - flat `voice > threshold` is carried even when cohost_status is absent
 *
 * jsdom env: index.ts imports citation-strip.ts, whose registerStyle() touches
 * document.head at module load — so this spec needs a DOM (the @vitest-environment
 * docblock above routes it without a vitest.config change).
 */

import { describe, expect, it } from "vitest";

import { initialPillState } from "./state-machine.js";
import {
  nextSuggestionChoiceMessage,
  reduceFrame,
  readDeckState,
  readNextSuggestion,
  toPillFrame,
} from "./index.js";

const T0 = 2_000_000;

describe("toPillFrame — defensive normalisation", () => {
  it("reads flat top-level voice on the live frame (LIVE-05a)", () => {
    const f = toPillFrame({ voice: 0.7, cohost_status: "TALKING" });
    expect(f?.voiceRms).toBe(0.7);
    expect(f?.cohostStatus).toBe("TALKING");
  });

  it("reads nested meters.voice.rms on the bridged snapshot (LIVE-05a)", () => {
    const f = toPillFrame({
      type: "snapshot",
      cohost_status: "TALKING",
      meters: { voice: { rms: 0.42, peak: 0.9 } },
    });
    expect(f?.voiceRms).toBe(0.42);
    expect(f?.voicePeak).toBe(0.9);
  });

  it("prefers the flat voice when both are present", () => {
    const f = toPillFrame({ voice: 0.55, meters: { voice: { rms: 0.1 } } });
    expect(f?.voiceRms).toBe(0.55);
  });

  it("returns null for a frame carrying nothing the pill reads", () => {
    expect(toPillFrame({ type: "snapshot", track: { title: "x" } })).toBeNull();
    expect(toPillFrame(null)).toBeNull();
    expect(toPillFrame("not an object")).toBeNull();
  });

  it("normalises a cohost-reaction to text + chips from citation_strip", () => {
    const f = toPillFrame({
      type: "cohost-reaction",
      text: "ride the kick",
      citation_strip: [{ event_id: "ev:KICK@1.0", verb: "kick", timestamp_s: 1.0 }],
    });
    expect(f?.type).toBe("cohost-reaction");
    expect(f?.text).toBe("ride the kick");
    expect(f?.chips?.length).toBe(1);
  });

  it("WR-06: filters malformed citation chips (no `[undefined @ 0:00]` slop)", () => {
    const f = toPillFrame({
      type: "cohost-reaction",
      text: "kick swap",
      citation_strip: [
        42,
        null,
        {},
        { event_id: "ev:OK@2.0", verb: "kick", timestamp_s: 2.0 }, // the only valid one
        { event_id: "ev:BAD", verb: "x" }, // missing timestamp_s
        { event_id: 7, verb: "x", timestamp_s: 1 }, // event_id wrong type
      ],
    });
    expect(f?.chips?.length).toBe(1);
    expect(f?.chips?.[0]?.event_id).toBe("ev:OK@2.0");
  });

  it("WR-06: a non-array citation_strip yields no chips (defensive)", () => {
    const f = toPillFrame({ type: "cohost-reaction", text: "x", citation_strip: "nope" });
    expect(f?.chips).toEqual([]);
  });
});

describe("reduceFrame — frame→state map (READER)", () => {
  it("TALKING → speaking", () => {
    const s = reduceFrame(initialPillState(T0), { cohost_status: "TALKING", voice: 0.5 }, T0 + 1);
    expect(s.mode).toBe("speaking");
    expect(s.voiceRms).toBe(0.5);
  });

  it("LISTENING → listening", () => {
    const s = reduceFrame(initialPillState(T0), { cohost_status: "LISTENING" }, T0 + 1);
    expect(s.mode).toBe("listening");
  });

  it("IDLE → idle", () => {
    const s = reduceFrame(
      reduceFrame(initialPillState(T0), { cohost_status: "TALKING", voice: 0.5 }, T0 + 1),
      { cohost_status: "IDLE" },
      T0 + 2,
    );
    expect(s.mode).toBe("idle");
  });

  it("a frame the pill ignores leaves the state unchanged (same ref)", () => {
    const s0 = initialPillState(T0);
    const s1 = reduceFrame(s0, { type: "snapshot", track: { title: "x" } }, T0 + 1);
    expect(s1).toBe(s0);
  });

  it("carries flat voice even when cohost_status is absent on the flat frame", () => {
    const s = reduceFrame(initialPillState(T0), { voice: 0.33 }, T0 + 1);
    expect(s.voiceRms).toBe(0.33);
  });
});

describe("readDeckState — latest-frame deck context (WR-03)", () => {
  it("returns the deck_state map verbatim when the frame carries one", () => {
    const ds = readDeckState({
      deck_state: { A: { title: "x", camelot: "8A", key: "C", bpm: 128, confidence: 0.9 } },
    });
    expect(ds).not.toBeNull();
    expect(ds!.A?.camelot).toBe("8A");
  });

  it("WR-03: an EMPTY deck_state {} is returned as {} (clears the chips on a deck unload)", () => {
    // A deck unload empties deck_state. readDeckState must return the empty map
    // (NOT null) so the caller replaces view.deckState with {} → the resolved
    // chip falls back to `decks · unknown` (no stale resolved key lingers).
    const ds = readDeckState({ deck_state: {} });
    expect(ds).not.toBeNull();
    expect(ds).toEqual({});
  });

  it("WR-03: a frame that OMITS deck_state returns null (caller keeps last — no thrash)", () => {
    // A bridged ipc.session.snapshot omits deck_state entirely; that frame says
    // nothing about decks, so the caller holds the last flat-frame map rather
    // than wiping it on every interleaved snapshot.
    expect(readDeckState({ type: "snapshot", meters: {} })).toBeNull();
    expect(readDeckState({})).toBeNull();
    expect(readDeckState(null)).toBeNull();
  });
});

describe("readNextSuggestion — tri-state (omitted / null / object)", () => {
  it("returns the suggestion object verbatim", () => {
    const ns = readNextSuggestion({
      next_suggestion: {
        track_id: "t1", title: "X", artist: "A", similarity: 0.8,
        why: "similar vibe", camelot: null, bpm: null,
      },
    });
    expect(ns).not.toBeNull();
    expect((ns as { track_id: string }).track_id).toBe("t1");
  });

  it("explicit null → null (the SuggestionService has no grounded pick → clear)", () => {
    expect(readNextSuggestion({ next_suggestion: null })).toBeNull();
  });

  it("OMITTED field → undefined (a bridged snapshot says nothing → hold last)", () => {
    expect(readNextSuggestion({ type: "snapshot" })).toBeUndefined();
    expect(readNextSuggestion({})).toBeUndefined();
    expect(readNextSuggestion(null)).toBeUndefined();
  });
});

describe("nextSuggestionChoiceMessage — backup command payload", () => {
  it("builds the existing websocket action shape for a rendered backup", () => {
    expect(
      nextSuggestionChoiceMessage({
        key: "tr_002",
        candidateId: "tr_002",
        trackId: "t2",
        title: "02 · Backup Heat",
        meta: "cue B",
      }),
    ).toEqual({
      action: "next_suggestion.choose",
      candidate_id: "tr_002",
      track_id: "t2",
    });
  });
});

describe("reduceFrame — cohost-reaction (WRITER → expand)", () => {
  it("a cohost-reaction drives expand with the VERBATIM text", () => {
    const s = reduceFrame(
      initialPillState(T0),
      { type: "cohost-reaction", text: "kick swap on the 1", citation_strip: [] },
      T0 + 5,
    );
    expect(s.mode).toBe("expand");
    expect(s.reactionText).toBe("kick swap on the 1");
  });

  it("accepts the ipc.session.cohost-reaction alias", () => {
    const s = reduceFrame(
      initialPillState(T0),
      { type: "ipc.session.cohost-reaction", text: "tight" },
      T0 + 5,
    );
    expect(s.mode).toBe("expand");
    expect(s.reactionText).toBe("tight");
  });

  it("never adds framing — reaction text is the wire string as-is", () => {
    const raw = "no AI: prefix, no marketing voice";
    const s = reduceFrame(initialPillState(T0), { type: "cohost-reaction", text: raw }, T0 + 5);
    expect(s.reactionText).toBe(raw);
  });
});
