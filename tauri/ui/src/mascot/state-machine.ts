/* Phase 13 Plan 04 — Mascot state machine (pure functions, no three.js, no wall-clock).
 *
 * PURITY DISCIPLINE (load-bearing — verifier greps this file):
 *   - No wall-clock reads — every function takes `now: number` as a parameter.
 *   - No timers — scheduling is expressed as a `pendingSwitch` field
 *     on MachineState; the renderer's rAF loop fires it when timestamps land.
 *   - No `three` imports — this file MUST be testable in isolation under node.
 *
 * Why pure: the state machine is the most-tested layer (12+ vitest cases).
 * Locking out wall-clock + timers means literal-number tests are fully
 * deterministic without clock mocking. Plan 13-04 verify step greps this
 * file for the forbidden patterns (see CLAUDE.md note in the test file).
 *
 * Public surface (4 functions, all pure):
 *   - initialMachineState(now) → MachineState
 *   - planTransition(machine, request, now) → TransitionPlan
 *   - applyTransition(machine, plan, now) → MachineState
 *   - tickIdleTimeout(machine, now) → MascotState | null
 *
 * The flow:
 *   caller → planTransition() → TransitionPlan
 *          → applyTransition() → new MachineState
 *          → if plan.action === "switch_now": renderer.crossFadeTo(target, blendMs)
 *          → if plan.action === "schedule_for_downbeat": rAF loop watches pendingSwitch
 *          → on next rAF tick: tickIdleTimeout() may fire sleep at 5min idle
 */

import type { MascotState, MascotStateClass, StateRequest } from "./types.js";
import { STATE_CLASS, STATE_PRIORITY } from "./types.js";

// ── Types ─────────────────────────────────────────────────────────────────

/**
 * The state machine's full memory. Immutable — every state update returns
 * a new object (callers `m = applyTransition(m, plan, now)`).
 *
 * - `current` + `currentClass`: the active state and its class bucket.
 * - `since`: when did we enter `current` (ms; same clock as `now` passed
 *   into planTransition / tickIdleTimeout). Used by Plan 13-06 / future
 *   tuning logic for "how long has the mascot been idle?" diagnostics.
 * - `pendingSwitch`: when planTransition returns schedule_for_downbeat,
 *   applyTransition stores the future switch here. The renderer's rAF
 *   loop checks `now >= pendingSwitch.atTimestamp` and fires the switch.
 * - `lastEventAt`: any non-deny incoming StateRequest updates this. It's
 *   the reference timestamp for the 5-minute idle-sleep timeout.
 * - `idleTimeoutMs`: configurable but locked at 300_000 in initialMachineState
 *   per CONTEXT Open Q 5. Exposed as a field for future settings-drawer
 *   override or test parametrization.
 */
export interface MachineState {
  current: MascotState;
  currentClass: MascotStateClass;
  since: number;
  pendingSwitch:
    | { state: MascotState; atTimestamp: number; blendMs: number }
    | null;
  lastEventAt: number;
  idleTimeoutMs: number;
}

/**
 * The decision planTransition emits. The caller (typically index.ts via the
 * rAF loop or a public requestState API) applies it via applyTransition AND
 * — for `switch_now` — calls `renderer.crossFadeTo(target, blendMs)` to
 * actually drive the visible animation.
 */
export interface TransitionPlan {
  action: "switch_now" | "schedule_for_downbeat" | "deny";
  /** Set when action is switch_now or schedule_for_downbeat. */
  target?: MascotState;
  /** Crossfade duration in ms. Default 300. */
  blendMs: number;
  /** Set when action is schedule_for_downbeat. */
  delayMs?: number;
  /** Human-readable reason for audit + Plan 13-06 logging. */
  reason: string;
}

// ── Tuning constants (locked per CONTEXT) ─────────────────────────────────

/** Below this BPM confidence, we don't trust the beat — switch immediately. */
const BPM_CONFIDENCE_THRESHOLD = 0.6;
/** Default crossfade blend duration in ms. CONTEXT Area 3 → 300ms. */
const DEFAULT_BLEND_MS = 300;
/** If the next downbeat is sooner than this, treat it as "already there". */
const DOWNBEAT_PROXIMITY_MS = 30;
/** CONTEXT Open Q 5: 5 minutes of no activity in idle → sleep. */
const IDLE_TIMEOUT_DEFAULT_MS = 300_000;
/** CONTEXT Area 3: boot state. */
const BOOT_STATE: MascotState = "idle_breathe";

// ── Function 1: initial state ─────────────────────────────────────────────

/**
 * Build the boot-time MachineState. Caller picks the boot timestamp (usually
 * `performance.now()` at app start) so this stays pure.
 *
 * Why fixed boot state instead of mood-derived: Plan 13-04 boots before any
 * mood profile has loaded. Plan 13-07 will swap the idle clip when the mood
 * is known via a separate mood_swap request. CONTEXT Area 3 + the must-have
 * "Boot state should respect mood-specific idle_default if mood profile
 * already known; else default to idle_breathe" — since this plan doesn't
 * subscribe to mood signals yet (that's 13-06), we default unconditionally.
 */
export function initialMachineState(now: number): MachineState {
  return {
    current: BOOT_STATE,
    currentClass: STATE_CLASS[BOOT_STATE],
    since: now,
    pendingSwitch: null,
    lastEventAt: now,
    idleTimeoutMs: IDLE_TIMEOUT_DEFAULT_MS,
  };
}

// ── Function 2: planTransition ────────────────────────────────────────────

/**
 * Decide what to do with an incoming StateRequest. Returns one of:
 *   - "switch_now" with target + blendMs (most common path)
 *   - "schedule_for_downbeat" with delayMs (beat-locked entry)
 *   - "deny" with a reason (lower-priority request while talk/effect active)
 *
 * Rule application order (matches plan):
 *   1. Compute class of requested vs current.
 *   2. Block rule: talk/effect block strictly-lower-priority requests.
 *      react/dance/idle/explanation/misc do NOT block.
 *   3. Beat-lock rule: idle/dance targets with bpmConfidence ≥ 0.6 +
 *      a valid bpm + downbeatPhase schedule for the next downbeat. If
 *      the next downbeat is within 30ms, fall through to switch_now.
 *   4. Default: switch_now.
 *
 * Throws via TypeScript narrowing if an unknown MascotState slips in
 * (STATE_CLASS lookup returns undefined → that's a developer error and
 * we let it surface rather than silently fall back to "misc").
 */
export function planTransition(
  machine: MachineState,
  request: StateRequest,
  // `now` is reserved for future extensions (e.g., dampening rapid-fire
  // requests, or biasing planTransition by `now - machine.since`). Plan
  // 13-04 has no use for it inside planTransition, but the signature
  // matches plan/contract so callers don't need to switch shape later.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _now: number,
): TransitionPlan {
  const requestedClass = STATE_CLASS[request.state];
  if (requestedClass === undefined) {
    // Unknown state — surface, do not silently fall back. The plan
    // mandates "no silent fallbacks; throw on unknown state name."
    throw new Error(
      `planTransition: unknown MascotState '${String(request.state)}' (no STATE_CLASS entry)`,
    );
  }
  const currentClass = machine.currentClass;
  const requestedPriority = STATE_PRIORITY[requestedClass];
  const currentPriority = STATE_PRIORITY[currentClass];
  const blendMs = request.blendMs ?? DEFAULT_BLEND_MS;

  // ── Rule 2: Block rule ────────────────────────────────────────────────
  // Talk and effect classes BLOCK requests that have strictly lower priority
  // than the current class. react/dance/idle/explanation/misc do NOT block —
  // they yield to anything higher and accept anything lower as a normal
  // switch_now (because they are not "interrupt-class" themselves).
  if (
    (currentClass === "talk" || currentClass === "effect") &&
    requestedPriority < currentPriority
  ) {
    return {
      action: "deny",
      blendMs: 0,
      reason: `blocked_by_${currentClass}`,
    };
  }

  // ── Rule 3: Beat-locked entry ─────────────────────────────────────────
  // Only for idle/dance targets, only when we have all three beat signals,
  // only when bpmConfidence clears the 0.6 threshold (CONTEXT Open Q 4).
  if (
    (requestedClass === "idle" || requestedClass === "dance") &&
    typeof request.bpmConfidence === "number" &&
    request.bpmConfidence >= BPM_CONFIDENCE_THRESHOLD &&
    typeof request.bpm === "number" &&
    request.bpm > 0 &&
    typeof request.downbeatPhase === "number"
  ) {
    // msPerBar at 4/4: (60 / bpm) * 4 beats * 1000 = msPerBeat * 4
    const msPerBar = (60 / request.bpm) * 4 * 1000;
    // downbeatPhase = how far through the current bar we are (0..1).
    // Time until next bar boundary = (1 - phase) * msPerBar.
    // Clamp phase to [0,1] defensively (Plan 13-05 returns 0..1; this is
    // belt-and-braces against future drift).
    const phase = Math.max(0, Math.min(1, request.downbeatPhase));
    const msUntilDownbeat = (1 - phase) * msPerBar;

    if (msUntilDownbeat >= DOWNBEAT_PROXIMITY_MS) {
      return {
        action: "schedule_for_downbeat",
        target: request.state,
        blendMs,
        delayMs: msUntilDownbeat,
        reason: "beat_locked_entry",
      };
    }
    // else: already within 30ms of a downbeat — fall through to switch_now.
  }

  // ── Rule 4: Default ───────────────────────────────────────────────────
  return {
    action: "switch_now",
    target: request.state,
    blendMs,
    reason: "immediate_switch",
  };
}

// ── Function 3: applyTransition ───────────────────────────────────────────

/**
 * Produce the next MachineState from a plan. Immutable — never mutates
 * `machine` in place. Caller pattern:
 *   m = applyTransition(m, plan, now);
 *
 * For `schedule_for_downbeat`, the `pendingSwitch` field is set with the
 * absolute timestamp at which the switch should fire. The renderer's rAF
 * loop polls this field and emits a `switch_now`-equivalent plan when
 * `now >= pendingSwitch.atTimestamp`.
 *
 * For `deny`, we return the machine unchanged — no side effect, no
 * `lastEventAt` update (a denied request shouldn't reset the idle timer
 * — the user's "request" didn't actually do anything visible).
 */
export function applyTransition(
  machine: MachineState,
  plan: TransitionPlan,
  now: number,
): MachineState {
  if (plan.action === "deny") {
    return machine;
  }

  if (plan.action === "schedule_for_downbeat") {
    if (plan.target === undefined || plan.delayMs === undefined) {
      throw new Error(
        "applyTransition: schedule_for_downbeat plan missing target/delayMs",
      );
    }
    return {
      ...machine,
      pendingSwitch: {
        state: plan.target,
        atTimestamp: now + plan.delayMs,
        blendMs: plan.blendMs,
      },
      lastEventAt: now,
    };
  }

  // switch_now
  if (plan.target === undefined) {
    throw new Error("applyTransition: switch_now plan missing target");
  }
  const targetClass = STATE_CLASS[plan.target];
  if (targetClass === undefined) {
    throw new Error(
      `applyTransition: switch_now target '${String(plan.target)}' has no STATE_CLASS entry`,
    );
  }
  return {
    ...machine,
    current: plan.target,
    currentClass: targetClass,
    since: now,
    pendingSwitch: null,
    lastEventAt: now,
  };
}

// ── Function 4: tickIdleTimeout ───────────────────────────────────────────

/**
 * Returns "sleep" when the mascot has been idling (class === "idle") for
 * longer than `machine.idleTimeoutMs`. Returns null otherwise.
 *
 * Caller pattern (inside rAF loop):
 *   const sleepTarget = tickIdleTimeout(machine, now);
 *   if (sleepTarget) {
 *     const plan = planTransition(machine, { state: "sleep", ... }, now);
 *     machine = applyTransition(machine, plan, now);
 *     if (plan.action === "switch_now") renderer.crossFadeTo("sleep", plan.blendMs);
 *   }
 *
 * Why class-based and not state-based: any idle_* (including idle_breathe_slow
 * and the bop-to-beat variants) counts as idling. dance_* / talk_* / react_* /
 * effect / explanation / misc never trigger the sleep timer.
 *
 * Returns the MascotState directly (not a TransitionPlan) so callers run it
 * through planTransition normally — keeps the "priority + beat-lock" logic
 * in one place.
 */
export function tickIdleTimeout(
  machine: MachineState,
  now: number,
): MascotState | null {
  if (machine.currentClass !== "idle") return null;
  if (now - machine.lastEventAt < machine.idleTimeoutMs) return null;
  return "sleep";
}

// ── Phase 43 Plan 43-06 / VIS-05 — test-only bind-pose probe ─────────────

/**
 * Test-only synthetic "skeleton state" probe for the 30s smoke
 * (smoke-30s.spec.ts). Returns a deterministic numeric vector keyed
 * off the machine's current state + its priority class — the pure-
 * function layer's equivalent of "what pose is the rig in?".
 *
 * The bind pose is `initialMachineState`'s `current` = "idle_breathe"
 * + idle-class priority (20). Comparing this vector against
 * BIND_POSE_PROBE (below) with ε=0.01 gives the idle-zero contract a
 * pure-function test handle. Real bone-transform comparison happens
 * at the Three.js layer in renderer.ts — out of scope for this pure
 * module + jsdom test environment.
 *
 * Leading underscore signals test-only intent per existing convention.
 */
export function _getSkeletonProbe(machine: MachineState): {
  state_id: string;
  class_priority: number;
} {
  return {
    state_id: machine.current,
    class_priority: STATE_PRIORITY[machine.currentClass],
  };
}

/** The bind-pose probe = boot-time idle_breathe @ idle priority (20). */
export const _BIND_POSE_PROBE = Object.freeze({
  state_id: "idle_breathe" as MascotState,
  class_priority: STATE_PRIORITY.idle,
});
