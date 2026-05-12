/* Phase 13 Plan 04 — state-machine.ts vitest spec (Task 2, 12 tests, TDD GREEN).
 *
 * Pure-function discipline: the state machine does NOT call Date.now() or
 * setTimeout. `now` is always passed in. Tests use literal numbers for full
 * determinism — no clock mocking needed.
 *
 * Tests mirror the plan's 12 cases (CONTEXT Area 3 priority + Open Q 4
 * beat-lock 0.6 threshold + Open Q 5 idle-sleep 300s timeout).
 */

import { describe, expect, it } from "vitest";

import {
  applyTransition,
  initialMachineState,
  planTransition,
  tickIdleTimeout,
} from "./state-machine.js";

const T0 = 1_000_000; // arbitrary base timestamp

describe("initialMachineState", () => {
  it("Test 1: starts at idle_breathe / class=idle / pendingSwitch=null", () => {
    const m = initialMachineState(T0);
    expect(m.current).toBe("idle_breathe");
    expect(m.currentClass).toBe("idle");
    expect(m.pendingSwitch).toBeNull();
    expect(m.since).toBe(T0);
    expect(m.lastEventAt).toBe(T0);
    expect(m.idleTimeoutMs).toBe(300_000);
  });
});

describe("planTransition — priority rules", () => {
  it("Test 2: talk_loop while in idle → switch_now (talk outranks idle)", () => {
    const m = initialMachineState(T0);
    const plan = planTransition(
      m,
      { state: "talk_loop", trigger: "ai_generating_reply" },
      T0 + 100,
    );
    expect(plan.action).toBe("switch_now");
    expect(plan.target).toBe("talk_loop");
  });

  it("Test 3: dance_a while in talk_loop → deny (talk blocks lower)", () => {
    // Boot, escalate to talk_loop, then try dance — must be denied.
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "talk_loop", trigger: "ai_generating_reply" }, T0 + 10),
      T0 + 10,
    );
    const plan = planTransition(
      m,
      { state: "dance_a", trigger: "phase_change" },
      T0 + 20,
    );
    expect(plan.action).toBe("deny");
    expect(plan.reason).toContain("talk");
  });

  it("Test 10: puff_particle while in talk_loop → switch_now (effect outranks talk)", () => {
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "talk_loop", trigger: "ai_generating_reply" }, T0 + 10),
      T0 + 10,
    );
    const plan = planTransition(
      m,
      { state: "puff_particle", trigger: "mood_swap" },
      T0 + 20,
    );
    expect(plan.action).toBe("switch_now");
    expect(plan.target).toBe("puff_particle");
  });

  it("Test 11: react_yes while in dance_hard → switch_now (react outranks dance)", () => {
    // Start in dance_hard (immediate switch since no bpm fields).
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "dance_hard", trigger: "drop" }, T0 + 10),
      T0 + 10,
    );
    expect(m.current).toBe("dance_hard");
    const plan = planTransition(
      m,
      { state: "react_yes", trigger: "ai_reply_done" },
      T0 + 20,
    );
    expect(plan.action).toBe("switch_now");
    expect(plan.target).toBe("react_yes");
  });
});

describe("planTransition — beat-locked entry", () => {
  it("Test 4: dance_hard bpm=120 confidence=0.85 phase=0.5 → schedule_for_downbeat ~1000ms", () => {
    const m = initialMachineState(T0);
    const plan = planTransition(
      m,
      {
        state: "dance_hard",
        trigger: "drop",
        bpm: 120,
        bpmConfidence: 0.85,
        downbeatPhase: 0.5,
      },
      T0 + 100,
    );
    expect(plan.action).toBe("schedule_for_downbeat");
    expect(plan.target).toBe("dance_hard");
    // msPerBar = (60/120) * 4 * 1000 = 2000ms; half-bar remaining = 1000ms.
    expect(plan.delayMs).toBeCloseTo(1000, 0);
    expect(plan.blendMs).toBe(300);
  });

  it("Test 5: dance_hard bpm=120 confidence=0.4 → switch_now (below 0.6 threshold)", () => {
    const m = initialMachineState(T0);
    const plan = planTransition(
      m,
      {
        state: "dance_hard",
        trigger: "drop",
        bpm: 120,
        bpmConfidence: 0.4,
        downbeatPhase: 0.5,
      },
      T0 + 100,
    );
    expect(plan.action).toBe("switch_now");
  });

  it("Test 6: dance_hard bpm=120 confidence=0.85 phase=0.99 → switch_now (already on boundary)", () => {
    const m = initialMachineState(T0);
    const plan = planTransition(
      m,
      {
        state: "dance_hard",
        trigger: "drop",
        bpm: 120,
        bpmConfidence: 0.85,
        downbeatPhase: 0.99,
      },
      T0 + 100,
    );
    // msUntilDownbeat = (1 - 0.99) * 2000 = 20ms < 30 → fall through to switch_now
    expect(plan.action).toBe("switch_now");
  });
});

describe("tickIdleTimeout", () => {
  it("Test 7: in idle class, now - lastEventAt = 300_001ms → returns 'sleep'", () => {
    const m = initialMachineState(T0);
    // m.lastEventAt = T0. now = T0 + 300_001 → elapsed 300_001ms (just over).
    const result = tickIdleTimeout(m, T0 + 300_001);
    expect(result).toBe("sleep");
  });

  it("Test 8: in dance_hard, regardless of elapsed time → returns null", () => {
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "dance_hard", trigger: "drop" }, T0 + 10),
      T0 + 10,
    );
    expect(m.currentClass).toBe("dance");
    const result = tickIdleTimeout(m, T0 + 600_000);
    expect(result).toBeNull();
  });

  it("Test 9: in idle, elapsed=1000ms → returns null (below 300s threshold)", () => {
    const m = initialMachineState(T0);
    const result = tickIdleTimeout(m, T0 + 1000);
    expect(result).toBeNull();
  });
});

describe("applyTransition", () => {
  it("Test 12: switch_now updates current/class/since/lastEventAt; pendingSwitch null", () => {
    const m = initialMachineState(T0);
    const plan = planTransition(
      m,
      { state: "talk_loop", trigger: "ai_generating_reply", blendMs: 250 },
      T0 + 50,
    );
    const m2 = applyTransition(m, plan, T0 + 60);
    expect(m2.current).toBe("talk_loop");
    expect(m2.currentClass).toBe("talk");
    expect(m2.since).toBe(T0 + 60);
    expect(m2.lastEventAt).toBe(T0 + 60);
    expect(m2.pendingSwitch).toBeNull();
  });

  it("Test 12b (bonus): schedule_for_downbeat sets pendingSwitch without changing current", () => {
    const m = initialMachineState(T0);
    const plan = planTransition(
      m,
      {
        state: "dance_hard",
        trigger: "drop",
        bpm: 120,
        bpmConfidence: 0.85,
        downbeatPhase: 0.25,
        blendMs: 400,
      },
      T0 + 100,
    );
    expect(plan.action).toBe("schedule_for_downbeat");
    const m2 = applyTransition(m, plan, T0 + 100);
    // Current state stays where it was (idle_breathe), but pendingSwitch is set.
    expect(m2.current).toBe("idle_breathe");
    expect(m2.pendingSwitch).not.toBeNull();
    expect(m2.pendingSwitch?.state).toBe("dance_hard");
    expect(m2.pendingSwitch?.blendMs).toBe(400);
    // delayMs = (1 - 0.25) * 2000 = 1500ms; atTimestamp = T0 + 100 + 1500
    expect(m2.pendingSwitch?.atTimestamp).toBeCloseTo(T0 + 100 + 1500, 0);
    // lastEventAt updates even for scheduled — it counts as activity.
    expect(m2.lastEventAt).toBe(T0 + 100);
  });

  it("Test 12c (bonus): deny leaves machine unchanged", () => {
    let m = initialMachineState(T0);
    m = applyTransition(
      m,
      planTransition(m, { state: "talk_loop", trigger: "ai_generating_reply" }, T0 + 10),
      T0 + 10,
    );
    const before = { ...m };
    const plan = planTransition(
      m,
      { state: "idle_breathe", trigger: "phase_change" },
      T0 + 20,
    );
    expect(plan.action).toBe("deny");
    const after = applyTransition(m, plan, T0 + 20);
    expect(after).toEqual(before);
  });
});
