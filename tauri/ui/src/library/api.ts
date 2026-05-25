// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — typed invoke()/event client for the library surface.
 *
 * The Rust bridge agent owns the matching `#[tauri::command]` handlers and the
 * `library://embed-*` event emitters (tauri/src-tauri/**). This module is the
 * webview-side typed gateway against that exact contract:
 *
 *   invoke("library_search",  { query, k })       -> SearchResult
 *   invoke("library_similar", { seed,  k })       -> SearchResult   (same shape)
 *   invoke("library_stats")                        -> LibraryStats
 *   invoke("library_embed_folder", { path, strategy })
 *        -> kicks off a folder embed; progress arrives as Tauri events:
 *           listen("library://embed-progress")  EmbedProgress
 *           listen("library://embed-done")      EmbedDone
 *
 * Unlike the wizard's schema-gated WS path (ipc/client.ts), the Vibe Engine
 * commands are direct Tauri commands — Rust runs the embedder + sqlite-vec
 * search in-process, so there is no JSON-schema validator on this seam.
 *
 * DEV FALLBACK: when `invoke()` is unavailable (plain `vite` dev, jsdom tests)
 * or throws (bridge not landed yet), every call resolves with the real sample
 * data captured from the 2026-05-25 subset run — the same numbers baked into
 * mocks/vibemix-library-ui.html — so the window renders fully without Rust.
 */

import { listen as tauriListen, type UnlistenFn } from "@tauri-apps/api/event";

// ── Wire types (the bridge contract) ───────────────────────────────────────

export type EmbedStrategy = "mean" | "cue-anchored";

/** One pulled track row. `meta` is a short mono caption (folder hash + dims,
 *  or `centered · cos` for the similar path). */
export interface TrackResult {
  track_id: string;
  title: string;
  /** Cosine score in [0,1]. Higher = closer in 1536-d vibe space. */
  score: number;
  meta: string;
}

export interface SearchResult {
  results: TrackResult[];
  /** Whether the corpus was mean-centered before scoring (collapses the
   *  cosine cone so real separation shows). Drives the scope's "centered". */
  centered: boolean;
  corpus_size: number;
}

export interface LibraryStats {
  indexed: number;
  backend: string;
  spent_eur: number;
  failed: number;
}

/** Per-file progress frame from `library://embed-progress`. */
export interface EmbedProgress {
  n: number;
  total: number;
  /** "ok" | "skip" | "err" — the LED color in the live log. */
  status: "ok" | "skip" | "err";
  filename: string;
  cost_eur: number;
}

/** Terminal frame from `library://embed-done`. */
export interface EmbedDone {
  embedded: number;
  skipped: number;
  failed: number;
  total: number;
  cost_eur: number;
}

// ── invoke() resolution (lazy, fallback-safe) ──────────────────────────────

type InvokeFn = <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;

let _invoke: InvokeFn | null | undefined;

/** Resolve the Tauri `invoke` lazily. Returns null when the Tauri API is not
 *  present (plain browser / vitest) so callers fall through to the dev data. */
async function getInvoke(): Promise<InvokeFn | null> {
  if (_invoke !== undefined) return _invoke;
  try {
    const mod = await import("@tauri-apps/api/core");
    _invoke = mod.invoke as InvokeFn;
  } catch {
    _invoke = null;
  }
  return _invoke;
}

/** True when we're running inside a real Tauri webview (invoke resolvable). */
export async function hasTauri(): Promise<boolean> {
  return (await getInvoke()) !== null;
}

// ── Dev fallback data — real 2026-05-25 subset run ─────────────────────────
// Mirrors mocks/vibemix-library-ui.html DATA/LOG/stats verbatim so the window
// is fully demoable in `vite` dev before the Rust bridge lands.

const DEV_SEARCH: SearchResult = {
  centered: true,
  corpus_size: 142,
  results: [
    { track_id: "23381471", title: "Raffertie — The Substance", score: 0.764, meta: "folder:23381471 · 1536d" },
    { track_id: "b8d4da96", title: "ARTLUS - i like the way you kiss me (Remix)", score: 0.758, meta: "folder:b8d4da96 · 1536d" },
    { track_id: "911ea756", title: "Quälgeist", score: 0.751, meta: "folder:911ea756 · 1536d" },
    { track_id: "a8f148f3", title: "FLKN - I Need Acid (Original mix)", score: 0.739, meta: "folder:a8f148f3 · 1536d" },
    { track_id: "7f9f9052", title: "Charli XCX - Guess (DJ Daddy Trance Edit)", score: 0.737, meta: "folder:7f9f9052 · 1536d" },
    { track_id: "a0b1a41b", title: "Brutalismus 3000 - nur mein körper und die angst", score: 0.734, meta: "folder:a0b1a41b · 1536d" },
  ],
};

const DEV_SIMILAR: SearchResult = {
  centered: true,
  corpus_size: 142,
  results: [
    { track_id: "girl-like-me", title: "Girl Like Me", score: 0.369, meta: "centered · cos" },
    { track_id: "fka-wild-alone", title: "FKA Twigs - Wild And Alone", score: 0.313, meta: "centered · cos" },
    { track_id: "troye-one-girls", title: "Troye Sivan - One of Your Girls", score: 0.308, meta: "centered · cos" },
    { track_id: "beatback", title: "Beatback", score: 0.305, meta: "centered · cos" },
    { track_id: "kylie-stateside", title: "Kylie Minogue - Stateside", score: 0.299, meta: "centered · cos" },
    { track_id: "i-hate-u-demo", title: "i hate u (demo) ft. Tor Miller", score: 0.279, meta: "centered · cos" },
  ],
};

const DEV_STATS: LibraryStats = {
  indexed: 142,
  backend: "sqlite-vec",
  spent_eur: 0.19,
  failed: 0,
};

/** The 8-file embed log from the subset run — replayed in dev to animate the
 *  ingest progress bar + live log without a real folder embed. */
const DEV_EMBED_LOG: Array<[EmbedProgress["status"], string, number]> = [
  ["ok", "jecta — purrr (at the goth club).mp3", 0.191],
  ["ok", "Just Like You.mp3", 0.190],
  ["skip", "Brutalismus 3000 - badthiings.mp3", 0.190],
  ["ok", "Safeword [BABYNYMPH Remix].mp3", 0.145],
  ["ok", "FLKN - I Need Acid (Original mix).mp3", 0.121],
  ["ok", "Anti.mp3", 0.121],
  ["ok", "ARTLUS - i like the way you kiss me (Remix).mp3", 0.011],
  ["ok", "9mm.mp3", 0.009],
];

/** Exported so the state machine + tests can assert the dev numbers. */
export const DEV_FALLBACK = {
  search: DEV_SEARCH,
  similar: DEV_SIMILAR,
  stats: DEV_STATS,
  embedLog: DEV_EMBED_LOG,
} as const;

// ── Public client ───────────────────────────────────────────────────────────

/** Text vibe query → ranked tracks + scope geometry. */
export async function librarySearch(query: string, k = 6): Promise<SearchResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_SEARCH;
  try {
    return await invoke<SearchResult>("library_search", { query, k });
  } catch {
    return DEV_SEARCH;
  }
}

/** Seed (track_id or dropped file path) → nearest neighbours. */
export async function librarySimilar(seed: string, k = 6): Promise<SearchResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_SIMILAR;
  try {
    return await invoke<SearchResult>("library_similar", { seed, k });
  } catch {
    return DEV_SIMILAR;
  }
}

/** Corpus readout for the left console. */
export async function libraryStats(): Promise<LibraryStats> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_STATS;
  try {
    return await invoke<LibraryStats>("library_stats");
  } catch {
    return DEV_STATS;
  }
}

/** Kick off a folder embed. Progress + completion arrive as Tauri events —
 *  subscribe with `onEmbedProgress` / `onEmbedDone` BEFORE calling this.
 *
 *  Returns `true` when the real bridge accepted the job, `false` when we fell
 *  through to the dev replay (so the caller can drive the replay itself). */
export async function libraryEmbedFolder(
  path: string,
  strategy: EmbedStrategy,
): Promise<boolean> {
  const invoke = await getInvoke();
  if (!invoke) return false;
  try {
    await invoke("library_embed_folder", { path, strategy });
    return true;
  } catch {
    return false;
  }
}

// ── Event subscriptions ─────────────────────────────────────────────────────

const NO_UNLISTEN: UnlistenFn = () => {};

/** Subscribe to per-file embed progress. No-op unlisten in non-Tauri envs. */
export async function onEmbedProgress(
  cb: (p: EmbedProgress) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<EmbedProgress>("library://embed-progress", (e) =>
      cb(e.payload),
    );
  } catch {
    return NO_UNLISTEN;
  }
}

/** Subscribe to embed completion. No-op unlisten in non-Tauri envs. */
export async function onEmbedDone(
  cb: (d: EmbedDone) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<EmbedDone>("library://embed-done", (e) =>
      cb(e.payload),
    );
  } catch {
    return NO_UNLISTEN;
  }
}
