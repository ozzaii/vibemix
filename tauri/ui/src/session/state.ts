/* Phase 12 Wave 3 — SessionState singleton (Plan 12-04).
 *
 * Single source of truth for the live session UI. Only `ws-bridge.ts`
 * writes to it; the rAF render loop reads from it. Components mutate
 * CSS variables off the diff between the previous frame and the new
 * state — no per-component setInterval / rAF anywhere downstream.
 *
 * Shape is a superset of SessionLayout.SessionState (the prop shape the
 * presentation components consume) — the bridge maps ipc.session.snapshot
 * → SessionState shallow-merge, and the render loop projects SessionState
 * → SessionLayout.SessionState (see render-loop.ts).
 *
 * Append-only ring caps:
 *   - transcript: 200 lines (UX-08 — last 200 lines per session).
 *   - midiEvents: 12 events (UX-11 — event-ribbon shows at most 12).
 *
 * Shallow-merge: top-level keys replace, nested objects are NOT deep-merged.
 * Callers send the full sub-tree (e.g. `{ meters: full-triple }`) — this
 * mirrors React's `setState` semantics so the merge cost is O(keys-in-patch).
 */

import type { PhaseChunk } from "./components/phase-tape.js";
import type { MidiEvent } from "./components/event-ribbon.js";
import type { TranscriptLine, CohostStatus } from "./components/cohost.js";

export interface LevelPair {
  rms: number;
  peak: number;
}

export interface MetersTriple {
  music: LevelPair;
  voice: LevelPair;
  mic: LevelPair;
}

export interface TrackInfo {
  title: string;
  artist?: string | null;
  deck?: string | null;
}

export interface StatusFlags {
  livekit: "ok" | "connecting" | "down" | null;
  gemini: "ok" | "down" | null;
  midi: number | null;
  screen: "ok" | "denied" | null;
}

/** Mascot personality + reaction-cadence preset (Phase 13 Area 4).
 *  Defended at every boundary: TS narrows here, sidecar schema validates
 *  on receive (Plan 13-05 extends ipc.settings.set). Invalid string values
 *  on the wire are dropped by the ws-bridge and the field stays at its
 *  current value. */
export type MascotMood = "hype-man" | "teacher" | "coach";

export interface SettingsView {
  voice: string;
  mode: "hype" | "coach";
  genre: string;
  output_device_id: string | null;
  output_profile: "hp" | "spk";
  retention_days: number;
  push_to_mute_hotkey: string;
  // --- Phase 13 (mascot overlay) additions --------------------------------
  /** Personality preset — drives Gemini voice + clip-pool + vocab. Default
   *  per CONTEXT.md Area 4 = "hype-man". */
  mood: MascotMood;
  /** When ON, the overlay window passes pointer events through to the app
   *  beneath. Default OFF (window stays draggable). */
  click_through: boolean;
}

export interface SessionState {
  meters: MetersTriple;
  phase: PhaseChunk[];
  phaseNowPct: number;
  bpm: number | null;
  bpmPeriodMs: number | null;
  dropPredBars: number | null;
  transcript: TranscriptLine[];
  midiEvents: MidiEvent[];
  track: TrackInfo | null;
  status: StatusFlags;
  settings: SettingsView;
  muted: boolean;
  cohostStatus: CohostStatus;
  latencyMs: number | null;
  grounded: boolean;
  /** Wall-clock display string (HH:MM:SS) for the titlebar + timecode.
   *  Recomputed locally in render-loop.ts; ws-bridge does not touch this. */
  clockText: string;
}

export const TRANSCRIPT_RING_CAP = 200;
export const MIDI_EVENT_RING_CAP = 12;

/** Default state — every field present so the render-loop never reads
 *  `undefined`. Mirrors SessionLayout.defaultState() for the overlapping
 *  fields. Booting state on first paint matches a "cohost-not-yet-wired"
 *  snapshot (grounded=false, cohostStatus=IDLE). */
function makeDefault(): SessionState {
  return {
    meters: {
      music: { rms: 0, peak: 0 },
      voice: { rms: 0, peak: 0 },
      mic: { rms: 0, peak: 0 },
    },
    phase: [],
    phaseNowPct: 0,
    bpm: null,
    bpmPeriodMs: null,
    dropPredBars: null,
    transcript: [],
    midiEvents: [],
    track: null,
    status: {
      livekit: null,
      gemini: null,
      midi: null,
      screen: null,
    },
    settings: {
      voice: "kore",
      mode: "hype",
      genre: "techno",
      output_device_id: null,
      output_profile: "hp",
      retention_days: 30,
      push_to_mute_hotkey: "cmd+shift+m",
      mood: "hype-man",
      click_through: false,
    },
    muted: false,
    cohostStatus: "IDLE",
    latencyMs: null,
    grounded: false,
    clockText: "00:00:00",
  };
}

let currentState: SessionState = makeDefault();

export function getSessionState(): Readonly<SessionState> {
  return currentState;
}

/** Shallow-merge patch into SessionState. Top-level keys in the patch
 *  replace the current value verbatim — nested objects are NOT deep-merged.
 *  The bridge writes whole sub-trees (e.g. `setSessionState({ meters: ... })`).
 *
 *  For append paths (transcript, midiEvents), callers use the helpers
 *  below which apply ring-cap trimming.
 *
 *  Returns the new state for convenience (tests assert ref change). */
export function setSessionState(patch: Partial<SessionState>): SessionState {
  currentState = { ...currentState, ...patch };
  return currentState;
}

/** Append-and-trim helper for transcript. Returns a NEW array (ref change
 *  is the renderer's signal to rebuild the transcript subtree); callers
 *  should pass an array of new lines (typically the snapshot's
 *  `transcript_delta`). */
export function appendTranscript(
  lines: TranscriptLine[],
): TranscriptLine[] {
  if (lines.length === 0) return currentState.transcript;
  const merged = currentState.transcript.concat(lines);
  const trimmed =
    merged.length > TRANSCRIPT_RING_CAP
      ? merged.slice(merged.length - TRANSCRIPT_RING_CAP)
      : merged;
  currentState = { ...currentState, transcript: trimmed };
  return trimmed;
}

/** Append-and-trim helper for midi events. Ring-caps to 12 — older
 *  events fall off the head. */
export function appendMidiEvents(
  events: MidiEvent[],
): MidiEvent[] {
  if (events.length === 0) return currentState.midiEvents;
  const merged = currentState.midiEvents.concat(events);
  const trimmed =
    merged.length > MIDI_EVENT_RING_CAP
      ? merged.slice(merged.length - MIDI_EVENT_RING_CAP)
      : merged;
  currentState = { ...currentState, midiEvents: trimmed };
  return trimmed;
}

/** Reset the singleton back to defaults. Test-only — production code
 *  doesn't need this. Lives in the module so vitest cases stay isolated. */
export function _resetSessionStateForTests(): void {
  currentState = makeDefault();
}
