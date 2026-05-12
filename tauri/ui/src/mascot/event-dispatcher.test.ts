/* Phase 13 Plan 06 — event-dispatcher.ts vitest spec (Task 1 RED, 10 tests).
 *
 * The dispatcher is a PURE function: it consumes a parsed bus message +
 * the current MachineState + a wall-clock `now` + the latest snapshot
 * (bpm + bpm_confidence + downbeat_phase + mood) and returns a
 * `{ plan, machine, followup? }` tuple — or null when the message is
 * unknown / malformed.
 *
 * Tests pin the full event taxonomy from CONTEXT.md Area 3:
 *   - TRACK_CHANGE       → react_surprised (followup idle_bop_to_beat_energetic)
 *   - PHASE → drop       → dance_hard
 *   - PHASE → silent     → idle_breathe
 *   - AI_GENERATING_REPLY → talk_loop (interrupt-class)
 *   - AI_REPLY_DONE      → react_yes (followup: previous idle/dance)
 *   - MANUAL             → react_yes
 *   - ipc.mascot.mood_change → puff_particle (followup: idle_breathe @500ms)
 *   - unknown subtype    → null
 *   - malformed          → null
 *
 * Beat-lock plumbing is asserted by Test 10 — dispatcher must read
 * bpmConfidence from currentSnapshot and pass it into planTransition so
 * dance_hard schedules-for-downbeat at conf≥0.6 vs switch_now at <0.6.
 */

import { describe, expect, it } from "vitest";

import { dispatchEvent } from "./event-dispatcher.js";
import { initialMachineState, applyTransition, planTransition } from "./state-machine.js";

const T0 = 1_000_000;

const HIGH_CONF_SNAP = {
  bpm: 120,
  bpm_confidence: 0.85,
  downbeat_phase: 0.5,
  mood: "hype-man",
};
const LOW_CONF_SNAP = {
  bpm: 120,
  bpm_confidence: 0.4,
  downbeat_phase: 0.5,
  mood: "hype-man",
};
const ZERO_SNAP = {
  bpm: 0,
  bpm_confidence: 0,
  downbeat_phase: 0,
  mood: "hype-man",
};

describe("dispatchEvent — event taxonomy", () => {
  it("Test 1: PHASE→drop → switch_now or schedule for dance_hard (beat-locked when conf≥0.6)", () => {
    const m = initialMachineState(T0);
    const message = {
      type: "event",
      subtype: "PHASE",
      payload: { from: "build", to: "drop" },
    };
    const result = dispatchEvent(m, message, T0 + 10, HIGH_CONF_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("dance_hard");
    // bpm=120, conf=0.85, phase=0.5 → schedule_for_downbeat (~1000ms)
    expect(result!.plan.action).toBe("schedule_for_downbeat");
  });

  it("Test 2: PHASE→silent → switch_now for idle_breathe", () => {
    const m = initialMachineState(T0);
    const message = {
      type: "event",
      subtype: "PHASE",
      payload: { from: "groove", to: "silent" },
    };
    const result = dispatchEvent(m, message, T0 + 10, ZERO_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("idle_breathe");
    expect(result!.plan.action).toBe("switch_now");
  });

  it("Test 3: TRACK_CHANGE → react_surprised + followup idle_bop_to_beat_energetic ~800ms", () => {
    const m = initialMachineState(T0);
    const message = {
      type: "event",
      subtype: "TRACK_CHANGE",
      payload: { title: "Some Track", deck: "A" },
    };
    const result = dispatchEvent(m, message, T0 + 10, HIGH_CONF_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("react_surprised");
    expect(result!.plan.action).toBe("switch_now");
    expect(result!.followup).toBeDefined();
    expect(result!.followup!.state).toBe("idle_bop_to_beat_energetic");
    // ~800ms react clip duration default (Plan 13-06 conservative).
    expect(result!.followup!.afterMs).toBeCloseTo(800, -2);
  });

  it("Test 4: AI_GENERATING_REPLY → talk_loop (interrupt-class outranks dance)", () => {
    // Start in dance_hard (forced, no beat-lock signals).
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "dance_hard", trigger: "drop" }, T0 + 5),
      T0 + 5,
    );
    expect(m.current).toBe("dance_hard");
    const message = { type: "event", subtype: "AI_GENERATING_REPLY", payload: {} };
    const result = dispatchEvent(m, message, T0 + 10, ZERO_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("talk_loop");
    expect(result!.plan.action).toBe("switch_now");
  });

  it("Test 5: AI_REPLY_DONE → react_yes + followup back to prior dance/idle", () => {
    // Start in dance_hard, then escalate to talk_loop (AI is speaking).
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "dance_hard", trigger: "drop" }, T0 + 5),
      T0 + 5,
    );
    m = applyTransition(
      m,
      planTransition(m, { state: "talk_loop", trigger: "ai_generating_reply" }, T0 + 10),
      T0 + 10,
    );
    expect(m.current).toBe("talk_loop");
    // AI finishes — should react_yes and then RETURN to dance_hard.
    const message = { type: "event", subtype: "AI_REPLY_DONE", payload: {} };
    const result = dispatchEvent(m, message, T0 + 20, ZERO_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("react_yes");
    expect(result!.plan.action).toBe("switch_now");
    expect(result!.followup).toBeDefined();
    // Plan 13-06 contract: followup returns to the state that was active
    // BEFORE talk_loop interrupted — the dispatcher must track this via
    // the dance/idle hint from MachineState OR from a passed-in "previous"
    // slot. For test purposes we accept either dance_hard or idle_bop_to_beat_energetic
    // (the implementation may take either the truly-prior or a safe idle default).
    expect(["dance_hard", "idle_bop_to_beat_energetic", "idle_breathe"]).toContain(
      result!.followup!.state,
    );
  });

  it("Test 6: MANUAL → react_yes (switch_now, no followup needed)", () => {
    const m = initialMachineState(T0);
    const message = { type: "event", subtype: "MANUAL", payload: {} };
    const result = dispatchEvent(m, message, T0 + 10, ZERO_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("react_yes");
    expect(result!.plan.action).toBe("switch_now");
  });

  it("Test 7: ipc.mascot.mood_change → puff_particle + followup idle_breathe @500ms", () => {
    const m = initialMachineState(T0);
    const message = {
      type: "ipc.mascot.mood_change",
      payload: { mood: "teacher", previous_mood: "hype-man" },
    };
    const result = dispatchEvent(m, message, T0 + 10, ZERO_SNAP);
    expect(result).not.toBeNull();
    expect(result!.plan.target).toBe("puff_particle");
    expect(result!.plan.action).toBe("switch_now");
    expect(result!.followup).toBeDefined();
    expect(result!.followup!.state).toBe("idle_breathe");
    expect(result!.followup!.afterMs).toBe(500);
  });

  it("Test 8: unknown subtype → null (silent, no exception)", () => {
    const m = initialMachineState(T0);
    const message = { type: "event", subtype: "SOMETHING_NEW", payload: {} };
    expect(() => dispatchEvent(m, message, T0 + 10, ZERO_SNAP)).not.toThrow();
    const result = dispatchEvent(m, message, T0 + 10, ZERO_SNAP);
    expect(result).toBeNull();
  });

  it("Test 9: malformed message → null (no throw, no listener call)", () => {
    const m = initialMachineState(T0);
    // missing `type` field entirely
    expect(() => dispatchEvent(m, { foo: "bar" }, T0 + 10, ZERO_SNAP)).not.toThrow();
    expect(dispatchEvent(m, { foo: "bar" }, T0 + 10, ZERO_SNAP)).toBeNull();
    // not even an object
    expect(dispatchEvent(m, null, T0 + 10, ZERO_SNAP)).toBeNull();
    expect(dispatchEvent(m, "not-an-object", T0 + 10, ZERO_SNAP)).toBeNull();
    expect(dispatchEvent(m, 42, T0 + 10, ZERO_SNAP)).toBeNull();
  });

  it("Test 10: beat-lock conditional — dance_hard schedule@conf=0.85, switch_now@conf=0.4", () => {
    const m = initialMachineState(T0);
    const dropMsg = {
      type: "event",
      subtype: "PHASE",
      payload: { from: "build", to: "drop" },
    };
    const high = dispatchEvent(m, dropMsg, T0 + 10, HIGH_CONF_SNAP);
    expect(high!.plan.action).toBe("schedule_for_downbeat");
    const low = dispatchEvent(m, dropMsg, T0 + 10, LOW_CONF_SNAP);
    expect(low!.plan.action).toBe("switch_now");
  });
});
