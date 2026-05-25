/* Phase 62 Plan 04 — pill state-machine.ts vitest spec (Task 1, TDD).
 *
 * Pure-function discipline: the pill state machine does NOT call Date.now()
 * or setTimeout. `now` is always passed in. Tests use literal numbers for
 * full determinism — no clock mocking. Mirrors the mascot state-machine.test
 * deterministic now-param pattern.
 *
 * Covers (PILL-03):
 *   - baseState mapping IDLE/LISTENING/TALKING/unknown → idle/listening/speaking
 *   - applyFrame READER updates status+voiceRms without transition
 *   - applyFrame WRITER (cohost-reaction) enters expand with collapseAt + text + chips
 *   - tickCollapse is data-driven (now >= collapseAt reverts), and a fresh
 *     reaction re-extends collapseAt
 *   - purity grep: no Date.now / setTimeout / setInterval / new Date
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import type { CitationChip } from "../session/components/citation-strip.js";
import {
  applyFrame,
  baseState,
  EXPAND_MS,
  initialPillState,
  setPeek,
  tickCollapse,
} from "./state-machine.js";

const T0 = 1_000_000; // arbitrary base timestamp

const SAMPLE_CHIPS: CitationChip[] = [
  { event_id: "ev:KICK_SWAP@45.2", verb: "kick swap", timestamp_s: 45.2 },
];

describe("baseState — wire status → collapsed mode", () => {
  it("maps TALKING → speaking", () => {
    expect(baseState("TALKING")).toBe("speaking");
  });
  it("maps LISTENING → listening", () => {
    expect(baseState("LISTENING")).toBe("listening");
  });
  it("maps IDLE → idle", () => {
    expect(baseState("IDLE")).toBe("idle");
  });
  it("maps unknown / null / undefined → idle (honest empty state)", () => {
    expect(baseState(null)).toBe("idle");
    expect(baseState(undefined)).toBe("idle");
    // @ts-expect-error — defensive against an off-enum wire value
    expect(baseState("WAT")).toBe("idle");
  });
});

describe("initialPillState — boot", () => {
  it("boots to idle / IDLE / no expand / silent waveform", () => {
    const s = initialPillState(T0);
    expect(s.mode).toBe("idle");
    expect(s.cohostStatus).toBe("IDLE");
    expect(s.collapseAt).toBeNull();
    expect(s.reactionText).toBe("");
    expect(s.chips).toEqual([]);
    expect(s.voiceRms).toBe(0);
    expect(s.peek).toBe(false);
  });
});

describe("setPeek — collapsed-pill hover flag (Phase-1b)", () => {
  it("turns peek on / off without touching mode or the reaction payload", () => {
    const s0 = applyFrame(initialPillState(T0), { cohostStatus: "LISTENING" }, T0 + 1);
    const on = setPeek(s0, true);
    expect(on.peek).toBe(true);
    // peek is orthogonal to mode — the collapsed state is untouched.
    expect(on.mode).toBe("listening");
    expect(on.cohostStatus).toBe("LISTENING");
    const off = setPeek(on, false);
    expect(off.peek).toBe(false);
    expect(off.mode).toBe("listening");
  });

  it("never enters/leaves expand — peek does not drive the panel", () => {
    const expanded = applyFrame(
      initialPillState(T0),
      { type: "cohost-reaction", text: "x", chips: SAMPLE_CHIPS },
      T0,
    );
    const peeked = setPeek(expanded, true);
    expect(peeked.mode).toBe("expand"); // expand untouched
    expect(peeked.reactionText).toBe("x"); // payload untouched
    expect(peeked.chips).toEqual(SAMPLE_CHIPS);
  });

  it("returns the SAME reference when the flag is unchanged (cheap skip)", () => {
    const s = initialPillState(T0);
    expect(setPeek(s, false)).toBe(s); // already false
    const on = setPeek(s, true);
    expect(setPeek(on, true)).toBe(on); // already true
  });

  it("is immutable — does not mutate the input state", () => {
    const s0 = initialPillState(T0);
    const s1 = setPeek(s0, true);
    expect(s0.peek).toBe(false);
    expect(s1).not.toBe(s0);
  });

  it("peek survives subsequent READER frames (frame spread preserves it)", () => {
    const peeked = setPeek(initialPillState(T0), true);
    const afterFrame = applyFrame(peeked, { cohostStatus: "TALKING", voiceRms: 0.4 }, T0 + 10);
    expect(afterFrame.peek).toBe(true);
    // and survives a collapse tick (non-expanded → no-op, ref preserved)
    expect(tickCollapse(afterFrame, T0 + 999).peek).toBe(true);
  });

  it("peek survives an expand→collapse tick (carried through the revert)", () => {
    const expanded = applyFrame(
      { ...initialPillState(T0), cohostStatus: "LISTENING" },
      { type: "cohost-reaction", text: "x", chips: SAMPLE_CHIPS },
      T0,
    );
    const peeked = setPeek(expanded, true);
    const collapsed = tickCollapse(peeked, T0 + EXPAND_MS);
    expect(collapsed.mode).toBe("listening");
    expect(collapsed.peek).toBe(true);
  });
});

describe("applyFrame — READER (snapshot / flat frame)", () => {
  it("TALKING snapshot drives mode → speaking + carries voiceRms (no expand)", () => {
    const s = applyFrame(initialPillState(T0), { cohostStatus: "TALKING", voiceRms: 0.7 }, T0 + 10);
    expect(s.mode).toBe("speaking");
    expect(s.cohostStatus).toBe("TALKING");
    expect(s.voiceRms).toBe(0.7);
    expect(s.collapseAt).toBeNull();
  });

  it("LISTENING → listening, IDLE → idle", () => {
    const listening = applyFrame(initialPillState(T0), { cohostStatus: "LISTENING" }, T0 + 10);
    expect(listening.mode).toBe("listening");
    const idle = applyFrame(listening, { cohostStatus: "IDLE" }, T0 + 20);
    expect(idle.mode).toBe("idle");
  });

  it("absent voiceRms keeps the prior value (defensive default)", () => {
    const s1 = applyFrame(initialPillState(T0), { cohostStatus: "TALKING", voiceRms: 0.42 }, T0 + 10);
    const s2 = applyFrame(s1, { cohostStatus: "TALKING" }, T0 + 20);
    expect(s2.voiceRms).toBe(0.42);
  });

  it("is immutable — does not mutate the input state", () => {
    const s0 = initialPillState(T0);
    const s1 = applyFrame(s0, { cohostStatus: "TALKING", voiceRms: 0.5 }, T0 + 10);
    expect(s0.mode).toBe("idle");
    expect(s0.voiceRms).toBe(0);
    expect(s1).not.toBe(s0);
  });
});

describe("applyFrame — WRITER (cohost-reaction)", () => {
  it("enters expand with collapseAt = now + EXPAND_MS + verbatim text + chips", () => {
    const s = applyFrame(
      initialPillState(T0),
      { type: "cohost-reaction", text: "kick's landing on the 1 — ride it", chips: SAMPLE_CHIPS },
      T0 + 100,
    );
    expect(s.mode).toBe("expand");
    expect(s.collapseAt).toBe(T0 + 100 + EXPAND_MS);
    expect(s.reactionText).toBe("kick's landing on the 1 — ride it");
    expect(s.chips).toEqual(SAMPLE_CHIPS);
  });

  it("accepts the ipc.session.cohost-reaction type alias", () => {
    const s = applyFrame(
      initialPillState(T0),
      { type: "ipc.session.cohost-reaction", text: "tight", chips: [] },
      T0 + 50,
    );
    expect(s.mode).toBe("expand");
    expect(s.reactionText).toBe("tight");
  });

  it("empty/absent chips → empty array (caller renders null strip)", () => {
    const s = applyFrame(initialPillState(T0), { type: "cohost-reaction", text: "nice" }, T0 + 1);
    expect(s.chips).toEqual([]);
  });
});

describe("tickCollapse — data-driven revert (no setTimeout)", () => {
  it("holds expand before collapseAt", () => {
    const expanded = applyFrame(
      { ...initialPillState(T0), cohostStatus: "LISTENING" },
      { type: "cohost-reaction", text: "x", chips: SAMPLE_CHIPS },
      T0,
    );
    const ticked = tickCollapse(expanded, T0 + EXPAND_MS - 1);
    expect(ticked.mode).toBe("expand");
    expect(ticked).toBe(expanded); // unchanged ref — cheap skip
  });

  it("reverts to baseState(cohostStatus) once now >= collapseAt + clears payload", () => {
    const expanded = applyFrame(
      { ...initialPillState(T0), cohostStatus: "LISTENING" },
      { type: "cohost-reaction", text: "x", chips: SAMPLE_CHIPS },
      T0,
    );
    const collapsed = tickCollapse(expanded, T0 + EXPAND_MS);
    expect(collapsed.mode).toBe("listening"); // reverts to the held base state
    expect(collapsed.collapseAt).toBeNull();
    expect(collapsed.reactionText).toBe("");
    expect(collapsed.chips).toEqual([]);
  });

  it("a fresh reaction before collapseAt re-extends the window", () => {
    let s = applyFrame(initialPillState(T0), { type: "cohost-reaction", text: "a", chips: [] }, T0);
    expect(s.collapseAt).toBe(T0 + EXPAND_MS);
    // second reaction 1s later → collapseAt extends to T0+1000+EXPAND_MS
    s = applyFrame(s, { type: "cohost-reaction", text: "b", chips: [] }, T0 + 1000);
    expect(s.collapseAt).toBe(T0 + 1000 + EXPAND_MS);
    // at the ORIGINAL collapseAt the pill is still expanded (extended)
    const ticked = tickCollapse(s, T0 + EXPAND_MS);
    expect(ticked.mode).toBe("expand");
  });

  it("is a no-op on a non-expanded state", () => {
    const s = applyFrame(initialPillState(T0), { cohostStatus: "TALKING", voiceRms: 0.3 }, T0);
    expect(tickCollapse(s, T0 + 999_999)).toBe(s);
  });
});

describe("a READER frame during an active expand holds the expand", () => {
  it("snapshot while expanded keeps mode=expand but updates voiceRms/status underneath", () => {
    const expanded = applyFrame(
      initialPillState(T0),
      { type: "cohost-reaction", text: "x", chips: SAMPLE_CHIPS },
      T0,
    );
    const held = applyFrame(expanded, { cohostStatus: "TALKING", voiceRms: 0.6 }, T0 + 10);
    expect(held.mode).toBe("expand"); // expand wins over the base state
    expect(held.cohostStatus).toBe("TALKING"); // base state updated underneath
    expect(held.voiceRms).toBe(0.6);
    // when it collapses, it reverts to the updated base state (speaking)
    const collapsed = tickCollapse(held, T0 + EXPAND_MS);
    expect(collapsed.mode).toBe("speaking");
  });
});

describe("PURITY — no wall-clock / no timers in state-machine.ts", () => {
  it("source contains no Date.now / setTimeout / setInterval / new Date", () => {
    const srcPath = fileURLToPath(new URL("./state-machine.ts", import.meta.url));
    const src = readFileSync(srcPath, "utf8");
    // Strip the comment header references so the grep targets real code.
    expect(src).not.toMatch(/Date\.now\s*\(/);
    expect(src).not.toMatch(/\bsetTimeout\s*\(/);
    expect(src).not.toMatch(/\bsetInterval\s*\(/);
    expect(src).not.toMatch(/new\s+Date\b/);
  });
});
