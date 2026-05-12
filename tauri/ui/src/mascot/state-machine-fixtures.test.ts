/* Phase 13 Plan 08 — state-machine fixture replay harness.
 *
 * Loads __fixtures__/event-traces.json and replays each trace through
 * dispatchEvent + applyTransition deterministically, asserting that the
 * resulting state-machine transitions match the documented expectations
 * verbatim from CONTEXT.md Area 3.
 *
 * Tolerance: the trace's `expectedTransitions[].after_t` is matched
 * within ±100ms (covers beat-lock jitter at 120-128 BPM; one bar at
 * 120bpm = 2000ms, so ±100ms = ±5% drift tolerance).
 *
 * This harness is PURE — no Three.js, no DOM, no fetch. Runs in vitest
 * jsdom env in <50ms total.
 *
 * Why a fixture-driven replay test (separate from event-dispatcher.test.ts):
 *   - event-dispatcher.test.ts asserts ONE event at a time.
 *   - This harness asserts MULTI-EVENT sequences with timing — exercises
 *     the followup-queue plumbing AND the priority+block rules
 *     end-to-end (e.g., `talk_blocks_dance` asserts the dance request is
 *     genuinely denied; `drop_then_groove` asserts the dance→idle exit).
 *   - Same fixture is replayed Python-side by
 *     tests/integration/test_mascot_event_taxonomy_e2e.py so the
 *     dispatcher's contract is pinned across the JS/Py boundary.
 */

import { describe, expect, it } from "vitest";

import traces from "./__fixtures__/event-traces.json";
import { dispatchEvent, type SnapshotSlice } from "./event-dispatcher.js";
import {
  applyTransition,
  initialMachineState,
  planTransition,
  type MachineState,
} from "./state-machine.js";
import { STATE_CLASS, type MascotState } from "./types.js";

const TOLERANCE_MS = 100;
const DEFAULT_SNAPSHOT: SnapshotSlice = {
  bpm: 0,
  bpm_confidence: 0,
  downbeat_phase: 0,
  mood: "hype-man",
};

interface TraceMessage {
  t: number;
  msg: Record<string, unknown>;
}

interface ExpectedTransition {
  after_t: number;
  state: MascotState;
}

interface Trace {
  name: string;
  criterion: number;
  description: string;
  messages: TraceMessage[];
  expectedTransitions: ExpectedTransition[];
}

interface ActualTransition {
  /** Absolute timestamp at which the state became active. */
  at: number;
  state: MascotState;
  source: "switch_now" | "scheduled" | "boot";
}

/**
 * Replay a single trace through the state machine.
 *
 * Behaviour:
 *   - At each `messages[i].t`, if `type === "snapshot"`, update the
 *     current `SnapshotSlice` ref (bpm/conf/downbeat/mood). Snapshots
 *     do NOT trigger transitions — they are state-readers per Plan
 *     13-06's "snapshots are state-READERS, events are state-WRITERS"
 *     discipline.
 *   - Otherwise call `dispatchEvent` with the current snapshot. Apply
 *     the plan to the machine. If the plan is `schedule_for_downbeat`,
 *     `pendingSwitch` is set inside the machine; we drain it when the
 *     clock advances past `pendingSwitch.atTimestamp`. If a `followup`
 *     is returned, queue it to fire at `t + followup.afterMs`.
 *   - Advance the clock to `t = max(expected.after_t) + 100ms`, draining
 *     pending switches + followups in chronological order.
 *
 * Returns the chronological list of state-becomes-active timestamps.
 */
function replayTrace(trace: Trace): ActualTransition[] {
  // ── 1. Initialise machine + bookkeeping ────────────────────────────────
  let machine: MachineState = initialMachineState(0);
  let snapshot: SnapshotSlice = { ...DEFAULT_SNAPSHOT };
  const actual: ActualTransition[] = [
    { at: 0, state: machine.current, source: "boot" },
  ];

  // Followups: { fireAt, state, trigger }
  interface PendingFollowup {
    fireAt: number;
    state: MascotState;
    trigger: string;
  }
  const followupQueue: PendingFollowup[] = [];

  /**
   * Drain any pending machine.pendingSwitch (beat-lock scheduled) AND
   * any followupQueue entries whose fireAt has landed at-or-before `t`.
   * Re-enters planTransition so the followup honours priority + beat-lock.
   */
  function drainUpTo(t: number): void {
    let progress = true;
    while (progress) {
      progress = false;
      // Drain a beat-lock pendingSwitch if its timestamp lands at-or-before t.
      if (
        machine.pendingSwitch !== null &&
        machine.pendingSwitch.atTimestamp <= t
      ) {
        const fireAt = machine.pendingSwitch.atTimestamp;
        const target = machine.pendingSwitch.state;
        // Synthesise a switch_now plan from the pendingSwitch.
        const plan = {
          action: "switch_now" as const,
          target,
          blendMs: machine.pendingSwitch.blendMs,
          reason: "beat_locked_apply",
        };
        machine = applyTransition(machine, plan, fireAt);
        actual.push({ at: fireAt, state: target, source: "scheduled" });
        progress = true;
        continue;
      }
      // Drain the earliest followup whose fireAt has landed.
      const idx = followupQueue.findIndex((f) => f.fireAt <= t);
      if (idx >= 0) {
        const followup = followupQueue.splice(idx, 1)[0]!;
        const fireAt = followup.fireAt;
        // Re-enter planTransition so priority + beat-lock apply on the
        // followup leg (consistent with index.ts's PendingFollowup processor).
        const wantBeatLock =
          STATE_CLASS[followup.state] === "idle" ||
          STATE_CLASS[followup.state] === "dance";
        const req = {
          state: followup.state,
          // trigger is a free-string in StateRequest; the dispatcher's
          // upstream callers use the documented literal union. We cast
          // through `as never` matching event-dispatcher.ts's pattern.
          trigger: followup.trigger,
          ...(wantBeatLock
            ? {
                bpm: snapshot.bpm,
                bpmConfidence: snapshot.bpm_confidence,
                downbeatPhase: snapshot.downbeat_phase,
              }
            : {}),
        } as Parameters<typeof planTransition>[1];
        const plan = planTransition(machine, req, fireAt);
        const before = machine.current;
        machine = applyTransition(machine, plan, fireAt);
        if (plan.action === "switch_now" && plan.target && machine.current !== before) {
          actual.push({
            at: fireAt,
            state: plan.target as MascotState,
            source: "switch_now",
          });
        } else if (plan.action === "schedule_for_downbeat" && plan.target) {
          // Don't record the schedule itself — drainUpTo will pick up
          // the pendingSwitch on the next iteration if it lands within t.
        }
        progress = true;
      }
    }
  }

  // ── 2. Walk through messages chronologically ───────────────────────────
  for (const message of trace.messages) {
    const t = message.t;
    // Drain everything that should have fired before this message arrives.
    drainUpTo(t);
    const type = message.msg.type;
    if (type === "snapshot") {
      // Snapshot: update the SnapshotSlice ref. No transitions.
      const m = message.msg;
      snapshot = {
        bpm: typeof m.bpm === "number" ? m.bpm : snapshot.bpm,
        bpm_confidence:
          typeof m.bpm_confidence === "number"
            ? m.bpm_confidence
            : snapshot.bpm_confidence,
        downbeat_phase:
          typeof m.downbeat_phase === "number"
            ? m.downbeat_phase
            : snapshot.downbeat_phase,
        mood: typeof m.mood === "string" ? m.mood : snapshot.mood,
      };
      continue;
    }
    // Event envelope: dispatch through event-dispatcher.
    const before = machine.current;
    const result = dispatchEvent(machine, message.msg, t, snapshot);
    if (result === null) continue;
    machine = result.machine;
    if (result.plan.action === "switch_now" && result.plan.target && machine.current !== before) {
      actual.push({
        at: t,
        state: result.plan.target as MascotState,
        source: "switch_now",
      });
    }
    // schedule_for_downbeat: drainUpTo will pick up the pendingSwitch.
    if (result.followup) {
      followupQueue.push({
        fireAt: t + result.followup.afterMs,
        state: result.followup.state,
        trigger: result.followup.trigger ?? "followup",
      });
    }
  }

  // ── 3. Final drain past the last expected transition timestamp ────────
  const lastExpectedT =
    trace.expectedTransitions.length === 0
      ? 0
      : Math.max(...trace.expectedTransitions.map((e) => e.after_t));
  drainUpTo(lastExpectedT + TOLERANCE_MS);

  return actual;
}

/**
 * Match each expected transition against the actuals: state must be
 * present AND its timestamp within ±TOLERANCE_MS of the expected.
 *
 * Returns the count of expected transitions that were matched.
 */
function matchExpected(
  expected: ExpectedTransition[],
  actual: ActualTransition[],
): { matched: number; misses: ExpectedTransition[] } {
  const misses: ExpectedTransition[] = [];
  let matched = 0;
  for (const e of expected) {
    const hit = actual.find(
      (a) => a.state === e.state && Math.abs(a.at - e.after_t) <= TOLERANCE_MS,
    );
    if (hit) {
      matched++;
    } else {
      misses.push(e);
    }
  }
  return { matched, misses };
}

describe("state-machine fixture replay — event-traces.json", () => {
  it("loads the fixture and has ≥7 traces covering the AI-event taxonomy", () => {
    expect(traces).toBeDefined();
    expect(Array.isArray(traces.traces)).toBe(true);
    expect(traces.traces.length).toBeGreaterThanOrEqual(7);
    // Every trace has a name + messages + expectedTransitions.
    for (const t of traces.traces) {
      expect(t.name).toBeTypeOf("string");
      expect(Array.isArray(t.messages)).toBe(true);
      expect(Array.isArray(t.expectedTransitions)).toBe(true);
      expect(t.expectedTransitions.length).toBeGreaterThan(0);
    }
  });

  for (const trace of traces.traces as Trace[]) {
    it(`replays "${trace.name}" (criterion #${trace.criterion}) and matches every expectedTransition`, () => {
      const actual = replayTrace(trace);
      const { matched, misses } = matchExpected(trace.expectedTransitions, actual);
      if (misses.length > 0) {
        // Helpful diagnostic message: dump actual sequence on miss.
        const actualDump = actual
          .map((a) => `${a.at}ms→${a.state}(${a.source})`)
          .join(", ");
        const missesDump = misses
          .map((m) => `${m.after_t}ms→${m.state}`)
          .join(", ");
        throw new Error(
          `Trace "${trace.name}" missed expectedTransitions: [${missesDump}]\n` +
            `Actual sequence: [${actualDump}]`,
        );
      }
      expect(matched).toBe(trace.expectedTransitions.length);
    });
  }

  it("aggregates: every documented ROADMAP event-mapping criterion is covered by ≥1 trace", () => {
    const criteriaCovered = new Set(
      (traces.traces as Trace[]).map((t) => t.criterion),
    );
    // Criteria 4 (beat-lock), 5 (event mapping), 6 (mood swap) are the
    // ones with concrete state-machine assertions. Criteria 1/2/3 are
    // human-verified visual concerns (see MANUAL-SMOKE-CHECKLIST).
    expect(criteriaCovered.has(4)).toBe(true);
    expect(criteriaCovered.has(5)).toBe(true);
    expect(criteriaCovered.has(6)).toBe(true);
  });
});
