/* Phase 62 Plan 04 — Pill state machine (pure functions, no DOM, no wall-clock).
 *
 * PURITY DISCIPLINE (load-bearing — the verify step greps this file):
 *   - No wall-clock reads — every function takes `now: number` as a parameter.
 *   - No timers — the 6s expand→collapse is expressed as a `collapseAt` data
 *     field on PillState; the rAF loop in index.ts fires the revert when the
 *     timestamp lands (no setTimeout / setInterval).
 *   - No heavy imports — this file MUST be testable in isolation under node.
 *
 * Cloned from the mascot's state-machine.ts purity header (Phase 13 Plan 04),
 * but the pill's model is far simpler: four states derived from the wire, with
 * the expand state carried as data so the vitest cases are fully deterministic
 * without clock mocking.
 *
 * The four states (PILL-03 / 62-UI-SPEC §"Pill States"):
 *   - idle      ← cohost_status === "IDLE"      (or unknown / no session)
 *   - listening ← cohost_status === "LISTENING"
 *   - speaking  ← cohost_status === "TALKING"   (real voice.rms waveform)
 *   - expand    ← ipc.session.cohost-reaction   (reaction text + citation chips)
 *
 * READER vs WRITER discipline (mirrors the mascot's handleMessage):
 *   - applyFrame() with a snapshot/flat frame is a READER — it updates
 *     cohostStatus + voiceRms WITHOUT forcing a transition (the collapsed
 *     view follows baseState(cohostStatus) unless an expand is active).
 *   - applyFrame() with a cohost-reaction is the only WRITER — it enters
 *     `expand` with collapseAt = now + EXPAND_MS and carries the reaction
 *     text + chips.
 *   - tickCollapse() reverts mode → baseState(cohostStatus) once
 *     now >= collapseAt — data-driven, no setTimeout.
 */

import type { CitationChip } from "../session/components/citation-strip.js";

// ── Types ─────────────────────────────────────────────────────────────────

/** The cohost_status enum on the bus (messages.schema.json / ws_bus.py). */
export type CohostStatus = "IDLE" | "LISTENING" | "TALKING";

/** The visible pill mode. `expand` overlays the base state until it collapses. */
export type PillMode = "idle" | "listening" | "speaking" | "expand";

/**
 * The pill's full memory. Immutable — every update returns a new object
 * (`state = applyFrame(state, frame, now)`).
 *
 * - `mode`: the visible state. `expand` while a reaction panel is shown,
 *   otherwise tracks baseState(cohostStatus).
 * - `cohostStatus`: the last status read off the wire (READER). The base
 *   state the pill reverts to when an expand collapses.
 * - `voiceRms`: the last AI-speech RMS read off the wire (drives the
 *   speaking-state waveform — real signal, never a fake animation).
 * - `voicePeak`: optional peak-hold for the waveform needle (may be null).
 * - `collapseAt`: absolute timestamp (same clock as `now`) at which an active
 *   expand reverts. null when not expanded. A fresh reaction re-extends it.
 * - `reactionText`: the verbatim cohost-reaction text shown in the expand
 *   panel ("" when not expanded). Rendered as a text node — never innerHTML
 *   (T-62-11).
 * - `chips`: the citation strip carried by the active reaction (empty when
 *   not expanded). Rendered verbatim via renderCitationStrip — the pill never
 *   fabricates or adds chips (T-62-12).
 */
export interface PillState {
  mode: PillMode;
  cohostStatus: CohostStatus;
  voiceRms: number;
  voicePeak: number | null;
  collapseAt: number | null;
  reactionText: string;
  chips: CitationChip[];
}

/**
 * A frame the pill consumes off the bus. Two shapes share one entry point:
 *   - snapshot / flat live frame (READER): carries cohost_status + a voice
 *     level (flat `voice` on the live frame, nested `meters.voice.rms` on the
 *     bridged snapshot — read defensively in index.ts before this is called).
 *   - cohost-reaction (WRITER): carries text + citation_strip.
 *
 * Kept permissive (all-optional) so the defensive read in index.ts owns the
 * flat-or-nested resolution and this module stays a pure transform.
 */
export interface PillFrame {
  type?: string;
  cohostStatus?: CohostStatus | null;
  voiceRms?: number | null;
  voicePeak?: number | null;
  /** cohost-reaction payload. */
  text?: string | null;
  chips?: CitationChip[] | null;
}

// ── Tuning constants (locked per 62-UI-SPEC) ──────────────────────────────

/**
 * Expand dwell before auto-collapse, ms. 62-UI-SPEC §"Pill States" → "After
 * ~6s of no new reaction, collapses back to the prior state." A fresh
 * reaction before collapseAt re-extends this window.
 */
export const EXPAND_MS = 6000;

/** Boot mode + status. */
const BOOT_STATUS: CohostStatus = "IDLE";

// ── baseState ─────────────────────────────────────────────────────────────

/**
 * Map the wire status to the collapsed pill mode. Unknown / absent → idle
 * (the honest empty state — no scripted "waiting…" filler, 62-UI-SPEC
 * §Copywriting).
 */
export function baseState(s: CohostStatus | null | undefined): "idle" | "listening" | "speaking" {
  if (s === "TALKING") return "speaking";
  if (s === "LISTENING") return "listening";
  return "idle";
}

// ── initialPillState ──────────────────────────────────────────────────────

/**
 * Build the boot-time PillState. Caller picks the boot timestamp (usually
 * `performance.now()` at app start) so this stays pure. Boots to idle with no
 * active expand — silence is the honest empty state.
 */
export function initialPillState(_now: number): PillState {
  return {
    mode: "idle",
    cohostStatus: BOOT_STATUS,
    voiceRms: 0,
    voicePeak: null,
    collapseAt: null,
    reactionText: "",
    chips: [],
  };
}

// ── applyFrame ────────────────────────────────────────────────────────────

/**
 * Apply one wire frame. Pure — never mutates `state`, always returns a new
 * object.
 *
 * (a) READER — a snapshot/flat frame (no `text`, type !== cohost-reaction)
 *     updates cohostStatus + voiceRms WITHOUT forcing a transition. If an
 *     expand is active the mode stays `expand`; otherwise the mode follows
 *     baseState(cohostStatus). voice fields default to the prior value when
 *     absent (the defensive flat-or-nested read happens in index.ts).
 *
 * (b) WRITER — a cohost-reaction (`type === "cohost-reaction"` or
 *     `"ipc.session.cohost-reaction"`) enters `expand`, sets
 *     collapseAt = now + EXPAND_MS, and carries the verbatim text + chips.
 *     A fresh reaction while already expanded re-extends collapseAt.
 */
export function applyFrame(state: PillState, frame: PillFrame, now: number): PillState {
  const isReaction =
    frame.type === "cohost-reaction" || frame.type === "ipc.session.cohost-reaction";

  if (isReaction) {
    // WRITER — enter (or re-extend) expand.
    return {
      ...state,
      mode: "expand",
      collapseAt: now + EXPAND_MS,
      reactionText: frame.text ?? "",
      chips: frame.chips ?? [],
    };
  }

  // READER — update the view; do not transition out of an active expand.
  const cohostStatus = frame.cohostStatus ?? state.cohostStatus;
  const voiceRms = typeof frame.voiceRms === "number" ? frame.voiceRms : state.voiceRms;
  const voicePeak =
    frame.voicePeak === undefined ? state.voicePeak : frame.voicePeak;
  const expanding = state.mode === "expand" && state.collapseAt !== null;
  return {
    ...state,
    cohostStatus,
    voiceRms,
    voicePeak,
    // While expanded, hold the expand; otherwise track the base state.
    mode: expanding ? "expand" : baseState(cohostStatus),
  };
}

// ── tickCollapse ──────────────────────────────────────────────────────────

/**
 * Data-driven expand→collapse. Pure — the rAF loop calls this every frame
 * with `performance.now()`. Once `now >= collapseAt`, revert the mode to
 * baseState(cohostStatus) and clear the reaction payload. No setTimeout.
 *
 * Returns `state` unchanged (same reference) when no collapse is due, so the
 * rAF loop can cheaply skip a re-render.
 */
export function tickCollapse(state: PillState, now: number): PillState {
  if (state.mode !== "expand" || state.collapseAt === null) return state;
  if (now < state.collapseAt) return state;
  return {
    ...state,
    mode: baseState(state.cohostStatus),
    collapseAt: null,
    reactionText: "",
    chips: [],
  };
}
