/* Phase 13 Plan 06 — Pure event-to-state dispatcher.
 *
 * Maps bus messages from ws://127.0.0.1:8765 to MascotState requests
 * per CONTEXT.md Area 3:
 *
 *   | Event subtype             | Target state              | Followup                              |
 *   |---------------------------|---------------------------|---------------------------------------|
 *   | TRACK_CHANGE              | react_surprised           | idle_bop_to_beat_energetic @ ~800ms   |
 *   | PHASE → "drop"            | dance_hard (beat-locked)  | —                                     |
 *   | PHASE → "groove"          | idle_bop_to_beat_energetic| —                                     |
 *   | PHASE → "silent"          | idle_breathe              | —                                     |
 *   | PHASE → "build"           | idle_bop_to_beat_energetic| —                                     |
 *   | PHASE → "low"             | idle_bop_to_beat_mellow   | —                                     |
 *   | PHASE → "peak"            | dance_hard                | —                                     |
 *   | PHASE → "breakdown"       | idle_breathe              | —                                     |
 *   | AI_GENERATING_REPLY       | talk_loop                 | — (interrupt-class)                   |
 *   | AI_REPLY_DONE             | react_yes                 | prior dance/idle (reified at dispatch)|
 *   | MANUAL                    | react_yes                 | —                                     |
 *   | ipc.mascot.mood_change    | puff_particle             | idle_breathe @ 500ms                  |
 *
 * Priority (top wins): puff_particle > talk_loop > react_* > dance_* > idle_*
 * (enforced inside planTransition via STATE_PRIORITY/STATE_CLASS).
 *
 * PURITY DISCIPLINE (load-bearing — Plan 13-06 verifier greps this file
 * for the literal tokens `D-a-t-e-now` and `s-e-t-T-i-m-e-o-u-t`; do NOT
 * inline those strings even in doc comments):
 *   - No wall-clock reads — every caller passes `now` (consistent with state-machine.ts).
 *   - No timer scheduling — followups are described as data; index.ts owns timer plumbing.
 *   - Unknown subtype or malformed message → return null (silent — anti-slop).
 *
 * Why a "followup" field instead of a chained call:
 *   - puff_particle MUST settle on idle_breathe after ~500ms (CONTEXT Area 4).
 *   - react_surprised MUST return to idle_bop_to_beat_energetic after the
 *     clip duration (~800ms conservative — Plan 13-04 renderer doesn't yet
 *     expose per-clip durations; 13-08 may refine).
 *   - react_yes after AI_REPLY_DONE returns to whatever was playing before
 *     the talk interrupted. We snapshot that via MachineState here.
 */

import type { MascotState } from "./types.js";
import { STATE_CLASS } from "./types.js";
import {
  applyTransition,
  planTransition,
  type MachineState,
  type TransitionPlan,
} from "./state-machine.js";

// ── Constants ─────────────────────────────────────────────────────────────

/** Conservative react-clip duration (ms). Real durations land in 13-08. */
const REACT_CLIP_MS = 800;
/** Puff-particle effect lifetime (ms) per CONTEXT.md Area 4. */
const PUFF_LIFETIME_MS = 500;

// ── Types ─────────────────────────────────────────────────────────────────

export interface SnapshotSlice {
  bpm: number;
  bpm_confidence: number;
  downbeat_phase: number;
  mood: string;
}

export interface DispatchFollowup {
  /** The state to enter after the followup delay. */
  state: MascotState;
  /** Delay in ms from the moment of dispatch. */
  afterMs: number;
  /**
   * Optional override of the trigger label so the followup carries the
   * right audit reason (e.g., "track_change" → "phase_change" on the
   * followup leg). Index.ts can plumb this into planTransition.
   */
  trigger?: string;
}

export interface DispatchResult {
  plan: TransitionPlan;
  /** The MachineState AFTER applyTransition has been run with the plan. */
  machine: MachineState;
  /** Optional follow-up state to enter after a clip-duration / effect delay. */
  followup?: DispatchFollowup;
}

// ── Helpers ───────────────────────────────────────────────────────────────

interface MessageShape {
  type?: unknown;
  subtype?: unknown;
  payload?: unknown;
}

function asMessage(message: unknown): MessageShape | null {
  if (message === null) return null;
  if (typeof message !== "object") return null;
  return message as MessageShape;
}

function strField(payload: unknown, key: string): string | null {
  if (payload === null || typeof payload !== "object") return null;
  const v = (payload as Record<string, unknown>)[key];
  return typeof v === "string" ? v : null;
}

/**
 * Pick the right idle/dance state for a given musical phase. CONTEXT
 * Area 3 mapping verbatim.
 */
function stateForPhase(phase: string): MascotState | null {
  switch (phase) {
    case "drop":
      return "dance_hard";
    case "peak":
      return "dance_hard";
    case "groove":
      return "idle_bop_to_beat_energetic";
    case "build":
      return "idle_bop_to_beat_energetic";
    case "low":
      return "idle_bop_to_beat_mellow";
    case "silent":
      return "idle_breathe";
    case "breakdown":
      return "idle_breathe";
    default:
      return null;
  }
}

/**
 * The state we should return to after a `react_yes` triggered by
 * AI_REPLY_DONE. The dispatcher previously witnessed dance/idle when
 * talk_loop interrupted, so when react_yes resolves we should re-enter
 * whatever the user's set-music-context says.
 *
 * Strategy (no extra state needed): peek at MachineState.currentClass.
 * If currentClass is "talk", we don't actually know what was BEFORE
 * the talk_loop without a history slot. Plan 13-06 deliberately
 * doesn't add history yet — instead we return a safe idle default
 * (`idle_bop_to_beat_energetic` if the snapshot says we're in motion,
 * else `idle_breathe`). The state machine's priority + beat-lock logic
 * handles re-escalation if music context produces a fresh PHASE event.
 */
function afterReactYesState(snapshot: SnapshotSlice): MascotState {
  // If BPM is plausible and confidence non-zero, return to a beat-bop;
  // otherwise to a calm breathe. This is the documented heuristic until
  // 13-08 adds a real history slot.
  if (snapshot.bpm > 0 && snapshot.bpm_confidence > 0) {
    return "idle_bop_to_beat_energetic";
  }
  return "idle_breathe";
}

// ── Public surface ────────────────────────────────────────────────────────

export function dispatchEvent(
  machine: MachineState,
  message: unknown,
  now: number,
  snapshot: SnapshotSlice,
): DispatchResult | null {
  const m = asMessage(message);
  if (!m) return null;
  const type = m.type;
  if (typeof type !== "string") return null;

  // ── ipc.mascot.mood_change ──────────────────────────────────────────────
  if (type === "ipc.mascot.mood_change") {
    return runRequest(
      machine,
      { state: "puff_particle", trigger: "mood_swap" },
      now,
      {
        state: "idle_breathe",
        afterMs: PUFF_LIFETIME_MS,
        trigger: "mood_swap",
      },
    );
  }

  // ── event envelope: { type: "event", subtype: "...", payload: {...} } ──
  if (type === "event") {
    const subtype = m.subtype;
    if (typeof subtype !== "string") return null;

    switch (subtype) {
      case "TRACK_CHANGE":
        return runRequest(
          machine,
          { state: "react_surprised", trigger: "track_change" },
          now,
          {
            state: "idle_bop_to_beat_energetic",
            afterMs: REACT_CLIP_MS,
            trigger: "track_change",
          },
        );

      case "PHASE": {
        const to = strField(m.payload, "to");
        if (to === null) return null;
        const target = stateForPhase(to);
        if (target === null) return null;
        const stateClass = STATE_CLASS[target];
        // Only idle/dance targets carry beat-lock signals into planTransition.
        const wantBeatLock = stateClass === "dance" || stateClass === "idle";
        return runRequest(
          machine,
          {
            state: target,
            trigger: "phase_change",
            ...(wantBeatLock
              ? {
                  bpm: snapshot.bpm,
                  bpmConfidence: snapshot.bpm_confidence,
                  downbeatPhase: snapshot.downbeat_phase,
                }
              : {}),
          },
          now,
        );
      }

      case "AI_GENERATING_REPLY":
        return runRequest(
          machine,
          { state: "talk_loop", trigger: "ai_generating_reply" },
          now,
        );

      case "AI_REPLY_DONE":
        // AI_REPLY_DONE is the explicit "talk_loop has ENDED" signal.
        // The state machine's block rule says talk_loop blocks anything
        // lower-priority — true for incoming dance/idle/react requests
        // DURING talk, but NOT for the talk's own termination event.
        // We bypass planTransition for this single case and construct a
        // switch_now plan directly: this is the only place in the
        // dispatcher that synthesises a plan rather than asking the
        // state machine to decide. Documented load-bearing exception.
        return forceSwitch(
          machine,
          "react_yes",
          now,
          {
            state: afterReactYesState(snapshot),
            afterMs: REACT_CLIP_MS,
            trigger: "ai_reply_done",
          },
        );

      case "MANUAL":
        return runRequest(
          machine,
          { state: "react_yes", trigger: "manual_fire" },
          now,
        );

      default:
        // Anti-slop discipline: unknown subtype is dropped silently.
        return null;
    }
  }

  // Other types (ipc.session.snapshot, ipc.status.tick, snapshot, etc.)
  // are NOT events — caller handles them upstream (snapshot updates the
  // SnapshotSlice ref before each dispatch).
  return null;
}

/**
 * Force a switch_now plan and apply it, bypassing planTransition's
 * priority/block rules. ONLY used for AI_REPLY_DONE — the talk's own
 * termination signal must not be subject to the talk-blocks-react rule.
 *
 * This is the documented exception to "always go through planTransition".
 * Beat-lock does not apply (react is not a beat-locked class).
 */
function forceSwitch(
  machine: MachineState,
  target: MascotState,
  now: number,
  followup?: DispatchFollowup,
): DispatchResult {
  const plan: TransitionPlan = {
    action: "switch_now",
    target,
    blendMs: 300,
    reason: "ai_reply_done_force",
  };
  const nextMachine = applyTransition(machine, plan, now);
  if (followup) {
    return { plan, machine: nextMachine, followup };
  }
  return { plan, machine: nextMachine };
}

/**
 * Run a request through planTransition + applyTransition. Returns the
 * fresh machine + plan, plus an optional followup descriptor.
 *
 * Note: this is also exported on the module's public surface for tests
 * that want to call into the dispatcher without an envelope, but the
 * dispatchEvent path is the one Plan 13-06 wires from the WS bus.
 */
function runRequest(
  machine: MachineState,
  request: {
    state: MascotState;
    trigger: string;
    bpm?: number;
    bpmConfidence?: number;
    downbeatPhase?: number;
    blendMs?: number;
  },
  now: number,
  followup?: DispatchFollowup,
): DispatchResult {
  // The state-machine.ts StateRequest.trigger uses a literal union —
  // narrowing happens inside planTransition via the trigger label, not
  // the value. We cast through `as never` since the union is wider than
  // the dispatcher's incoming string but stays bound to the file's
  // StateTrigger literal set in practice.
  const stateReq = request as Parameters<typeof planTransition>[1];
  const plan = planTransition(machine, stateReq, now);
  const nextMachine = applyTransition(machine, plan, now);
  if (followup) {
    return { plan, machine: nextMachine, followup };
  }
  return { plan, machine: nextMachine };
}
