// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — pure state-machine vitest spec.
 *
 * Pure-function discipline (mirrors pill/state-machine.test.ts): every
 * transition is a deterministic transform, no DOM, no clock. Covers the mode
 * switch, the per-mode labels/echo, immutability, and the per-mode LED meter
 * scaling (the load-bearing detail — centered scores ~0.3 would never light
 * the bar without the per-mode min/max).
 */

import { describe, expect, it } from "vitest";

import {
  echoText,
  fieldLabel,
  initialLibraryState,
  meterOn,
  METER_SEGMENTS,
  runLabel,
  setBrief,
  setChatMessage,
  setCueExport,
  setCueFolder,
  setCurve,
  setFolder,
  setMode,
  setQuery,
  setSeed,
  setStrategy,
} from "./state-machine.js";

describe("mode switch + labels", () => {
  it("starts in chat while keeping the techno search seed", () => {
    expect(initialLibraryState.mode).toBe("chat");
    expect(initialLibraryState.query).toBe("hard aggressive techno");
  });

  it("maps each mode to its field label", () => {
    expect(fieldLabel("search")).toBe("Vibe query");
    expect(fieldLabel("similar")).toBe("Seed track");
    expect(fieldLabel("ingest")).toBe("Folder to embed");
    expect(fieldLabel("cue")).toBe("Folder to cue");
    expect(fieldLabel("chat")).toBe("Talk to Viber");
  });

  it("maps each mode to its run-button label", () => {
    expect(runLabel("search")).toBe("▸ Run search");
    expect(runLabel("similar")).toBe("▸ Find similar");
    expect(runLabel("ingest")).toBe("▸ Embed folder");
    expect(runLabel("cue")).toBe("▸ Export cues");
    expect(runLabel("chat")).toBe("▸ Ask Viber");
  });

  it("echoes conversation in chat, query in search, seed in similar, and folder in cue", () => {
    const s = initialLibraryState;
    expect(echoText(s)).toBe("conversation");
    expect(echoText(setMode(s, "search"))).toBe(s.query);
    expect(echoText(setMode(s, "similar"))).toBe(s.seed);
    expect(echoText(setMode(s, "cue"))).toBe(s.cueFolder);
  });
});

describe("transitions are immutable", () => {
  it("setMode returns a new object", () => {
    const s = initialLibraryState;
    const next = setMode(s, "ingest");
    expect(next).not.toBe(s);
    expect(next.mode).toBe("ingest");
    expect(s.mode).toBe("chat");
  });

  it("setQuery / setSeed / setFolder / setStrategy update only their field", () => {
    let s = initialLibraryState;
    s = setQuery(s, "deep dub");
    expect(s.query).toBe("deep dub");
    s = setSeed(s, "track.wav");
    expect(s.seed).toBe("track.wav");
    s = setFolder(s, "/x");
    expect(s.folder).toBe("/x");
    s = setStrategy(s, "mean_excerpt");
    expect(s.strategy).toBe("mean_excerpt");
    // query survived the later mutations (immutable spread, not aliasing)
    expect(s.query).toBe("deep dub");
  });

  it("setCueFolder / setCueExport update only cue fields", () => {
    let s = initialLibraryState;
    s = setCueFolder(s, "/Music/set");
    expect(s.cueFolder).toBe("/Music/set");
    s = setCueExport(s, "both");
    expect(s.cueExport).toBe("both");
    expect(s.folder).toBe(initialLibraryState.folder);
    expect(s.query).toBe(initialLibraryState.query);
  });

  it("setBrief / setCurve update only their field (build mode)", () => {
    let s = initialLibraryState;
    s = setBrief(s, "festival mainstage");
    expect(s.brief).toBe("festival mainstage");
    s = setCurve(s, "festival");
    expect(s.curve).toBe("festival");
    // brief survived the curve mutation (immutable spread)
    expect(s.brief).toBe("festival mainstage");
  });

  it("setChatMessage is immutable + touches only the chat draft", () => {
    const s = initialLibraryState;
    const next = setChatMessage(s, "build me a dark bridge");
    expect(next).not.toBe(s);
    expect(next.chatMessage).toBe("build me a dark bridge");
    expect(s.chatMessage).toBe("");
    expect(next.query).toBe(s.query);
  });
});

describe("LED match meter — per-mode scaling", () => {
  it("uses 10 segments", () => {
    expect(METER_SEGMENTS).toBe(10);
  });

  it("lights a search score (~0.7) in the 0.60–0.80 band", () => {
    // 0.764 → (0.764-0.6)/(0.8-0.6) = 0.82 → round(8.2) = 8
    expect(meterOn(0.764, "search")).toBe(8);
    // a max-band score lights all 10
    expect(meterOn(0.8, "search")).toBe(METER_SEGMENTS);
    // below the floor lights none
    expect(meterOn(0.6, "search")).toBe(0);
  });

  it("lights a centered-similar score (~0.3) in the 0.20–0.40 band", () => {
    // 0.369 → (0.369-0.2)/(0.4-0.2) = 0.845 → round(8.45) = 8
    expect(meterOn(0.369, "similar")).toBe(8);
    expect(meterOn(0.4, "similar")).toBe(METER_SEGMENTS);
    expect(meterOn(0.2, "similar")).toBe(0);
  });

  it("clamps out-of-band scores to [0, SEGMENTS]", () => {
    expect(meterOn(0.95, "search")).toBe(METER_SEGMENTS);
    expect(meterOn(0.0, "search")).toBe(0);
    expect(meterOn(0.99, "similar")).toBe(METER_SEGMENTS);
  });
});
