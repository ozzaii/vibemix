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
 * The three modes (mocks/vibemix-library-ui.html):
 *   - search   ← text vibe query → ranked tracks + scope
 *   - similar  ← seed track (id or dropped file) → nearest neighbours + scope
 *   - ingest   ← folder path + strategy → embed progress + live log
 */

import type { EmbedStrategy } from "./api.js";

export type LibraryMode = "search" | "similar" | "ingest";

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
}

export const initialLibraryState: LibraryState = {
  mode: "search",
  query: "hard aggressive techno",
  seed: "ygmf_Remix.wav",
  folder: "~/Music",
  strategy: "cue-anchored",
};

/** The left-console field label for the active mode. */
export function fieldLabel(mode: LibraryMode): string {
  switch (mode) {
    case "similar":
      return "Seed track";
    case "ingest":
      return "Folder to embed";
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
    case "search":
    default:
      return "▸ Run search";
  }
}

/** The text echoed in the center header for the active mode. */
export function echoText(state: LibraryState): string {
  return state.mode === "similar" ? state.seed : state.query;
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
