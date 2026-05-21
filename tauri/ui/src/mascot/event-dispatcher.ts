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

// Phase 56 / LIVE-05a — music-confirmation thresholds, mirrored VERBATIM from
// the Python source-of-truth in src/vibemix/audio/constants.py
// (SILENT_RMS=0.012, LOW_RMS=0.040, PEAK_RMS=0.110). Keep these in lock-step
// with the Python side; never invent new values here.
//
// IMPORTANT (WR-01, Phase 56 review): the guard below is a defence-in-depth
// SANITY FLOOR, NOT a re-derivation of `state.phase`. `state.phase` already
// encodes the full breakdown/peak/drop logic upstream (src/vibemix/state/phase.py
// `_classify_phase_v4`). The guard's only job is to reject the GENUINE
// contradiction (a phase value that the audio level can't possibly support —
// chiefly the drop-during-silence misclassification, RESEARCH Pitfall 6). It
// must NOT impose boundaries STRICTER than the classifier, or it silently
// suppresses legitimate, correctly-classified modes (the LIVE-05a "≥6 distinct
// modes, each reachable" headline). See PEAK_FLOOR_RMS below for why `peak`
// uses 0.045, not PEAK_RMS.
/** Loud-section floor: a confirmed drop requires music ≥ this. Mirrors
 *  `last >= PEAK_RMS` in phase.py `_classify_phase_v4` (drop branch).
 *  Also used as the breakdown contradiction ceiling — reject a "breakdown"
 *  at full peak loudness (a breakdown can sit anywhere BELOW peak, but never
 *  AT peak; see the breakdown case below). */
const PEAK_RMS = 0.11;
/**
 * Python `peak` floor: phase.py `_classify_phase_v4` admits a `peak` when
 * `all(v >= 0.045 for v in recent)` — i.e. peaks legitimately live anywhere
 * from 0.045 upward, NOT only at PEAK_RMS (0.110). Re-imposing PEAK_RMS on
 * `peak` over-suppresses real peaks in the 0.045–0.110 band. Mirror Python's
 * actual floor so the guard never fights the classifier. (src/vibemix/state/
 * phase.py: `if all(v >= 0.045 for v in recent): return "peak"`.)
 */
const PEAK_FLOOR_RMS = 0.045;

// ── Types ─────────────────────────────────────────────────────────────────

export interface SnapshotSlice {
  bpm: number;
  bpm_confidence: number;
  downbeat_phase: number;
  mood: string;
  /**
   * Smoothed master-bus music level (0..1). The live ws frame broadcasts
   * this as a flat float (`levels.snapshot()`); the fixture frame carries
   * it nested as `{ rms, peak }`. Both feed this numeric field. Phase 56 /
   * LIVE-05a: the music-confirmation guard in stateForPhase reads it so a
   * `phase` that disagrees with the level is treated as "no signal".
   */
  music: number;
  /** Smoothed AI-voice level (0..1). Same flat-vs-nested duality as `music`. */
  voice: number;
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
 * Area 3 mapping + Phase 56 / LIVE-05a music-confirmation guard.
 *
 * Defence-in-depth (anti-slop): `phase` is the trusted classifier output;
 * the guard is a SANITY FLOOR that rejects only the GENUINE contradictions —
 * a `phase` value the audio level cannot possibly support. It does NOT
 * re-derive the classifier, and it must NOT be stricter than Python's
 * `_classify_phase_v4` (src/vibemix/state/phase.py), or it suppresses
 * legitimate modes (WR-01).
 *
 * Per-mode rationale (each mirrors phase.py semantics):
 *   - `drop`: a real drop is loud — phase.py needs `last >= PEAK_RMS`. The
 *     slop case is `phase=="drop"` on near-silence (Pitfall 6). Keep the
 *     hard PEAK_RMS floor.
 *   - `peak`: phase.py admits peaks down to 0.045 (`all(v >= 0.045 …)`), NOT
 *     PEAK_RMS. Confirm only "not silent" via PEAK_FLOOR_RMS (0.045); using
 *     PEAK_RMS here drops legit peaks in 0.045–0.110.
 *   - `breakdown`: phase.py classifies breakdown RELATIVELY (`last < 0.5 *
 *     earlier_max`), so a breakdown off a loud section sits FAR above
 *     LOW_RMS (e.g. 0.05–0.14). The TS rig has no energy history, so we do
 *     NOT re-derive it from an absolute level. The only genuine
 *     contradiction is the OPPOSITE extreme — a "breakdown" at full peak
 *     loudness — so reject only `music >= PEAK_RMS`.
 *
 * When the level contradicts the phase we return `null`, which the PHASE
 * case treats as "no signal" → the current mode persists (never drops to a
 * decorative mode). Same "contradiction → return null, never throw" discipline
 * as the dispatcher's `default` arm.
 *
 * @param phase the bus `state.phase` value
 * @param music the smoothed master-bus level (0..1) confirming the phase
 */
function stateForPhase(phase: string, music: number): MascotState | null {
  switch (phase) {
    case "drop":
      // Drop is the slop-prone case: a real drop is loud. Keep the hard
      // floor — mirrors phase.py drop branch (`last >= PEAK_RMS`).
      return music >= PEAK_RMS ? "dance_hard" : null;
    case "peak":
      // Python peak floor is 0.045 (NOT PEAK_RMS) — confirm "not silent"
      // only, so legit peaks in 0.045–0.110 are not over-suppressed.
      return music >= PEAK_FLOOR_RMS ? "dance_hard" : null;
    case "breakdown":
      // Python breakdown = "fell to < half recent max", which can sit well
      // above LOW_RMS. With no energy history here, gate on "not at full
      // peak" (reject only the absurd loud breakdown), never on `< LOW_RMS`.
      return music < PEAK_RMS ? "idle_breathe" : null;
    case "groove":
      return "idle_bop_to_beat_energetic";
    case "build":
      return "idle_bop_to_beat_energetic";
    case "low":
      return "idle_bop_to_beat_mellow";
    case "silent":
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
        // Phase 56 / LIVE-05a: pass the confirming music level so a phase
        // that disagrees with the level is treated as "no signal".
        const target = stateForPhase(to, snapshot.music);
        // A contradictory frame falls out here = current mode persists (anti-slop).
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

// ── Phase 47 / MASCOT-05 — 4-layer additive event fanout ──────────────
//
// Declarative event-class → 4-layer fanout map. Reads cleanly + serves as
// single source of truth for "when EVENT X fires, which mascot layers
// react?". Tested by tauri/ui/src/mascot/__tests__/event-coverage-matrix.test.ts.
//
// Anchored to Phase 47 / CONTEXT.md § State-Machine Wiring (verbatim copy
// to keep this module the canonical record). KAAN_SPOKE is empty by
// design — talk-block rule per Phase 13 STATE_PRIORITY = mascot stays on
// Base during user speech.

import type {
  BaseClip,
  EmotionClip,
  AnticipationClip,
  ReactionClip,
} from "./types.js";

/** v2.0 EventDetector event classes + Phase 30 Hard Tek detectors.
 *  Total: 15 event classes (matches src/vibemix/agent/event_detector.py). */
export type EventClass =
  | "TRACK_CHANGE"
  | "PHASE"
  | "LAYER_ARRIVAL"
  | "MIX_MOVE"
  | "HEARTBEAT"
  | "KAAN_SPOKE"
  | "MANUAL"
  | "DISTORTION_CLIMB"
  | "ACID_LINE_ENTRY"
  | "KICK_SWAP"
  | "SUB_LAYER_ARRIVAL"
  | "BREAKDOWN_KICK_KILL"
  | "REENTRY_KICK_LAND"
  | "KICK_DENSITY_SHIFT"
  | "PHRASE_BOUNDARY";

export interface LayerFanout {
  base?: BaseClip;
  emotion?: EmotionClip;
  anticipation?: AnticipationClip;
  reaction?: ReactionClip;
}

export const EVENT_LAYER_PRIORITY_MAP: Readonly<
  Record<EventClass, LayerFanout>
> = Object.freeze({
  TRACK_CHANGE: {
    emotion: "emotion_focus",
    anticipation: "prep_mix",
    reaction: "react_mix_in",
  },
  PHASE: { emotion: "emotion_anticipation", anticipation: "prep_breakdown" },
  LAYER_ARRIVAL: { emotion: "emotion_surprise", reaction: "react_sub_layer" },
  MIX_MOVE: { reaction: "react_mix_in" },
  HEARTBEAT: { base: "base_breathe" },
  KAAN_SPOKE: {}, // talk-block rule — mascot stays on Base
  MANUAL: { reaction: "react_hype_peak" }, // caller-driven; default to peak
  DISTORTION_CLIMB: { reaction: "react_distortion_climb" },
  ACID_LINE_ENTRY: { reaction: "react_acid_line" },
  KICK_SWAP: { reaction: "react_kick_swap" },
  SUB_LAYER_ARRIVAL: { reaction: "react_sub_layer" },
  BREAKDOWN_KICK_KILL: {
    anticipation: "prep_breakdown",
    reaction: "react_breakdown",
  },
  REENTRY_KICK_LAND: { reaction: "react_reentry" },
  KICK_DENSITY_SHIFT: { emotion: "emotion_focus" },
  PHRASE_BOUNDARY: { reaction: "react_phrase_boundary" },
});

/** Layer-instance bundle passed to dispatchEvent47. Caller (typically the
 *  Tauri webview index.ts) constructs all four and threads them through.
 *  Each layer's actual class import is intentionally NOT bound here —
 *  this module stays decoupled from concrete layer constructors so it
 *  remains test-friendly (vitest passes mock objects with the methods below). */
export interface MascotLayerBundle47 {
  base: { schedule(clip: BaseClip, now_ms: number): void };
  emotion: { update(clip: EmotionClip | null, now_ms: number): void };
  anticipation: { update(clip: AnticipationClip | null, now_ms: number): void };
  reaction: { fire(clip: ReactionClip, now_ms: number): void };
}

/**
 * Phase 47 / MASCOT-05 — dispatch an event class to the 4-layer additive state machine.
 *
 * Reads EVENT_LAYER_PRIORITY_MAP[event] and invokes the appropriate
 * .schedule/.update/.fire on each layer in priority order
 * (base → emotion → anticipation → reaction).
 *
 * Returns the set of layer keys that received a non-null fanout (used
 * by the vitest coverage matrix as the assertion target).
 *
 * Naming: dispatchEvent47 (not dispatchEvent) to avoid colliding with the
 * pre-existing v2.0 envelope-dispatcher in this module.
 */
export function dispatchEvent47(
  event: EventClass,
  layers: MascotLayerBundle47,
  now_ms: number,
): ReadonlyArray<keyof LayerFanout> {
  const fanout = EVENT_LAYER_PRIORITY_MAP[event];
  const fired: Array<keyof LayerFanout> = [];

  if (fanout.base !== undefined) {
    layers.base.schedule(fanout.base, now_ms);
    fired.push("base");
  }
  if (fanout.emotion !== undefined) {
    layers.emotion.update(fanout.emotion, now_ms);
    fired.push("emotion");
  }
  if (fanout.anticipation !== undefined) {
    layers.anticipation.update(fanout.anticipation, now_ms);
    fired.push("anticipation");
  }
  if (fanout.reaction !== undefined) {
    layers.reaction.fire(fanout.reaction, now_ms);
    fired.push("reaction");
  }

  return Object.freeze(fired);
}
