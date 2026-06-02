// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — pure state machine for the library console.
 *
 * PURITY DISCIPLINE (mirrors pill/mascot state-machine.ts):
 *   - No DOM, no wall-clock, no timers, no `invoke`. Every function is a pure
 *     transform over LibraryState — fully deterministic for vitest.
 *   - The mode switch (SEARCH / SIMILAR / INGEST), the active query/seed/folder,
 *     and the per-mode run-button label all live here as data; index.ts is the
 *     thin DOM renderer that maps this state onto the panels.
 *
 * The modes (mocks/vibemix-library-ui.html + curate/build/chat extensions):
 *   - search   ← text vibe query → ranked tracks + scope
 *   - similar  ← seed track (id or dropped file) → nearest neighbours + scope
 *   - ingest   ← folder path + strategy → embed progress + live log
 *   - cue      ← folder path + export format → auto-cued XML/M3U8 receipt
 *   - curate   ← theme → AI-curated playlist (numbered set + rationale)
 *   - build    ← brief + energy curve → set-prep co-host: discovered + sequenced
 *               set, auto-exported to Rekordbox XML (v8.2 Vibe Mix surface)
 *   - chat     ← conversational Viber, grounded tool trace + artifacts
 */

import type { CueExportFormat, EmbedStrategy } from "./api.js";

export type LibraryMode =
  | "search"
  | "similar"
  | "ingest"
  | "cue"
  | "curate"
  | "build"
  | "chat";

/** Energy-curve preset for the set-prep co-host (build mode). The EXACT wire
 *  values the agent's CLI accepts (`--curve <preset>`); the UI shows nicer
 *  labels ("Opener" / "Peak time" / …) but `invoke` sends one of these. */
export type EnergyCurve = "opener" | "peak_time" | "after_hours" | "festival";

export interface LibraryState {
  mode: LibraryMode;
  /** Free-text vibe query (search mode). */
  query: string;
  /** Seed for similar mode — a track_id or a dropped file path/basename. */
  seed: string;
  /** Folder path to embed (ingest mode). */
  folder: string;
  /** Embed strategy chip (ingest mode). */
  strategy: EmbedStrategy;
  /** Folder path to auto-cue (cue mode). */
  cueFolder: string;
  /** Portable cue export format (cue mode). */
  cueExport: CueExportFormat;
  /** Free-text theme for the AI curator (curate mode). */
  theme: string;
  /** Natural-language set brief for the set-prep co-host (build mode). */
  brief: string;
  /** Chosen energy curve preset (build mode). */
  curve: EnergyCurve;
  /** Current chat draft for conversational Viber mode. */
  chatMessage: string;
}

export const initialLibraryState: LibraryState = {
  mode: "chat",
  query: "hard aggressive techno",
  seed: "ygmf_Remix.wav",
  folder: "~/Music",
  strategy: "cue_anchored",
  cueFolder: "~/Music",
  cueExport: "rekordbox",
  theme: "warm sunset rooftop, dusk to dark",
  brief: "warehouse opener, melodic into rolling, 90 min",
  curve: "peak_time",
  chatMessage: "",
};

/** The left-console field label for the active mode. */
export function fieldLabel(mode: LibraryMode): string {
  switch (mode) {
    case "similar":
      return "Seed track";
    case "ingest":
      return "Folder to embed";
    case "cue":
      return "Folder to cue";
    case "curate":
      return "Curate a set";
    case "build":
      return "Build a Set";
    case "chat":
      return "Talk to Viber";
    case "search":
    default:
      return "Vibe query";
  }
}

/** The run-button label for the active mode (matches the mock copy). */
export function runLabel(mode: LibraryMode): string {
  switch (mode) {
    case "similar":
      return "▸ Find similar";
    case "ingest":
      return "▸ Embed folder";
    case "cue":
      return "▸ Export cues";
    case "curate":
      return "▸ Curate playlist";
    case "build":
      return "▸ Build a Set";
    case "chat":
      return "▸ Ask Viber";
    case "search":
    default:
      return "▸ Run search";
  }
}

/** The text echoed in the center header for the active mode. */
export function echoText(state: LibraryState): string {
  switch (state.mode) {
    case "similar":
      return state.seed;
    case "curate":
      return state.theme;
    case "build":
      return state.brief;
    case "cue":
      return state.cueFolder;
    case "chat":
      return "conversation";
    default:
      return state.query;
  }
}

// ── Transitions (immutable) ─────────────────────────────────────────────────

export function setMode(state: LibraryState, mode: LibraryMode): LibraryState {
  return { ...state, mode };
}

export function setQuery(state: LibraryState, query: string): LibraryState {
  return { ...state, query };
}

export function setSeed(state: LibraryState, seed: string): LibraryState {
  return { ...state, seed };
}

export function setFolder(state: LibraryState, folder: string): LibraryState {
  return { ...state, folder };
}

export function setCueFolder(state: LibraryState, cueFolder: string): LibraryState {
  return { ...state, cueFolder };
}

export function setCueExport(
  state: LibraryState,
  cueExport: CueExportFormat,
): LibraryState {
  return { ...state, cueExport };
}

export function setTheme(state: LibraryState, theme: string): LibraryState {
  return { ...state, theme };
}

export function setBrief(state: LibraryState, brief: string): LibraryState {
  return { ...state, brief };
}

export function setChatMessage(state: LibraryState, chatMessage: string): LibraryState {
  return { ...state, chatMessage };
}

export function setCurve(state: LibraryState, curve: EnergyCurve): LibraryState {
  return { ...state, curve };
}

export function setStrategy(
  state: LibraryState,
  strategy: EmbedStrategy,
): LibraryState {
  return { ...state, strategy };
}

// ── Match meter mapping ─────────────────────────────────────────────────────

/** Number of lit segments (0..SEGMENTS) for a score in the active mode.
 *
 * The two paths live in very different score ranges — text search lands ~0.7,
 * mean-centered similar lands ~0.3 — so the 10-segment LED strip is scaled
 * per-mode (matching the mock's `meter()`), otherwise centered scores would
 * never light the bar.
 */
export const METER_SEGMENTS = 10;

export function meterOn(score: number, mode: LibraryMode): number {
  const max = mode === "similar" ? 0.4 : 0.8;
  const min = mode === "similar" ? 0.2 : 0.6;
  const norm = Math.max(0, Math.min(1, (score - min) / (max - min)));
  return Math.round(norm * METER_SEGMENTS);
}
