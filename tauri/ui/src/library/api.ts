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
 * DEV FALLBACK: when `invoke()` is genuinely UNAVAILABLE (plain `vite` dev,
 * jsdom tests — `getInvoke()` returns null), every call resolves with the real
 * sample data captured from the 2026-05-25 subset run — the same numbers baked
 * into mocks/vibemix-library-ui.html — so the window renders fully without Rust.
 *
 * CRITICAL (anti-slop): the fallback fires ONLY for the no-Tauri case. When
 * invoke IS available (real app) and the backend call THROWS — empty cache,
 * missing key, bad strategy — we PROPAGATE the error instead of masking it with
 * canned sample data, so the UI can show a real error state. Silently returning
 * fake 142-track data on a real failure would make a broken backend look like
 * success — exactly the AI-slop failure mode this product blocks on.
 */

import { listen as tauriListen, type UnlistenFn } from "@tauri-apps/api/event";

// ── Wire types (the bridge contract) ───────────────────────────────────────

/** Embed strategy — the EXACT wire values the Rust bridge accepts
 *  (library_cmds.rs validates against `mean_excerpt` | `cue_anchored`).
 *  The UI shows nicer labels ("Mean" / "Cue-anchored") but the value sent
 *  over `invoke` MUST be one of these. */
export type EmbedStrategy = "mean_excerpt" | "cue_anchored";

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

/** One curated track row. `meta` is a short mono caption (artist, or
 *  `track <id>` when the CLI gave only the id — never a fabricated title). */
export interface CurateTrack {
  track_id: string;
  title: string;
  meta: string;
}

/** Result of an AI-curated playlist (`library curate <theme> --json`, mapped by
 *  the Rust bridge into `{ name, rationale, stop_reason, tracks, count }`). */
export interface CurateResult {
  /** Agent-chosen playlist name (falls back to the theme). */
  name: string;
  /** The agent's plain-language explanation of the set it built. */
  rationale: string;
  /** "created" | "max_iters" | "no_create" | "model_done" — why it stopped. */
  stop_reason: string;
  tracks: CurateTrack[];
  count: number;
}

/** Energy-curve preset for the set-prep co-host (`--curve <preset>`). The EXACT
 *  wire values the agent's CLI accepts; mirrors EnergyCurve in state-machine. */
export type EnergyCurve = "opener" | "peak_time" | "after_hours" | "festival";

/** Result of a set-prep run (`library build-set <brief> --curve <c> --export
 *  rekordbox --json`, mapped by the Rust bridge). Same shape as CurateResult
 *  plus `export_path` — the Rekordbox XML the agent wrote when it exported
 *  (`null` when it never did, e.g. an empty/failed run). `stop_reason` may be
 *  "exported" here (the set-prep terminal that curation never reaches). */
export interface BuildSetResult extends CurateResult {
  /** Absolute path to the exported Rekordbox XML, or `null` if none. */
  export_path: string | null;
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

/** Resolve the Tauri `invoke` lazily. Returns null when Tauri is genuinely not
 *  present (plain browser / vitest / jsdom) so callers fall through to the dev
 *  data — and ONLY then.
 *
 *  The `@tauri-apps/api/core` MODULE resolves even under vitest, but its
 *  `invoke` dereferences `window.__TAURI_INTERNALS__`, which only exists inside
 *  a real Tauri webview. We gate on that global so the null-path means "no
 *  Tauri" (→ demo data) while a resolved invoke that THROWS means a real
 *  backend error (→ propagated, never masked with fake data). */
async function getInvoke(): Promise<InvokeFn | null> {
  if (_invoke !== undefined) return _invoke;
  // Genuine Tauri presence check: the runtime injects __TAURI_INTERNALS__ into
  // the webview's window. Absent (vitest / plain vite) → no Tauri → dev data.
  const hasTauriRuntime =
    typeof window !== "undefined" &&
    (window as unknown as { __TAURI_INTERNALS__?: unknown })
      .__TAURI_INTERNALS__ != null;
  if (!hasTauriRuntime) {
    _invoke = null;
    return _invoke;
  }
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

// A representative curate run over the same 2026-05-25 subset — the agent built
// a 6-track set from the indexed library and explained the arc. Each row mirrors
// the REAL bridge contract exactly: `title = track_id`, `meta = "track <id>"`
// (Rust `map_curate_result`'s flat-id branch). The in-memory `PlaylistResult`
// carries only track_ids — no human titles — so fabricating pretty titles here
// would train the eye to expect rows the shipped product cannot produce
// (anti-slop). Dev-only: fires solely when `getInvoke()` is falsy (no Tauri), so
// it can never reach the packaged app — but it still reads exactly like prod.
const DEV_CURATE: CurateResult = {
  name: "Dusk to Dark",
  stop_reason: "created",
  rationale:
    "Opened soft and melodic, then bent the energy down into rolling, " +
    "hypnotic territory — each step tightens the groove without breaking the " +
    "floor. Kept the BPM drift under ±4% so the blends stay seamless.",
  count: 6,
  tracks: [
    { track_id: "7f9f9052", title: "7f9f9052", meta: "track 7f9f9052" },
    { track_id: "b8d4da96", title: "b8d4da96", meta: "track b8d4da96" },
    { track_id: "a0b1a41b", title: "a0b1a41b", meta: "track a0b1a41b" },
    { track_id: "911ea756", title: "911ea756", meta: "track 911ea756" },
    { track_id: "a8f148f3", title: "a8f148f3", meta: "track a8f148f3" },
    { track_id: "23381471", title: "23381471", meta: "track 23381471" },
  ],
};

// A representative set-prep (build-set) run over the same 2026-05-25 subset —
// the agent discovered + sequenced a set for a peak-time curve and EXPORTED it
// to Rekordbox XML (the v8.2 set-prep terminal). Rows mirror the real bridge
// contract exactly (title = track_id, meta = "track <id>" — the flat-id branch
// of map_curate_result), and `export_path` is the headline artefact the build
// surface reports. Dev-only: fires solely when getInvoke() is falsy (no Tauri),
// so it can never reach the packaged app — but it reads exactly like prod.
const DEV_BUILD: BuildSetResult = {
  name: "Warehouse Opener",
  stop_reason: "exported",
  rationale:
    "Opened at 122 BPM with melodic, restrained energy, then climbed a step " +
    "per blend into rolling, hypnotic territory by slot 8 — peak-time arc, BPM " +
    "drift held under ±4% so the transitions stay seamless. Each move is the " +
    "nearest grounded neighbour in vibe space, not a guess.",
  count: 6,
  export_path: "~/Music/vibemix/Warehouse Opener.xml",
  tracks: [
    { track_id: "7f9f9052", title: "7f9f9052", meta: "track 7f9f9052" },
    { track_id: "b8d4da96", title: "b8d4da96", meta: "track b8d4da96" },
    { track_id: "a0b1a41b", title: "a0b1a41b", meta: "track a0b1a41b" },
    { track_id: "911ea756", title: "911ea756", meta: "track 911ea756" },
    { track_id: "a8f148f3", title: "a8f148f3", meta: "track a8f148f3" },
    { track_id: "23381471", title: "23381471", meta: "track 23381471" },
  ],
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
  curate: DEV_CURATE,
  build: DEV_BUILD,
  stats: DEV_STATS,
  embedLog: DEV_EMBED_LOG,
} as const;

// ── Public client ───────────────────────────────────────────────────────────

/** Text vibe query → ranked tracks + scope geometry. */
export async function librarySearch(query: string, k = 6): Promise<SearchResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_SEARCH; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return invoke<SearchResult>("library_search", { query, k });
}

/** Seed (track_id or dropped file path) → nearest neighbours. */
export async function librarySimilar(seed: string, k = 6): Promise<SearchResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_SIMILAR; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return invoke<SearchResult>("library_similar", { seed, k });
}

/** Theme → AI-curated playlist (one-shot, NOT interactive). */
export async function libraryCurate(theme: string): Promise<CurateResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_CURATE; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return invoke<CurateResult>("library_curate", { theme });
}

/** Brief + energy curve → set-prep co-host: a discovered + sequenced set,
 *  auto-exported to Rekordbox XML (`export_path` on the result). One-shot; the
 *  same propagate-don't-mask discipline as curate (a real backend error throws;
 *  a no-key run returns stop_reason "max_iters" with no tracks, surfaced honestly). */
export async function libraryBuildSet(
  brief: string,
  curve: EnergyCurve,
): Promise<BuildSetResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_BUILD; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return invoke<BuildSetResult>("library_build_set", { brief, curve });
}

/** Corpus readout for the left console. */
export async function libraryStats(): Promise<LibraryStats> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_STATS; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return invoke<LibraryStats>("library_stats");
}

/** Kick off a folder embed. Progress + completion arrive as Tauri events —
 *  subscribe with `onEmbedProgress` / `onEmbedDone` BEFORE calling this.
 *
 *  Returns `true` when the real bridge accepted the job, `false` when there is
 *  no Tauri bridge (plain vite / jsdom) so the caller drives the dev replay.
 *
 *  A real backend error (bad strategy, missing folder, spawn failure) is
 *  PROPAGATED — not swallowed into a `false` that would silently animate the
 *  fake 8-file replay and look like a successful embed. */
export async function libraryEmbedFolder(
  path: string,
  strategy: EmbedStrategy,
): Promise<boolean> {
  const invoke = await getInvoke();
  if (!invoke) return false; // no Tauri (plain vite / jsdom) → caller replays
  // Real bridge: let a backend error PROPAGATE — never fall to the fake replay.
  await invoke("library_embed_folder", { path, strategy });
  return true;
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
