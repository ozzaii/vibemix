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
  music: 0,
  voice: 0,
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
      // The fixture frame carries music/voice NESTED as { rms, peak }
      // (the live ws frame carries them flat — both feed the same numeric
      // SnapshotSlice fields). Read the nested `.rms`, default to prior.
      const nestedRms = (v: unknown, prior: number): number => {
        if (typeof v !== "object" || v === null) return prior;
        const rms = (v as { rms?: unknown }).rms;
        return typeof rms === "number" ? rms : prior;
      };
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
        music: nestedRms(m.music, snapshot.music),
        voice: nestedRms(m.voice, snapshot.voice),
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

  // Phase 56 / LIVE-05a — the discriminating held-mode assertion. The
  // auto-runner above proves dance_hard is present (positive); this proves
  // the contradictory quiet drop fires NO new transition after it (the held
  // behaviour the guard exists for). Without the guard, the t=1100 quiet
  // PHASE→drop would re-issue dance_hard — but more importantly any future
  // regression that swapped the guard for an unconditional mode flip would
  // surface here as an extra transition past the contradictory frame.
  it("anti_slop_drop_quiet — quiet drop fires no transition after the seed (held)", () => {
    const trace = (traces.traces as Trace[]).find(
      (t) => t.name === "anti_slop_drop_quiet",
    )!;
    expect(trace).toBeDefined();
    const actual = replayTrace(trace);
    // Real transitions (exclude the boot seed).
    const transitions = actual.filter((a) => a.source !== "boot");
    // Exactly TWO real transitions: dance_hard@~100 (loud drop seed) and
    // idle_bop_to_beat_energetic@~600 (settle to groove). The contradictory
    // quiet PHASE→drop at 1100ms must NOT add a third.
    expect(transitions).toHaveLength(2);
    expect(transitions[0]!.state).toBe("dance_hard");
    expect(transitions[1]!.state).toBe("idle_bop_to_beat_energetic");
    // DISCRIMINATING: nothing fires at/after the quiet-drop timestamp
    // (1100ms). A broken/removed guard would re-flip to dance_hard here
    // (idle→dance is a real recorded transition) — this catches it.
    const afterContradiction = transitions.filter((a) => a.at >= 1100);
    expect(afterContradiction).toHaveLength(0);
    // The held mode after the contradiction is still the groove idle_bop.
    expect(transitions[transitions.length - 1]!.state).toBe(
      "idle_bop_to_beat_energetic",
    );
  });

  // Phase 56 / LIVE-05a (WR-01/IN-01) — the breakdown anti-slop assertion.
  // The corrected guard loosens breakdown (it no longer requires music <
  // LOW_RMS), but it MUST still reject the opposite-extreme contradiction: a
  // `phase=breakdown` arriving while the audio is at full peak loudness
  // (music >= PEAK_RMS). A real loud drop seeds dance_hard, then the
  // contradictory loud "breakdown" must be HELD — no idle_breathe fires off a
  // peak-loudness breakdown. This is the discriminating proof that the WR-01
  // loosening did NOT open an anti-slop hole.
  it("anti_slop_breakdown_at_peak — a breakdown at peak loudness fires no transition (held)", () => {
    const trace = (traces.traces as Trace[]).find(
      (t) => t.name === "anti_slop_breakdown_at_peak",
    )!;
    expect(trace).toBeDefined();
    const actual = replayTrace(trace);
    const transitions = actual.filter((a) => a.source !== "boot");
    // Exactly ONE real transition: dance_hard@~100 (loud-drop seed). The
    // contradictory loud PHASE→breakdown at 1100ms must NOT add a second.
    expect(transitions).toHaveLength(1);
    expect(transitions[0]!.state).toBe("dance_hard");
    // DISCRIMINATING: nothing fires at/after the contradictory frame (1100ms).
    // A regression that re-derived breakdown from an absolute level (or dropped
    // the >= PEAK_RMS rejection) would surface here as a spurious idle_breathe.
    const afterContradiction = transitions.filter((a) => a.at >= 1100);
    expect(afterContradiction).toHaveLength(0);
    // The held mode is still the loud-drop dance_hard.
    expect(transitions[transitions.length - 1]!.state).toBe("dance_hard");
  });

  // Phase 56 / LIVE-05a (WR-01/IN-01) — the realistic-breakdown reachability
  // assertion. A mid-energy breakdown (music=0.10, ABOVE LOW_RMS, the
  // half-of-earlier-max shape real audio produces) MUST now enter idle_breathe.
  // This is the case the OLD strict guard wrongly suppressed — the explicit
  // assertion pins that the corrected guard makes it reachable.
  it("realistic_breakdown_above_low_rms — a mid-energy breakdown enters idle_breathe", () => {
    const trace = (traces.traces as Trace[]).find(
      (t) => t.name === "realistic_breakdown_above_low_rms",
    )!;
    expect(trace).toBeDefined();
    const actual = replayTrace(trace);
    const { matched } = matchExpected(trace.expectedTransitions, actual);
    expect(matched).toBe(trace.expectedTransitions.length);
    // The breakdown@0.10 (above LOW_RMS) genuinely reaches idle_breathe — the
    // WR-01 fix. Under the pre-fix guard this would never have appeared.
    const enteredStates = new Set(actual.map((a) => a.state));
    expect(enteredStates.has("idle_breathe")).toBe(true);
    // And it lands AFTER the loud-drop dance_hard (the held-mode-broken case
    // would leave dance_hard as the terminal state instead).
    const transitions = actual.filter((a) => a.source !== "boot");
    expect(transitions[transitions.length - 1]!.state).toBe("idle_breathe");
  });

  // Phase 56 / LIVE-05a (WR-01/IN-01) — the realistic-peak reachability
  // assertion. A peak in the 0.045–0.110 band (Python's actual peak floor is
  // 0.045, NOT PEAK_RMS) MUST now enter dance_hard. This is the case the OLD
  // guard wrongly suppressed.
  it("realistic_peak_midband — a peak at 0.045–0.110 enters dance_hard", () => {
    const trace = (traces.traces as Trace[]).find(
      (t) => t.name === "realistic_peak_midband",
    )!;
    expect(trace).toBeDefined();
    const actual = replayTrace(trace);
    const { matched } = matchExpected(trace.expectedTransitions, actual);
    expect(matched).toBe(trace.expectedTransitions.length);
    const transitions = actual.filter((a) => a.source !== "boot");
    // The mid-band peak@0.06 reaches dance_hard — the WR-01 fix.
    expect(transitions[transitions.length - 1]!.state).toBe("dance_hard");
  });

  // Phase 56 / LIVE-05a (LIVE-05) — the ≥6-distinct-modes reachability proof.
  // The auto-runner above already replays six_mode_reachability and matches
  // every expectedTransition; this explicit test adds the LIVE-05a acceptance
  // assertion directly: each of the six contract modes is ENTERED from its
  // real bus event, and the walk reaches ≥4 distinct MascotStates across the
  // six phase/event steps (idle_breathe + idle_bop_to_beat_energetic each
  // cover >1 phase, so the six modes collapse to 4 distinct states + talk).
  it("six_mode_reachability — all six contract modes enter from a real bus event", () => {
    const trace = (traces.traces as Trace[]).find(
      (t) => t.name === "six_mode_reachability",
    )!;
    expect(trace).toBeDefined();
    const actual = replayTrace(trace);
    // Every expectedTransition must land (the per-step reachability proof).
    const { matched } = matchExpected(trace.expectedTransitions, actual);
    expect(matched).toBe(trace.expectedTransitions.length);
    // The six contract modes map onto these distinct entered states. Each
    // MUST appear at least once in the actual replay (proves it is reachable
    // from a real signal — the "≥6 distinct modes, each gated to a real
    // event" LIVE-05a acceptance).
    const enteredStates = new Set(actual.map((a) => a.state));
    expect(enteredStates.has("idle_breathe")).toBe(true); // silent + breakdown
    expect(enteredStates.has("idle_bop_to_beat_energetic")).toBe(true); // groove + build
    expect(enteredStates.has("dance_hard")).toBe(true); // drop (music-confirmed)
    expect(enteredStates.has("talk_loop")).toBe(true); // speaking
    // Six phase/event steps collapse to ≥4 distinct entered states (excluding
    // the boot seed). idle_breathe + idle_bop each carry two phases.
    const nonBoot = new Set(
      actual.filter((a) => a.source !== "boot").map((a) => a.state),
    );
    expect(nonBoot.size).toBeGreaterThanOrEqual(4);
  });

  // Phase 56 / LIVE-05a — speaking overrides music (the talk-block proof).
  // The auto-runner above replays speaking_overrides_music and matches its
  // positive expectedTransitions (dance_hard -> talk_loop -> react_yes); this
  // explicit test adds the DISCRIMINATING held assertion (mirroring
  // anti_slop_drop_quiet + talk_blocks_dance): the music PHASE->groove DURING
  // talk records NO new transition — talk_loop persists. A regression that
  // removed the block rule would surface here as an idle/groove transition
  // between the talk and the AI_REPLY_DONE.
  it("speaking_overrides_music — music PHASE during talk is denied (held)", () => {
    const trace = (traces.traces as Trace[]).find(
      (t) => t.name === "speaking_overrides_music",
    )!;
    expect(trace).toBeDefined();
    const actual = replayTrace(trace);
    const transitions = actual.filter((a) => a.source !== "boot");
    // The recorded transitions are EXACTLY: dance_hard (loud-drop seed),
    // talk_loop (AI speaks), react_yes (AI done). The groove PHASE at t=450
    // DURING talk must NOT add a fourth — it is blocked_by_talk.
    expect(transitions).toHaveLength(3);
    expect(transitions[0]!.state).toBe("dance_hard");
    expect(transitions[1]!.state).toBe("talk_loop");
    expect(transitions[2]!.state).toBe("react_yes");
    // DISCRIMINATING: between the talk-enter (t=200) and the AI_REPLY_DONE
    // (t=600), NO transition fires — the spurious music PHASE->groove at
    // t=450 is denied, so talk_loop holds across the whole talk window.
    const duringTalk = transitions.filter((a) => a.at > 200 && a.at < 600);
    expect(duringTalk).toHaveLength(0);
    // No groove/idle state ever appears DURING the talk window (the
    // speaking-overrides-music acceptance — UI-SPEC speaking row).
    const idleDuringTalk = actual.filter(
      (a) =>
        a.at > 200 &&
        a.at < 600 &&
        (STATE_CLASS[a.state] === "idle" || STATE_CLASS[a.state] === "dance"),
    );
    expect(idleDuringTalk).toHaveLength(0);
  });

  // Phase 56 / LIVE-05a — mood is a variant TINT, not a mode (Pitfall 5).
  // mood lives on the SnapshotSlice ref and drives WHICH variant the renderer
  // tints — it does NOT branch the dispatcher's mode selection. A snapshot
  // frame (mood-carrying) is a state-READER: it returns null from dispatchEvent
  // (no transition), exactly like any other snapshot. Two snapshots that differ
  // ONLY in mood produce the SAME (null) dispatch result — the dispatcher does
  // not select a different mode based on mood.
  it("mood is a tint, not a mode — a mood-only snapshot frame produces no transition", () => {
    const m = initialMachineState(0);
    const hypeSnap: SnapshotSlice = {
      bpm: 120,
      bpm_confidence: 0.4,
      downbeat_phase: 0.5,
      mood: "hype-man",
      music: 0.3,
      voice: 0,
    };
    const coachSnap: SnapshotSlice = { ...hypeSnap, mood: "coach" };
    // A snapshot frame is a state-READER — dispatchEvent returns null (no
    // transition) regardless of the mood it carries.
    const hypeFrame = { type: "snapshot", mood: "hype-man" };
    const coachFrame = { type: "snapshot", mood: "coach" };
    expect(dispatchEvent(m, hypeFrame, 100, hypeSnap)).toBeNull();
    expect(dispatchEvent(m, coachFrame, 100, coachSnap)).toBeNull();
    // And a real event dispatched with two mood-differing snapshots picks the
    // SAME target mode — mood does not branch the mode selection.
    const phaseDrop = {
      type: "event",
      subtype: "PHASE",
      payload: { from: "build", to: "drop" },
    };
    const underHype = dispatchEvent(m, phaseDrop, 100, hypeSnap);
    const underCoach = dispatchEvent(m, phaseDrop, 100, coachSnap);
    expect(underHype!.plan.target).toBe("dance_hard");
    expect(underCoach!.plan.target).toBe("dance_hard");
    expect(underHype!.plan.target).toBe(underCoach!.plan.target);
  });

  // Phase 56 / LIVE-05 — emotion is a finer nudge; emotion == null is a no-op.
  // The dispatcher has NO emotion branch — emotion (when present) is a renderer
  // eye/brow nudge layered on the mood tint, never a mode selector. A frame
  // carrying emotion: null (or no emotion at all) must produce NO transition
  // (backward-compatible with the pre-emotion Three.js rig contract).
  it("emotion == null is a no-op — an emotion-only/null-emotion frame produces no transition", () => {
    const m = initialMachineState(0);
    const snap: SnapshotSlice = {
      bpm: 120,
      bpm_confidence: 0.4,
      downbeat_phase: 0.5,
      mood: "hype-man",
      music: 0.3,
      voice: 0,
    };
    // A snapshot frame carrying emotion: null — the dispatcher has no emotion
    // branch, so a null (or any) emotion is silently a no-op (returns null).
    const nullEmotionFrame = { type: "snapshot", emotion: null };
    expect(dispatchEvent(m, nullEmotionFrame, 100, snap)).toBeNull();
    // An explicit emotion value is ALSO a no-op at the dispatcher (it's a
    // renderer nudge, not a mode) — proving emotion never branches the FSM.
    const hypedEmotionFrame = { type: "snapshot", emotion: "hyped" };
    expect(dispatchEvent(m, hypedEmotionFrame, 100, snap)).toBeNull();
  });

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

// ── Phase 56 / LIVE-05a — SnapshotSlice carries music/voice ───────────────
//
// The live ws frame broadcasts music/voice as FLAT floats; the fixture frame
// carries them NESTED as { rms, peak }. Both feed the SAME SnapshotSlice
// numeric fields. The replay harness must read the nested fixture shape so
// the Phase-56 music-confirmation guard (Task 2) can see the level.
describe("Phase 56 — SnapshotSlice carries music/voice (LIVE-05a)", () => {
  it("the DEFAULT_SNAPSHOT declares music/voice with a 0 default", () => {
    // The guard never sees `undefined` — music/voice default to 0.
    expect(DEFAULT_SNAPSHOT.music).toBe(0);
    expect(DEFAULT_SNAPSHOT.voice).toBe(0);
  });

  it("the harness threads nested music.rms / voice.rms into the SnapshotSlice", () => {
    // A snapshot frame carrying nested music:{rms} drives a level-gated
    // PHASE→drop the same tick: dance_hard must land, proving the harness
    // read music.rms (≥ PEAK_RMS) off the nested shape. (Pre-Task-2 the
    // guard is a no-op, so this also stays green after the guard lands.)
    const trace: Trace = {
      name: "harness_reads_nested_music",
      criterion: 5,
      description: "harness threads nested music.rms",
      messages: [
        {
          t: 0,
          msg: {
            type: "snapshot",
            phase: "build",
            bpm: 120,
            bpm_confidence: 0.4,
            downbeat_phase: 0.5,
            mood: "hype-man",
            music: { rms: 0.3, peak: 0.5 },
            voice: { rms: 0.0, peak: 0.0 },
          },
        },
        {
          t: 100,
          msg: {
            type: "event",
            subtype: "PHASE",
            payload: { from: "build", to: "drop" },
          },
        },
      ],
      expectedTransitions: [{ after_t: 100, state: "dance_hard" }],
    };
    const actual = replayTrace(trace);
    const { matched } = matchExpected(trace.expectedTransitions, actual);
    expect(matched).toBe(1);
  });
});
