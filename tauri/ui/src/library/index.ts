// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — library window entry point.
 *
 * Mounts into #app of library.html (the 5th Tauri webview, opened by the Rust
 * bridge's `open_library_window` command). Thin DOM renderer over the pure
 * state-machine.ts; all backend I/O goes through api.ts (typed invoke/event
 * client with a dev fallback so this window renders fully in plain `vite` dev).
 *
 * Seven modes (mode switch in the left console):
 *   - search   text query → librarySearch → results + scope
 *   - similar  seed (drop a file or keep the current) → librarySimilar → results + scope
 *   - ingest   folder + strategy → libraryEmbedFolder → progress bar + live log + running €
 *   - curate   theme → libraryCurate → numbered set + notes
 *   - build    brief + curve → libraryBuildSet → ordered set + Rekordbox export
 *   - cue      folder + format → libraryCueFolder → portable cue export receipt
 *   - chat     message + history → libraryChat → reply, tools, artifacts
 *
 * Wire-vs-dev: every api.ts call falls back to the real 2026-05-25 subset-run
 * sample only when `invoke()` is unavailable, so the surface is demoable before
 * the Rust bridge lands. Real backend errors propagate and render honestly. The
 * ingest replay below drives the same bar + log from DEV_FALLBACK.embedLog when
 * the bridge isn't there.
 */

import {
  DEV_FALLBACK,
  libraryBuildSet,
  libraryChat,
  libraryCueFolder,
  libraryCurate,
  libraryEmbedFolder,
  libraryModels,
  librarySearch,
  librarySimilar,
  libraryStats,
  normalizeLiveContextPayload,
  onEmbedDone,
  onEmbedProgress,
  onLiveDeckContext,
  onLiveMoveContext,
  onModelProgress,
  onViberTool,
  type BuildSetResult,
  type CurateResult,
  type CueExportFormat,
  type EmbedDone,
  type EmbedProgress,
  type EmbedStrategy,
  type EnergyCurve,
  type LibraryChatMoveGrade,
  type LibraryChatPlaylist,
  type LibraryChatResult,
  type LibraryChatToolTrace,
  type LibraryChatTurn,
  type LibraryCueResult,
  type LibraryLiveDeck,
  type LibraryLiveContext,
  type LibraryLiveEvidence,
  type LibraryLiveMidiEvidence,
  type LibraryLiveVerification,
  type LibraryModelInstallTarget,
  type LibraryModelProgress,
  type LibraryViberToolEvent,
  type LibraryModelsResult,
  type LibraryStats,
  type SearchResult,
} from "./api.js";
import { renderScope } from "./scope.js";
import {
  echoText,
  fieldLabel,
  initialLibraryState,
  meterOn,
  METER_SEGMENTS,
  runLabel,
  setBrief,
  setChatMessage,
  setCueExport,
  setCueFolder,
  setCurve,
  setFolder,
  setMode,
  setQuery,
  setSeed,
  setStrategy,
  setTheme,
  type LibraryMode,
  type LibraryState,
} from "./state-machine.js";

// ── DOM lookups ─────────────────────────────────────────────────────────────

function $(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error(`vmx-lib: missing #${id}`);
  return el;
}

// ── Render helpers ──────────────────────────────────────────────────────────

function meterMarkup(score: number, mode: LibraryMode): string {
  const on = meterOn(score, mode);
  let h = "";
  for (let i = 0; i < METER_SEGMENTS; i++) {
    const cls = i < on ? "on" : i < on + 1 ? "dim" : "";
    h += `<i class="${cls}"></i>`;
  }
  return h;
}

/** Escape user/data text before injecting into innerHTML (track titles may
 *  contain `<`, `&`, etc. — the corpus is the user's own filenames). */
function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function clarificationMarkup(
  result: CurateResult,
  rerunHint: string,
): string | null {
  if (result.stop_reason !== "clarification_needed") return null;
  const question = (result.question || result.rationale || "").trim();
  const choices = (result.choices || [])
    .map((choice) => choice.trim())
    .filter((choice) => choice.length > 0);
  const choiceList =
    choices.length > 0
      ? `<ol class="vmx-lib-clarification-choices">${choices
          .map((choice) => `<li>${esc(choice)}</li>`)
          .join("")}</ol>`
      : "";

  return `<div class="vmx-lib-empty vmx-lib-clarification" data-wire="library.clarification">
    <div class="vmx-lib-empty-kicker">Viber needs one detail</div>
    <div class="vmx-lib-clarification-question">${esc(
      question || "Choose the direction before building this set.",
    )}</div>
    ${choiceList}
    <div class="vmx-lib-clarification-hint">${esc(rerunHint)}</div>
  </div>`;
}

let latestStats: LibraryStats | null = null;
let latestModels: LibraryModelsResult | null = null;
let latestLiveContext: LibraryLiveContext | null = null;
let latestRecentMoves: string[] = [];
let latestMoveWindow: Array<{ label: string; seenAtMs: number }> = [];
const LIVE_MOVE_CONTEXT_TTL_MS = 8_000;
const LIVE_EVIDENCE_CAP = 10;
const LIVE_EVIDENCE_REFS_CAP = 14;
const LIVE_MIDI_EVIDENCE_CAP = 4;
const LIVE_CONTEXT_TEXT_KEYS = [
  "deck_lanes_context",
  "deck_reference_context",
  "deck_source_context",
  "deck_audio_context",
  "deck_audio_separation_context",
  "deck_audio_features_context",
  "deck_audio_delta_context",
  "deck_audio_window_context",
  "audio_part_context",
] as const;

function baseLiveContext(
  context: LibraryLiveContext | null,
): Omit<LibraryLiveContext, "recent_moves"> | null {
  if (!context) return null;
  const { recent_moves: _recentMoves, ...base } = context;
  return Object.keys(base).length > 0 ? base : null;
}

function compactLiveMoveWindow(nowMs = Date.now()): string[] {
  const fresh = latestMoveWindow.filter(
    (record) => nowMs - record.seenAtMs <= LIVE_MOVE_CONTEXT_TTL_MS,
  );
  const seen = new Set<string>();
  const deduped: Array<{ label: string; seenAtMs: number }> = [];
  for (const record of [...fresh].reverse()) {
    if (seen.has(record.label)) continue;
    seen.add(record.label);
    deduped.push(record);
  }
  latestMoveWindow = deduped.reverse().slice(-6);
  latestRecentMoves = latestMoveWindow.map((record) => record.label);
  return latestRecentMoves;
}

function liveEvidencePriority(token: string): number {
  if (token.startsWith("midi:")) return 0;
  if (token.includes("deck_lanes=")) return 1;
  if (token.includes("deck_reference=")) return 2;
  if (token.includes("deck_source=")) return 3;
  if (
    token.includes("transition_block=") ||
    token.includes("transition_watch=")
  )
    return 4;
  if (token.includes("transition_candidate=")) return 5;
  if (token.includes("second_deck_identity=")) return 6;
  if (token.includes("deck_audio_capture=")) return 7;
  if (token.includes("deck_audio_features=")) return 8;
  if (token.includes("deck_audio_delta=")) return 9;
  if (token.includes("deck_audio_window=")) return 10;
  if (token.includes("move_scope=")) return 11;
  if (token.includes("move_effect=") || token.includes("audio_delta="))
    return 12;
  if (token.includes("deck_audio_support=")) return 13;
  if (token.includes("deck_route=")) return 14;
  return 15;
}

function mergeLiveEvidenceTokens(
  existing?: string[],
  incoming?: string[],
  cap = LIVE_EVIDENCE_CAP,
): string[] | undefined {
  const items: Array<{ priority: number; index: number; token: string }> = [];
  const seen = new Set<string>();
  let index = 0;
  for (const list of [existing, incoming]) {
    for (const raw of list ?? []) {
      const token = raw.trim();
      if (!token || seen.has(token)) continue;
      seen.add(token);
      items.push({ priority: liveEvidencePriority(token), index, token });
      index += 1;
    }
  }
  if (items.length === 0) return undefined;
  if (items.length <= cap) return items.map((item) => item.token);
  return [...items]
    .sort((a, b) => a.priority - b.priority || a.index - b.index)
    .slice(0, cap)
    .sort((a, b) => a.index - b.index)
    .map((item) => item.token);
}

function mergeLiveMidiEvidence(
  existing?: LibraryLiveMidiEvidence[],
  incoming?: LibraryLiveMidiEvidence[],
): LibraryLiveMidiEvidence[] {
  const items: LibraryLiveMidiEvidence[] = [];
  const seen = new Set<string>();
  for (const list of [existing, incoming]) {
    for (const item of list ?? []) {
      const ident = `${item.key}@${item.t.toFixed(1)}`;
      if (seen.has(ident)) continue;
      seen.add(ident);
      items.push(item);
    }
  }
  return items.slice(-LIVE_MIDI_EVIDENCE_CAP);
}

function mergeLiveEvidence(
  existing?: LibraryLiveEvidence,
  incoming?: LibraryLiveEvidence,
): LibraryLiveEvidence | undefined {
  const merged: LibraryLiveEvidence = {};
  const mix = mergeLiveEvidenceTokens(existing?.mix, incoming?.mix);
  if (mix) merged.mix = mix;
  const refs = mergeLiveEvidenceTokens(
    existing?.refs,
    incoming?.refs,
    LIVE_EVIDENCE_REFS_CAP,
  );
  if (refs) merged.refs = refs;
  const midi = mergeLiveMidiEvidence(existing?.midi, incoming?.midi);
  if (midi && midi.length > 0) merged.midi = midi;
  return Object.keys(merged).length > 0 ? merged : undefined;
}

function mergeAudioDelta(
  existing?: string[],
  incoming?: string[],
): string[] | undefined {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const list of [existing, incoming]) {
    for (const raw of list ?? []) {
      const item = raw.trim();
      if (!item || seen.has(item)) continue;
      seen.add(item);
      out.push(item);
    }
  }
  return out.length > 0 ? out.slice(-4) : undefined;
}

function mergeLiveContext(
  existing: LibraryLiveContext | null,
  incoming: LibraryLiveContext,
): LibraryLiveContext | null {
  const normalizedIncoming = normalizeLiveContextPayload(incoming);
  if (!normalizedIncoming) return liveContextForChat(existing);
  if (
    normalizedIncoming.recent_moves &&
    normalizedIncoming.recent_moves.length > 0
  ) {
    rememberLiveMoves(normalizedIncoming.recent_moves);
  }
  const oldBase = baseLiveContext(existing) ?? {};
  const newBase = baseLiveContext(normalizedIncoming) ?? {};
  const merged: LibraryLiveContext = { ...oldBase, ...newBase };
  const oldMusic =
    typeof oldBase.music === "number" && Number.isFinite(oldBase.music)
      ? oldBase.music
      : null;
  const newMusic =
    typeof newBase.music === "number" && Number.isFinite(newBase.music)
      ? newBase.music
      : null;
  if (oldMusic !== null || newMusic !== null) {
    merged.music = Math.max(oldMusic ?? 0, newMusic ?? 0);
  }

  if (newBase.deck_state !== undefined) {
    merged.deck_state = newBase.deck_state;
  } else if (oldBase.deck_state !== undefined) {
    merged.deck_state = oldBase.deck_state;
  }
  if (newBase.deck_mixer !== undefined) {
    merged.deck_mixer = newBase.deck_mixer;
  } else if (oldBase.deck_mixer !== undefined) {
    merged.deck_mixer = oldBase.deck_mixer;
  }
  if (merged.deck_mixer !== undefined) {
    if (Object.keys(merged.deck_mixer.A ?? {}).length === 0)
      delete merged.deck_mixer.A;
    if (Object.keys(merged.deck_mixer.B ?? {}).length === 0)
      delete merged.deck_mixer.B;
    if (Object.keys(merged.deck_mixer).length === 0) delete merged.deck_mixer;
  }
  if (newBase.deck_source_status !== undefined) {
    merged.deck_source_status = newBase.deck_source_status;
  } else {
    delete merged.deck_source_status;
  }
  for (const key of LIVE_CONTEXT_TEXT_KEYS) {
    if (newBase[key] !== undefined) {
      merged[key] = newBase[key];
    } else {
      delete merged[key];
    }
  }
  const audioDelta = mergeAudioDelta(oldBase.audio_delta, newBase.audio_delta);
  if (audioDelta) merged.audio_delta = audioDelta;
  if (newBase.audio_window_context !== undefined) {
    merged.audio_window_context = newBase.audio_window_context;
  } else {
    delete merged.audio_window_context;
  }
  if (newBase.audio_window_map !== undefined) {
    merged.audio_window_map = newBase.audio_window_map;
  } else {
    delete merged.audio_window_map;
  }
  const liveEvidence = mergeLiveEvidence(
    newBase.deck_state !== undefined ? undefined : oldBase.live_evidence,
    newBase.live_evidence,
  );
  if (liveEvidence) merged.live_evidence = liveEvidence;
  else delete merged.live_evidence;

  return liveContextForChat(merged) ?? merged;
}

function rememberLiveMoves(moves: string[], nowMs = Date.now()): string[] {
  moves
    .map((move) => move.trim())
    .filter((move) => move.length > 0)
    .forEach((label) => latestMoveWindow.push({ label, seenAtMs: nowMs }));
  return compactLiveMoveWindow(nowMs);
}

function liveContextForChat(
  context: LibraryLiveContext | null,
): LibraryLiveContext | null {
  const moves = compactLiveMoveWindow();
  const base = baseLiveContext(context);
  if (base) return { ...base, recent_moves: moves };
  return moves.length > 0 ? { recent_moves: moves } : null;
}

function renderResults(result: SearchResult, mode: LibraryMode): void {
  const el = $("vmx-lib-results");
  el.innerHTML = "";
  if (result.results.length === 0) {
    el.innerHTML = `<div class="vmx-lib-empty">No tracks pulled. Embed a folder first, or widen the query.</div>`;
  } else {
    result.results.forEach((r, i) => {
      const top = i === 0 ? " top" : "";
      el.insertAdjacentHTML(
        "beforeend",
        `<div class="vmx-lib-row${top}">
          <div class="rank">${String(i + 1).padStart(2, "0")}</div>
          <div><div class="title">${esc(r.title)}</div><div class="meta">${esc(r.meta)}</div></div>
          <div class="score"><div class="num">${r.score.toFixed(3)}</div><div class="vmx-lib-meter">${meterMarkup(r.score, mode)}</div></div>
        </div>`,
      );
    });
    // staggered ease-out settle (.settled adds the transition on next frame)
    Array.from(el.children).forEach((row, i) => {
      requestAnimationFrame(() =>
        setTimeout(() => row.classList.add("settled"), i * 55),
      );
    });
  }

  $("vmx-lib-rcount").textContent =
    `${result.results.length} of ${result.corpus_size}`;
  $("vmx-lib-scope-state").textContent = result.centered ? "centered" : "raw";
  $("vmx-lib-scope").innerHTML = renderScope(result, mode);
}

/** Render an AI-curated playlist: a numbered set (reusing the row styling, but
 *  WITHOUT the score meter — a curated set is ordered by the agent's arc, not a
 *  cosine score) plus the agent's plain-language set notes. The track titles are
 *  whatever the CLI gave (often the id when no human title exists — honest, no
 *  fabrication). */
function renderCurate(result: CurateResult): void {
  const bodyEl = $("vmx-lib-rationale-body");
  bodyEl.textContent = result.rationale || "No set notes returned.";
  $("vmx-lib-rationale-meta").textContent =
    `${result.count} tracks · ${result.stop_reason}`;

  const el = $("vmx-lib-results");
  el.innerHTML = "";
  if (result.tracks.length === 0) {
    el.innerHTML =
      clarificationMarkup(
        result,
        "Add one choice to the theme and run Viber again.",
      ) ||
      `<div class="vmx-lib-empty">No set built (${esc(result.stop_reason)}). Try a different theme, or embed more tracks first.</div>`;
  } else {
    result.tracks.forEach((t, i) => {
      const top = i === 0 ? " top" : "";
      el.insertAdjacentHTML(
        "beforeend",
        `<div class="vmx-lib-row${top}">
          <div class="rank">${String(i + 1).padStart(2, "0")}</div>
          <div><div class="title">${esc(t.title)}</div><div class="meta">${esc(t.meta)}</div></div>
          <div class="score"></div>
        </div>`,
      );
    });
    Array.from(el.children).forEach((row, i) => {
      requestAnimationFrame(() =>
        setTimeout(() => row.classList.add("settled"), i * 55),
      );
    });
  }

  $("vmx-lib-rcount").textContent = `${result.tracks.length} in set`;
}

/** Clear the curate set-notes block so a stale rationale never lingers under a
 *  fresh error, or after switching away from curate mode (the block is only
 *  hidden by `body[data-mode]`, not emptied — without this it leaks the prior
 *  run's notes back into view the next time curate is shown). */
function clearRationale(): void {
  $("vmx-lib-rationale-body").textContent = "";
  $("vmx-lib-rationale-meta").textContent = "";
  // The export line is shared by build mode; clear it too so a stale "Exported
  // → …" never lingers under a fresh error or after leaving build/curate.
  const exportEl = document.getElementById("vmx-lib-export");
  if (exportEl) {
    exportEl.style.display = "none";
    const p = document.getElementById("vmx-lib-export-path");
    if (p) p.textContent = "";
  }
}

/** Working state while the Viber agent builds the set (it can take several
 *  seconds; current app backend is local Codex). Skeleton
 *  rows + a "building" note so the surface never reads as hung — the run button
 *  merely disabling is not enough feedback. Replaced wholesale by renderCurate
 *  / renderError when the run lands. */
function renderCurateLoading(theme: string): void {
  $("vmx-lib-rationale-body").textContent = `Building a set for "${theme}"…`;
  $("vmx-lib-rationale-meta").textContent = "viber · working";
  const el = $("vmx-lib-results");
  el.innerHTML = "";
  for (let i = 0; i < 4; i++) {
    el.insertAdjacentHTML(
      "beforeend",
      `<div class="vmx-lib-row vmx-lib-skeleton"><div class="rank">${String(i + 1).padStart(2, "0")}</div><div><div class="title"></div><div class="meta"></div></div><div class="score"></div></div>`,
    );
  }
  $("vmx-lib-rcount").textContent = "building…";
}

/** Render a built set (set-prep co-host). Reuses the numbered-set rows from
 *  renderCurate — a built set is also ordered by the agent's arc, no score
 *  meter — but the HEADLINE value is the per-transition rationale (the "why"
 *  behind each move) plus the Rekordbox export. When `export_path` is present we
 *  show an "Exported → <path>" line with a one-line import hint; honest empty
 *  state otherwise (a no-key run returns max_iters with no tracks — never faked). */
function renderBuildSet(result: BuildSetResult): void {
  const bodyEl = $("vmx-lib-rationale-body");
  bodyEl.textContent = result.rationale || "No set notes returned.";
  $("vmx-lib-rationale-meta").textContent =
    `${result.count} tracks · ${result.stop_reason}`;

  // Export line — the build flow auto-exports to Rekordbox XML. Shown only when
  // the agent actually wrote a file (anti-slop: no path, no claim of an export).
  const exportEl = $("vmx-lib-export");
  if (result.export_path) {
    exportEl.style.display = "";
    $("vmx-lib-export-path").textContent = result.export_path;
  } else {
    exportEl.style.display = "none";
    $("vmx-lib-export-path").textContent = "";
  }

  const el = $("vmx-lib-results");
  el.innerHTML = "";
  if (result.tracks.length === 0) {
    el.innerHTML =
      clarificationMarkup(
        result,
        "Add one choice to the brief and run set prep again.",
      ) ||
      `<div class="vmx-lib-empty">No set built (${esc(result.stop_reason)}). Check AI setup, embed more tracks, or refine the brief.</div>`;
  } else {
    result.tracks.forEach((t, i) => {
      const top = i === 0 ? " top" : "";
      el.insertAdjacentHTML(
        "beforeend",
        `<div class="vmx-lib-row${top}">
          <div class="rank">${String(i + 1).padStart(2, "0")}</div>
          <div><div class="title">${esc(t.title)}</div><div class="meta">${esc(t.meta)}</div></div>
          <div class="score"></div>
        </div>`,
      );
    });
    Array.from(el.children).forEach((row, i) => {
      requestAnimationFrame(() =>
        setTimeout(() => row.classList.add("settled"), i * 55),
      );
    });
  }

  $("vmx-lib-rcount").textContent = `${result.tracks.length} in set`;
}

/** Working state while the set-prep agent discovers + sequences the set (it can
 *  take several seconds — the current app default runs the local Codex MCP
 *  tool loop). Skeleton rows + a "building" note so
 *  the surface never reads as hung. Replaced wholesale by
 *  renderBuildSet / renderError when the run lands. */
function renderBuildSetLoading(brief: string): void {
  $("vmx-lib-rationale-body").textContent = `Building a set for "${brief}"…`;
  $("vmx-lib-rationale-meta").textContent = "set-prep · working";
  $("vmx-lib-export").style.display = "none";
  const el = $("vmx-lib-results");
  el.innerHTML = "";
  for (let i = 0; i < 4; i++) {
    el.insertAdjacentHTML(
      "beforeend",
      `<div class="vmx-lib-row vmx-lib-skeleton"><div class="rank">${String(i + 1).padStart(2, "0")}</div><div><div class="title"></div><div class="meta"></div></div><div class="score"></div></div>`,
    );
  }
  $("vmx-lib-rcount").textContent = "building…";
}

function cueOutputPath(result: LibraryCueResult): string | null {
  return result.outputs.rekordbox ?? result.outputs.m3u8 ?? null;
}

function cueOutputSummary(result: LibraryCueResult): string {
  const formats = Object.keys(result.outputs);
  return formats.length > 0 ? formats.join(" + ") : "no file";
}

function renderCueExport(result: LibraryCueResult): void {
  $("vmx-lib-rationale-body").textContent = result.ok
    ? `Cued ${result.tracks_cued} tracks with ${result.cues_total} hot cues.`
    : "Cue export did not write a file.";
  $("vmx-lib-rationale-meta").textContent =
    `${cueOutputSummary(result)} · ${result.skipped} skipped`;

  const exportEl = $("vmx-lib-export");
  const path = cueOutputPath(result);
  if (path) {
    exportEl.style.display = "";
    $("vmx-lib-export-path").textContent = path;
  } else {
    exportEl.style.display = "none";
    $("vmx-lib-export-path").textContent = "";
  }

  const rows = $("vmx-lib-results");
  rows.innerHTML = "";
  const outputs = Object.entries(result.outputs).filter(
    (entry): entry is [string, string] => typeof entry[1] === "string",
  );
  if (outputs.length === 0) {
    rows.innerHTML = `<div class="vmx-lib-empty">No cue export written. Check the folder, CUE model setup, or try fewer cues.</div>`;
  } else {
    outputs.forEach(([format, output], index) => {
      rows.insertAdjacentHTML(
        "beforeend",
        `<div class="vmx-lib-row${index === 0 ? " top" : ""}">
          <div class="rank">${String(index + 1).padStart(2, "0")}</div>
          <div><div class="title">${esc(format)}</div><div class="meta">${esc(output)}</div></div>
          <div class="score"></div>
        </div>`,
      );
    });
  }
  $("vmx-lib-rcount").textContent = `${result.tracks_cued} tracks`;
}

function renderCueLoading(folder: string): void {
  $("vmx-lib-rationale-body").textContent = `Auto-cueing "${folder}"…`;
  $("vmx-lib-rationale-meta").textContent = "cue export · working";
  $("vmx-lib-export").style.display = "none";
  const rows = $("vmx-lib-results");
  rows.innerHTML = "";
  for (let i = 0; i < 3; i++) {
    rows.insertAdjacentHTML(
      "beforeend",
      `<div class="vmx-lib-row vmx-lib-skeleton"><div class="rank">${String(i + 1).padStart(2, "0")}</div><div><div class="title"></div><div class="meta"></div></div><div class="score"></div></div>`,
    );
  }
  $("vmx-lib-rcount").textContent = "cueing…";
}

/** Idle state for agent-backed modes. Search/similar can refresh on tab switch;
 *  Codex-backed curate/build should wait for an explicit run or preset chip so
 *  merely opening the mode does not start a slow tool loop. */
function renderAgentIdle(mode: "curate" | "build" | "cue"): void {
  clearRationale();
  $("vmx-lib-rationale-body").textContent =
    mode === "build"
      ? "No set built yet."
      : mode === "cue"
        ? "No cue export yet."
        : "No playlist curated yet.";
  $("vmx-lib-rationale-meta").textContent = "idle";
  $("vmx-lib-results").innerHTML = "";
  $("vmx-lib-rcount").textContent = "ready";
  $("vmx-lib-scope-state").textContent = "ready";
}

/** Surface a REAL backend error in the results panel — honest failure, not the
 *  fake sample data. The message is the bridge's own error string (e.g.
 *  "No library cache.", "invalid strategy …"). */
function renderError(err: unknown): void {
  // Clear any stale curate set-notes so they never sit above a fresh error.
  clearRationale();
  const msg = errorMessage(err);
  const el = $("vmx-lib-results");
  el.innerHTML = `<div class="vmx-lib-error"><div class="vmx-lib-error-title">engine error</div><div class="vmx-lib-error-msg">${esc(msg)}</div></div>`;
}

function errorMessage(err: unknown): string {
  return err instanceof Error
    ? err.message
    : typeof err === "string"
      ? err
      : String(err);
}

function embeddingLabel(stats: LibraryStats): string {
  const backend = (stats.embedding_backend ?? "clap").toLowerCase();
  const dim = stats.embedding_dim ?? 512;
  const model =
    backend === "clap"
      ? stats.clap_model_installed === false
        ? "CLAP missing"
        : "CLAP ready"
      : backend;
  const agent = (stats.agent_backend ?? "codex").toLowerCase();
  const agentLabel =
    stats.agent_ready === false ? `Viber ${agent} setup` : `Viber ${agent}`;
  const freshness = stats.library_freshness_status
    ? `library ${stats.library_freshness_status.replace(/_/g, " ")}`
    : "library unknown";
  return `${agentLabel} / ${model} / ${dim}d / ${stats.backend} / ${freshness}`;
}

function renderStats(stats: LibraryStats): void {
  latestStats = stats;
  $("vmx-lib-stat-indexed").textContent = String(stats.indexed);
  $("vmx-lib-stat-backend").textContent = stats.backend;
  $("vmx-lib-stat-spent").textContent = `€${stats.spent_eur.toFixed(2)}`;
  $("vmx-lib-stat-failed").textContent = String(stats.failed);
  const engineLabelEl = document.getElementById("vmx-lib-engine-label");
  if (engineLabelEl) engineLabelEl.textContent = embeddingLabel(stats);
  renderAgentSetup(stats);
  if (latestModels) renderModelSetup(latestModels);
}

function renderStatsError(err: unknown): void {
  latestStats = null;
  $("vmx-lib-stat-indexed").textContent = "·";
  $("vmx-lib-stat-backend").textContent = "unavailable";
  $("vmx-lib-stat-spent").textContent = "·";
  $("vmx-lib-stat-failed").textContent = "·";
  const engineLabelEl = document.getElementById("vmx-lib-engine-label");
  if (engineLabelEl) engineLabelEl.textContent = "library stats unavailable";
  renderAgentSetup(null);
  // eslint-disable-next-line no-console
  console.error("[vmx-lib] stats refresh failed:", err);
}

function installStatusLine(models: LibraryModelsResult): string | null {
  const install = models.install;
  if (!install) return null;

  const errors = install.results.flatMap((result) => result.errors);
  if (!install.ok) {
    const prefix =
      install.target === "cue"
        ? "Optional CUE setup unavailable"
        : "Model setup failed";
    return errors[0] ? `${prefix}: ${errors[0]}` : prefix;
  }

  const files = install.results.flatMap((result) => result.files);
  const downloaded = files.filter(
    (file) => file.status === "downloaded",
  ).length;
  const skipped = files.filter((file) => file.status === "skipped").length;
  const verified = downloaded + skipped;
  const prefix =
    install.target === "required"
      ? "Required models ready"
      : install.target === "cue"
        ? "Optional CUE checked"
        : install.target === "all"
          ? "Local models ready"
          : "CLAP ready";
  if (downloaded > 0)
    return `${prefix}: downloaded ${downloaded}/${files.length}`;
  if (verified > 0) return `${prefix}: verified ${verified} files`;
  return prefix;
}

function formatModelBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 MB";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${Math.round(bytes / (1024 * 1024))} MB`;
}

export function modelProgressStateText(progress: LibraryModelProgress): string {
  const model = progress.id === "cue-detr" ? "CUE" : "CLAP";
  const rel = progress.rel_path.split(/[\\/]/).pop() ?? progress.rel_path;
  const count = `${progress.n}/${progress.total}`;
  if (progress.status === "verified") {
    return `${model} verified ${count} · ${rel}`;
  }
  if (progress.status === "downloaded") {
    return `${model} downloaded ${count} · ${rel}`;
  }
  if (progress.status === "error") {
    return `${model} setup failed ${count} · ${rel}`;
  }
  const loaded = formatModelBytes(progress.downloaded);
  const total = formatModelBytes(progress.size);
  return `${model} downloading ${count} · ${rel} · ${loaded}/${total}`;
}

export interface ModelSetupView {
  stateText: string;
  installTarget: LibraryModelInstallTarget | null;
  installButtonHidden: boolean;
  installButtonText: string;
}

export function modelInstallTargetFromDataset(
  target: string | undefined,
): LibraryModelInstallTarget {
  return target === "cue" ||
    target === "all" ||
    target === "required" ||
    target === "clap"
    ? target
    : "required";
}

export function deriveModelSetupView(
  models: LibraryModelsResult,
): ModelSetupView {
  const clap = models.models.find((m) => m.id === "clap");
  const cue = models.models.find((m) => m.id === "cue-detr");
  const clapMismatched = (clap?.mismatched?.length ?? 0) > 0;
  const cueMismatched = (cue?.mismatched?.length ?? 0) > 0;
  const cueInstallable = cue?.installable === true;
  const installErrors =
    models.install?.results.flatMap((result) => result.errors) ?? [];
  const hasInstallError =
    installErrors.length > 0 || (models.install ? !models.install.ok : false);
  const clapLabel = clap?.installed
    ? "CLAP ready"
    : clapMismatched
      ? "CLAP repair"
      : "CLAP missing";
  const cueLabel = cue?.installed
    ? "CUE ready"
    : cueMismatched
      ? cueInstallable
        ? "CUE repair"
        : "CUE manual repair"
      : "CUE optional";
  const needsClap =
    clap?.installed === false ||
    clapMismatched ||
    models.required_ready === false;
  const needsCue =
    cueInstallable && (cue?.installed === false || cueMismatched);
  const installTarget: LibraryModelInstallTarget | null = needsClap
    ? "required"
    : needsCue
      ? "cue"
      : null;
  const installButtonText =
    installTarget === "required"
      ? hasInstallError
        ? "Retry Required Models"
        : "Install Required Models"
      : installTarget === "cue"
        ? hasInstallError
          ? "Retry Optional CUE"
          : cueMismatched
            ? "Repair CUE"
            : "Check Optional CUE"
        : "Install Required Models";

  return {
    stateText: [clapLabel, cueLabel, installStatusLine(models)]
      .filter(Boolean)
      .join(" · "),
    installTarget,
    installButtonHidden: installTarget === null,
    installButtonText,
  };
}

function renderModelSetup(models: LibraryModelsResult): void {
  latestModels = models;
  const stateEl = $("vmx-lib-model-state");
  const installBtn = $("vmx-lib-install-models") as HTMLButtonElement;
  const view = deriveModelSetupView(models);
  stateEl.textContent = view.stateText;
  renderAgentSetup(latestStats);

  if (view.installTarget) installBtn.dataset.installTarget = view.installTarget;
  else delete installBtn.dataset.installTarget;
  installBtn.hidden = view.installButtonHidden;
  installBtn.disabled = false;
  installBtn.textContent = view.installButtonText;
}

function renderModelSetupError(err: unknown): void {
  latestModels = null;
  const stateEl = $("vmx-lib-model-state");
  const installBtn = $("vmx-lib-install-models") as HTMLButtonElement;
  stateEl.textContent = `model check failed · ${errorMessage(err)}`;
  installBtn.hidden = true;
  installBtn.disabled = false;
  delete installBtn.dataset.installTarget;
  // eslint-disable-next-line no-console
  console.error("[vmx-lib] model refresh failed:", err);
}

function agentSetupHint(stats: LibraryStats | null): string | null {
  if (!stats || stats.agent_ready !== false) return null;
  const backend = (stats.agent_backend ?? "codex").toLowerCase();
  const status = (stats.agent_status ?? "setup_needed").replace(/_/g, " ");
  const hint = stats.agent_hint?.trim();
  return `Viber ${backend}: ${hint || status}`;
}

function renderAgentSetup(stats: LibraryStats | null): void {
  const setupEl = document.getElementById("vmx-lib-agent-setup");
  const stateEl = document.getElementById("vmx-lib-agent-state");
  if (!setupEl || !stateEl) return;

  const hint = agentSetupHint(stats);
  setupEl.hidden = hint === null;
  stateEl.textContent = hint ?? "";
}

function setProgress(
  n: number,
  total: number,
  costEur: number,
  note: string,
): void {
  const pct = total > 0 ? (n / total) * 100 : 0;
  ($("vmx-lib-progress-fill") as HTMLElement).style.transform =
    `scaleX(${Math.max(0, Math.min(1, pct / 100)).toFixed(3)})`;
  $("vmx-lib-prog-n").innerHTML =
    `${n}<small> / ${total}${note ? ` · ${esc(note)}` : ""}</small>`;
  $("vmx-lib-prog-cost").textContent = `~€${costEur.toFixed(2)}`;
}

function appendLog(
  status: EmbedProgress["status"],
  filename: string,
  costEur: number,
): void {
  const el = $("vmx-lib-loglist");
  el.insertAdjacentHTML(
    "afterbegin",
    `<div class="ll"><span class="st ${status}">${status}</span><span class="fn">${esc(filename)}</span><span class="c">~€${costEur.toFixed(3)}</span></div>`,
  );
}

function appendChatTurn(
  thread: HTMLElement,
  role: LibraryChatTurn["role"],
  text: string,
  pending = false,
): HTMLElement {
  const turn = document.createElement("div");
  turn.className = "vmx-lib-chat-turn";
  turn.dataset.role = role === "you" ? "you" : "viber";
  if (pending) turn.dataset.pending = "true";

  const who = document.createElement("div");
  who.className = "who";
  who.textContent = role === "you" ? "you" : "viber";

  const body = document.createElement("div");
  body.className = "body";
  body.textContent = text;

  turn.append(who, body);
  thread.append(turn);
  thread.scrollTop = thread.scrollHeight;
  return turn;
}

function setChatTurnText(
  turn: HTMLElement,
  text: string,
  pending = false,
): void {
  const body = turn.querySelector<HTMLElement>(".body");
  if (body) body.textContent = text;
  if (pending) turn.dataset.pending = "true";
  else delete turn.dataset.pending;
}

function ensureChatIntro(thread: HTMLElement): void {
  if (thread.childElementCount > 0) return;
  appendChatTurn(thread, "viber", "In your library. What are we chasing?");
}

function renderChatBusy(): void {
  const tools = $("vmx-lib-chat-tools");
  tools.replaceChildren();
  appendLiveProofStatusToolRow(tools, latestLiveContext);
  const row = document.createElement("div");
  row.className = "vmx-lib-chat-tool";
  row.dataset.ok = "true";
  row.append(document.createElement("span"));
  row.firstElementChild?.classList.add("gem");
  const text = document.createElement("div");
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = "thinking";
  const arg = document.createElement("div");
  arg.className = "arg";
  arg.textContent = "grounding turn";
  text.append(name, arg);
  row.append(text);
  tools.append(row);
  $("vmx-lib-chat-artifact").replaceChildren();
  $("vmx-lib-scope-state").textContent = "working";
}

function proofDeckResolved(deck?: LibraryLiveDeck): boolean {
  if (!deck) return false;
  return (
    (deck.confidence ?? 0) >= 0.3 &&
    Boolean(deck.title || deck.track_id || deck.camelot)
  );
}

const LIVE_TRUSTED_DECK_SOURCES = new Set([
  "rekordbox_xml",
  "folder_cache",
  "screen_vision",
  "numpy_key",
  "nowplaying",
]);

function proofDeckCitable(deck?: LibraryLiveDeck): boolean {
  return (deck?.confidence ?? 0) >= 0.3 && Boolean(deck?.track_id);
}

function proofDeckSourced(deck?: LibraryLiveDeck): boolean {
  const source = deck?.source ?? "";
  return proofDeckCitable(deck) && LIVE_TRUSTED_DECK_SOURCES.has(source);
}

function liveDeckPairResolved(context: LibraryLiveContext): boolean {
  const deckState = context.deck_state ?? {};
  return proofDeckResolved(deckState.A) && proofDeckResolved(deckState.B);
}

function liveDeckPairCitable(context: LibraryLiveContext): boolean {
  const deckState = context.deck_state ?? {};
  return proofDeckCitable(deckState.A) && proofDeckCitable(deckState.B);
}

function liveDeckPairSourced(context: LibraryLiveContext): boolean {
  const deckState = context.deck_state ?? {};
  return proofDeckSourced(deckState.A) && proofDeckSourced(deckState.B);
}

function proofRouteTier(score: number): string {
  if (score <= 0.04) return "muted";
  if (score < 0.2) return "low";
  if (score < 0.45) return "present";
  return "dominant";
}

function proofXfaderFactor(side: "A" | "B", xfader: number): number {
  if (side === "A") {
    if (xfader >= 112) return 0;
    if (xfader >= 80) return 0.3;
    if (xfader >= 48) return 0.7;
    return 1;
  }
  if (xfader < 16) return 0;
  if (xfader < 48) return 0.3;
  if (xfader <= 80) return 0.7;
  return 1;
}

function proofRouteScores(
  context: LibraryLiveContext,
): Array<[string, number]> {
  const mixer = context.deck_mixer;
  if (!mixer?.connected) return [];
  const xfader = Math.max(0, Math.min(127, Math.round(mixer.xfader ?? 64)));
  return (["A", "B"] as const).map((side) => {
    const row = mixer[side];
    if (!row) return [side, 0];
    const volume = Math.max(0, Math.min(127, Math.round(row.vol ?? 0))) / 127;
    let score = volume * proofXfaderFactor(side, xfader);
    if (volume < 0.1) score = 0;
    return [side, Math.max(0, Math.min(1, score))];
  });
}

function liveDeckIdentity(deck?: LibraryLiveDeck): string {
  if (!deck) return "unknown";
  return proofDeckResolved(deck) ? "known" : "unresolved";
}

function deckLaneSummary(context: LibraryLiveContext | null): string | null {
  if (!context) return null;
  const deckState = context.deck_state ?? {};
  const scoreMap = new Map(proofRouteScores(context));
  const aRoute = scoreMap.has("A")
    ? proofRouteTier(scoreMap.get("A") ?? 0)
    : "unknown";
  const bRoute = scoreMap.has("B")
    ? proofRouteTier(scoreMap.get("B") ?? 0)
    : "unknown";
  return `deck1 A=${liveDeckIdentity(deckState.A)}:${aRoute} / deck2 B=${liveDeckIdentity(deckState.B)}:${bRoute}`;
}

function hasLiveProofTransitionGate(context: LibraryLiveContext): boolean {
  return (context.live_evidence?.mix ?? []).some(
    (token) =>
      token.includes("transition_block=") ||
      token.includes("transition_watch=") ||
      token.includes("transition_candidate="),
  );
}

function liveDeckPairCaptureConfigured(context: LibraryLiveContext): boolean {
  const text = context.deck_audio_separation_context ?? "";
  return (
    text.includes("mode=deck_pair_capture_configured") &&
    text.includes("deckA_audio=captured") &&
    text.includes("deckB_audio=captured") &&
    text.includes("per_deck_audio=captured_not_attached")
  );
}

function liveEvidenceTokens(
  context: LibraryLiveContext,
  needle: string,
): string[] {
  return [
    ...(context.live_evidence?.mix ?? []),
    ...(context.live_evidence?.refs ?? []),
  ].filter((token) => token.includes(needle));
}

function liveDeckAudioCaptureTokens(context: LibraryLiveContext): string[] {
  return liveEvidenceTokens(context, "deck_audio_capture=");
}

function liveDeckAudioCaptureActive(context: LibraryLiveContext): boolean {
  return liveDeckAudioCaptureTokens(context).some(
    (token) => token.includes("A_active") || token.includes("B_active"),
  );
}

function liveDeckAudioCaptureBothActive(context: LibraryLiveContext): boolean {
  return liveDeckAudioCaptureTokens(context).some(
    (token) => token.includes("A_active") && token.includes("B_active"),
  );
}

function liveProofStatus(context: LibraryLiveContext | null): {
  ok: boolean;
  state: string;
  detail: string;
} {
  if (!context) {
    return { ok: false, state: "waiting", detail: "live deck feed" };
  }
  const capabilities = new Set(context.live_context_capabilities ?? []);
  const transportOk =
    (context.live_context_schema_version ?? 0) >= 2 &&
    [
      "deck_source_status",
      "audio_part_context",
      "deck_audio_separation_context",
      "deck_audio_features_context",
      "deck_audio_delta_context",
      "deck_audio_window_context",
      "audio_window_map",
      "audio_delta",
      "live_evidence",
    ].every((capability) => capabilities.has(capability));
  if (!transportOk) {
    return { ok: false, state: "partial", detail: "transport stale" };
  }
  const missing: string[] = [];
  if (!context.deck_lanes_context || !context.deck_reference_context) {
    missing.push("lanes");
  }
  if (!context.deck_source_context || !context.deck_source_status) {
    missing.push("source");
  }
  if (!liveDeckPairResolved(context)) {
    missing.push("deck identities");
  }
  if (!liveDeckPairCitable(context)) {
    missing.push("deck track IDs");
  } else if (!liveDeckPairSourced(context)) {
    missing.push("deck sources");
  }
  if (
    !context.deck_audio_context ||
    !context.deck_audio_separation_context ||
    !context.audio_window_context ||
    !context.audio_window_map
  ) {
    missing.push("audio map");
  }
  if (!hasLiveProofTransitionGate(context)) {
    missing.push("gate");
  }
  if (!liveDeckPairCaptureConfigured(context)) {
    missing.push("deck audio");
  } else if (!context.deck_audio_features_context) {
    missing.push("deck audio features");
  } else if (!context.deck_audio_delta_context) {
    missing.push("deck audio delta");
  } else if (!context.deck_audio_window_context) {
    missing.push("deck audio window");
  } else if (liveDeckAudioCaptureTokens(context).length === 0) {
    missing.push("deck audio receipt");
  } else if (!liveDeckAudioCaptureActive(context)) {
    missing.push("deck audio idle");
  } else if (!liveDeckAudioCaptureBothActive(context)) {
    missing.push("both decks active");
  } else if (liveEvidenceTokens(context, "deck_audio_features=").length === 0) {
    missing.push("deck audio feature receipt");
  } else if (liveEvidenceTokens(context, "deck_audio_delta=").length === 0) {
    missing.push("deck audio delta receipt");
  } else if (liveEvidenceTokens(context, "deck_audio_window=").length === 0) {
    missing.push("deck audio window receipt");
  }
  if (missing.length > 0) {
    return {
      ok: false,
      state: "partial",
      detail: missing.slice(0, 2).join(" + "),
    };
  }
  return {
    ok: true,
    state: "armed",
    detail: deckLaneSummary(context) ?? "deck lanes armed",
  };
}

function appendLiveProofStatusToolRow(
  tools: HTMLElement,
  context: LibraryLiveContext | null,
): void {
  const status = liveProofStatus(context);
  const row = document.createElement("div");
  row.className = "vmx-lib-chat-tool";
  row.dataset.ok = String(status.ok);
  row.dataset.proof = "true";
  row.dataset.proofState = status.state.replace(/\s+/g, "_");
  const gem = document.createElement("span");
  gem.className = "gem";
  const text = document.createElement("div");
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = "live read";
  const arg = document.createElement("div");
  arg.className = "arg";
  arg.textContent = `${status.state} · ${status.detail}`;
  text.append(name, arg);
  row.append(gem, text);
  tools.append(row);
}

function renderChatIdleSide(): void {
  const tools = $("vmx-lib-chat-tools");
  if (tools.dataset.live === "true") return;
  tools.replaceChildren();
  appendLiveProofStatusToolRow(tools, latestLiveContext);
  $("vmx-lib-chat-artifact").replaceChildren();
  $("vmx-lib-scope-state").textContent = liveProofStatus(latestLiveContext).ok
    ? "live read armed"
    : "ready";
}

/** Append one live tool-tape row as Viber fires it (the agentic work made
 *  visible). XSS-safe: textContent only, no innerHTML. The first event of a run
 *  clears any placeholder ("thinking" / "no tools this turn"). */
function appendLiveToolRow(e: LibraryViberToolEvent): void {
  const tools = $("vmx-lib-chat-tools");
  if (tools.dataset.live !== "true") {
    tools.replaceChildren();
    tools.dataset.live = "true";
  }
  const row = document.createElement("div");
  row.className = "vmx-lib-chat-tool";
  row.dataset.ok = String(e.ok);
  const gem = document.createElement("span");
  gem.className = "gem";
  const text = document.createElement("div");
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = chatToolDisplayName(e.tool);
  const arg = document.createElement("div");
  arg.className = "arg";
  arg.textContent = chatToolDisplayArg(e.tool, e.summary, e.ok);
  text.append(name, arg);
  row.append(gem, text);
  tools.append(row);
  tools.scrollTop = tools.scrollHeight;
}

function liveVerificationStateText(v: LibraryLiveVerification): string {
  const transport =
    v.transport_status === "fresh_schema_v2"
      ? "fresh"
      : v.transport_status === "missing_live_context"
        ? "waiting"
        : v.transport_status === "stale_or_pre_schema_v2"
          ? "partial"
          : "checked";
  const policy =
    v.claim_policy === "requires_more_evidence"
      ? "listening"
      : v.claim_policy === "blocked" || v.claim_policy === "watch_not_claim"
        ? "live move checked"
        : v.claim_policy === "candidate_not_verdict"
          ? "setup noted"
          : v.claim_policy === "supported_verdict"
            ? "scoring grounded"
          : "ready";
  const result = v.ok ? (v.guard_applied ? "grounded" : "checked") : "waiting";
  return `${transport} · ${policy} · ${result}`;
}

function appendLiveVerificationToolRow(
  tools: HTMLElement,
  verification: LibraryLiveVerification,
): void {
  const row = document.createElement("div");
  row.className = "vmx-lib-chat-tool";
  row.dataset.ok = String(verification.ok);
  row.dataset.proof = "true";
  const gem = document.createElement("span");
  gem.className = "gem";
  const text = document.createElement("div");
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = "live read";
  const arg = document.createElement("div");
  arg.className = "arg";
  arg.textContent = liveVerificationStateText(verification);
  text.append(name, arg);
  row.append(gem, text);
  tools.append(row);
}

function isInternalLiveProofTool(tool: LibraryChatToolTrace): boolean {
  return tool.name === "live_context_required";
}

function chatToolDisplayName(name: string): string {
  return name === "live_context_required" ? "live read" : name;
}

function chatToolDisplayArg(name: string, arg: string, ok: boolean): string {
  if (name === "live_context_required") return "waiting";
  return arg || (ok ? "ok" : "failed");
}

function chatScopeStateText(result: LibraryChatResult): string {
  if (isChatSetupStop(result.stop_reason))
    return `setup · ${result.stop_reason}`;
  if (result.stop_reason === "live_context_required")
    return "live read waiting";
  return `${result.iterations} iter · ${result.stop_reason}`;
}

function renderChatSide(result: LibraryChatResult): void {
  const tools = $("vmx-lib-chat-tools");
  tools.replaceChildren();
  if (result.live_verification) {
    appendLiveVerificationToolRow(tools, result.live_verification);
  } else {
    appendLiveProofStatusToolRow(tools, latestLiveContext);
  }
  if (result.tool_trace.length === 0 && !result.live_verification) {
    const empty = document.createElement("div");
    empty.className = "vmx-lib-chat-empty";
    empty.textContent = "no tools this turn";
    tools.append(empty);
  }
  if (result.tool_trace.length > 0) {
    result.tool_trace
      .filter(
        (tool) => !(result.live_verification && isInternalLiveProofTool(tool)),
      )
      .forEach((tool) => {
        const row = document.createElement("div");
        row.className = "vmx-lib-chat-tool";
        row.dataset.ok = String(tool.ok);
        const gem = document.createElement("span");
        gem.className = "gem";
        const text = document.createElement("div");
        const name = document.createElement("div");
        name.className = "name";
        name.textContent = chatToolDisplayName(tool.name);
        const arg = document.createElement("div");
        arg.className = "arg";
        arg.textContent = chatToolDisplayArg(tool.name, tool.arg, tool.ok);
        text.append(name, arg);
        row.append(gem, text);
        tools.append(row);
      });
  }

  const artifact = $("vmx-lib-chat-artifact");
  artifact.replaceChildren();
  const card = chatArtifactCard(result);
  if (card) artifact.append(card);
  $("vmx-lib-scope-state").textContent = chatScopeStateText(result);
}

function isChatSetupStop(stopReason: string): boolean {
  return (
    stopReason === "codex_not_installed" ||
    stopReason === "codex_auth_required" ||
    stopReason === "codex_mcp_blocked"
  );
}

function isChatClarification(result: LibraryChatResult): boolean {
  return result.stop_reason === "clarification_needed";
}

function chatArtifactCard(result: LibraryChatResult): HTMLElement | null {
  const setupStop = isChatSetupStop(result.stop_reason);
  const clarification = isChatClarification(result);
  if (
    !setupStop &&
    !clarification &&
    !result.live_verification &&
    !result.playlist &&
    !result.export_path &&
    result.move_grades.length === 0 &&
    result.seen_track_ids.length === 0
  ) {
    return null;
  }

  const card = document.createElement("div");
  card.className = "vmx-lib-chat-card";
  const cap = document.createElement("div");
  cap.className = "cap";
  const led = document.createElement("span");
  led.className = "led";
  const label = document.createElement("span");
  label.textContent = result.playlist
    ? "playlist"
    : result.export_path
      ? "export"
      : clarification
        ? "clarify"
        : setupStop
          ? "setup"
          : result.live_verification
            ? "live read"
            : result.move_grades.length > 0
              ? "moves"
              : "receipts";
  cap.append(led, label);
  card.append(cap);

  if (clarification) {
    card.dataset.wire = "library.chat-clarification";
    appendChatCardLine(
      card,
      result.question || "Viber needs one detail before it can continue.",
    );
    (result.choices || []).forEach((choice, index) => {
      appendChatCardLine(card, `${index + 1}. ${choice}`);
    });
  }
  if (setupStop) {
    appendChatCardLine(card, chatSetupTitle(result.stop_reason));
    if (result.reply) appendChatCardLine(card, result.reply);
  }
  if (result.live_verification) {
    appendChatLiveVerificationLines(card, result.live_verification);
  }
  if (result.playlist) {
    appendChatCardLine(card, result.playlist.name);
    appendChatCardLine(card, `${result.playlist.track_ids.length} tracks`);
    if (result.playlist.m3u_path)
      appendChatCardLine(card, result.playlist.m3u_path);
    appendChatSetBreakdown(card, result.playlist, result.move_grades);
  }
  if (result.export_path) appendChatCardLine(card, result.export_path);
  result.move_grades
    .slice(0, 4)
    .forEach((grade) => appendChatMoveGradeLine(card, grade));
  if (!result.playlist && result.seen_track_ids.length > 0) {
    appendChatCardLine(card, result.seen_track_ids.slice(0, 6).join(" · "));
  }
  return card;
}

function appendChatLiveVerificationLines(
  card: HTMLElement,
  verification: LibraryLiveVerification,
): void {
  appendChatCardLine(
    card,
    `live read: ${liveVerificationStateText(verification)}`,
  );
  if (verification.move_grades_seen > 0 && !verification.move_grades_allowed) {
    appendChatCardLine(card, "move scoring waits for a stronger live read");
  }
  if (verification.move_grades_seen > 0 && verification.move_grades_allowed) {
    appendChatCardLine(card, "move scoring grounded by live read");
  }
}

function chatSetupTitle(stopReason: string): string {
  if (stopReason === "codex_not_installed") return "Codex CLI missing";
  if (stopReason === "codex_auth_required") return "Codex login needed";
  if (stopReason === "codex_mcp_blocked") return "Codex MCP blocked";
  return "Agent setup needed";
}

function appendChatCardLine(card: HTMLElement, text: string): void {
  const line = document.createElement("div");
  line.className = "line";
  line.textContent = text;
  card.append(line);
}

/** The ordered "01. track" set view a built/curated playlist deserves — the
 *  affordance the dedicated Curate/Build tabs used to own. The chat playlist
 *  carries only track_ids (no titles), so titles are enriched from move_grades
 *  when present and the bare id is the honest fallback otherwise (same no-
 *  fabrication contract as renderCurate). Built with textContent, never HTML. */
function appendChatSetBreakdown(
  card: HTMLElement,
  playlist: LibraryChatPlaylist,
  moveGrades: LibraryChatMoveGrade[],
): void {
  if (playlist.track_ids.length === 0) return;
  const titleById = new Map<string, string>();
  moveGrades.forEach((grade) => {
    if (grade.title) titleById.set(grade.track_id, grade.title);
  });
  const set = document.createElement("div");
  set.className = "set";
  set.dataset.wire = "library.chat-set-breakdown";
  playlist.track_ids.forEach((id, i) => {
    const row = document.createElement("div");
    row.className = "setrow";
    const rank = document.createElement("span");
    rank.className = "rank";
    rank.textContent = String(i + 1).padStart(2, "0");
    const title = document.createElement("span");
    title.className = "t";
    title.textContent = titleById.get(id) || id;
    row.append(rank, title);
    set.append(row);
  });
  card.append(set);
  if (playlist.dropped_ids.length > 0) {
    appendChatCardLine(card, `${playlist.dropped_ids.length} dropped`);
  }
}

function chatMoveGradeInt(
  value: number | undefined,
  min: number,
  max: number,
): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  const next = Math.trunc(value);
  if (next < min) return null;
  return Math.min(next, max);
}

function chatMoveGradeProgressText(grade: LibraryChatMoveGrade): string {
  const parts: string[] = [];
  const level = chatMoveGradeInt(grade.level, 1, 999);
  const levelXp = chatMoveGradeInt(grade.level_xp, 0, 999_999);
  const nextLevelXp = chatMoveGradeInt(grade.next_level_xp, 1, 999_999);
  if (level !== null) {
    parts.push(
      levelXp !== null && nextLevelXp !== null
        ? `LV${level} ${levelXp}/${nextLevelXp}xp`
        : `LV${level}`,
    );
  }
  const streak = chatMoveGradeInt(grade.streak, 0, 999);
  if (streak !== null && streak > 1) parts.push(`x${streak}`);
  if (grade.level_up === true) {
    const levelsGained = chatMoveGradeInt(grade.levels_gained, 0, 999);
    parts.push(
      levelsGained !== null && levelsGained > 1
        ? `LEVEL UP x${levelsGained}`
        : "LEVEL UP",
    );
  }
  return parts.join(" / ");
}

function chatMoveGradeIntelState(
  grade: LibraryChatMoveGrade,
): "care" | "earned" | "overdrive" {
  if (grade.level_up === true || grade.overdrive) return "overdrive";
  if (grade.slug === "negative" || grade.slug === "mid") return "care";
  return "earned";
}

function chatMoveGradeTitle(grade: LibraryChatMoveGrade): string {
  if (grade.level_up === true || grade.overdrive) return "DJ KNOWS";
  return grade.reason ? `DJ KNOWS · ${grade.reason}` : "DJ KNOWS";
}

function appendChatMoveGradeLine(
  card: HTMLElement,
  grade: LibraryChatMoveGrade,
): void {
  const row = document.createElement("div");
  row.className = "vmx-lib-chat-grade";
  row.dataset.wire = "library.chat-move-grade";
  row.dataset.moveGrade = grade.slug;
  row.dataset.overdrive = grade.overdrive ? "true" : "false";
  row.dataset.levelUp = grade.level_up === true ? "true" : "false";
  row.dataset.intel = chatMoveGradeIntelState(grade);
  const level = chatMoveGradeInt(grade.level, 1, 999);
  if (level !== null) row.dataset.gradeLevel = String(level);
  const totalXp = chatMoveGradeInt(grade.total_xp, 0, 999_999);
  if (totalXp !== null) row.dataset.totalXp = String(totalXp);
  row.title = chatMoveGradeTitle(grade);
  row.setAttribute("aria-label", chatMoveGradeTitle(grade));

  const label = document.createElement("span");
  label.className = "grade-label";
  label.textContent = grade.label;

  const xp = document.createElement("span");
  xp.className = "grade-xp";
  xp.textContent = grade.xp > 0 ? `+${grade.xp}xp` : "0xp";

  const title = document.createElement("span");
  title.className = "grade-title";
  title.textContent = grade.title || grade.track_id;

  const meta = document.createElement("span");
  meta.className = "grade-meta";
  const progressText = chatMoveGradeProgressText(grade);
  if (progressText) {
    const progress = document.createElement("span");
    progress.className = "grade-progress";
    progress.textContent = progressText;
    meta.append(progress);
  }

  const reason = document.createElement("span");
  reason.className = "grade-reason";
  reason.textContent = grade.reason;

  meta.append(reason);
  row.append(label, xp, title, meta);
  card.append(row);
}

function renderChatError(err: unknown): void {
  const msg =
    err instanceof Error
      ? err.message
      : typeof err === "string"
        ? err
        : String(err);
  const artifact = $("vmx-lib-chat-artifact");
  artifact.replaceChildren();
  const card = document.createElement("div");
  card.className = "vmx-lib-chat-card";
  const cap = document.createElement("div");
  cap.className = "cap";
  const led = document.createElement("span");
  led.className = "led";
  const label = document.createElement("span");
  label.textContent = "engine error";
  cap.append(led, label);
  card.append(cap);
  appendChatCardLine(card, msg);
  artifact.append(card);
  $("vmx-lib-chat-tools").replaceChildren();
  $("vmx-lib-scope-state").textContent = "error";
}

// ── Bootstrap ───────────────────────────────────────────────────────────────

export function mountLibrary(): void {
  let state: LibraryState = initialLibraryState;
  let busy = false;
  let runSeq = 0;
  let cancelActiveRun: (() => void) | null = null;

  const qInput = $("vmx-lib-q") as HTMLInputElement;
  const folderInput = $("vmx-lib-folder") as HTMLInputElement;
  const cueFolderInput = $("vmx-lib-cue-folder") as HTMLInputElement;
  const themeInput = $("vmx-lib-theme") as HTMLInputElement;
  const briefInput = $("vmx-lib-brief") as HTMLTextAreaElement;
  const chatInput = $("vmx-lib-chat") as HTMLTextAreaElement;
  const runBtn = $("vmx-lib-runbtn") as HTMLButtonElement;
  const installModelsBtn = $("vmx-lib-install-models") as HTMLButtonElement;
  const echoEl = $("vmx-lib-echo");
  const qlabelEl = $("vmx-lib-qlabel");
  const seedNameEl = $("vmx-lib-seed-name");
  const chatThread = $("vmx-lib-chat-thread");
  const chatHistory: LibraryChatTurn[] = [];

  // restore initial field values from state
  qInput.value = state.query;
  folderInput.value = state.folder;
  cueFolderInput.value = state.cueFolder;
  themeInput.value = state.theme;
  briefInput.value = state.brief;
  chatInput.value = state.chatMessage;
  seedNameEl.textContent = state.seed;

  function applyModeVisibility(): void {
    document.body.dataset.mode = state.mode;
    document
      .querySelectorAll<HTMLElement>(".vmx-lib-modeswitch button")
      .forEach((b) => {
        b.setAttribute("aria-selected", String(b.dataset.mode === state.mode));
      });
    document.querySelectorAll<HTMLElement>("[data-for]").forEach((el) => {
      const modes = (el.dataset.for ?? "").split(" ");
      el.style.display = modes.includes(state.mode) ? "" : "none";
    });
    qlabelEl.textContent = fieldLabel(state.mode);
    $("vmx-lib-center-label").textContent =
      state.mode === "chat"
        ? "Viber"
        : state.mode === "build"
          ? "Built"
          : state.mode === "cue"
            ? "Cued"
          : state.mode === "curate"
            ? "Curated"
            : state.mode === "ingest"
              ? "Embed"
              : "Pulled";
    $("vmx-lib-side-label").textContent =
      state.mode === "chat" ? "Grounding" : "Vibe scope";
    runBtn.textContent = runLabel(state.mode);
    echoEl.textContent = echoText(state);
    if (state.mode === "chat") {
      ensureChatIntro(chatThread);
      if (!busy) renderChatIdleSide();
    }
  }

  async function refreshStats(): Promise<void> {
    try {
      renderStats(await libraryStats());
    } catch (err) {
      renderStatsError(err);
    }
  }

  async function refreshModels(): Promise<void> {
    try {
      renderModelSetup(await libraryModels());
    } catch (err) {
      renderModelSetupError(err);
    }
  }

  function currentInstallTarget(): LibraryModelInstallTarget {
    return modelInstallTargetFromDataset(
      installModelsBtn.dataset.installTarget,
    );
  }

  function isCurrentRun(runId: number, mode: LibraryMode): boolean {
    return runSeq === runId && state.mode === mode;
  }

  function cancelRun(): void {
    if (!busy) return;
    runSeq += 1;
    busy = false;
    runBtn.disabled = false;
    const cancel = cancelActiveRun;
    cancelActiveRun = null;
    cancel?.();
  }

  async function installLocalModels(): Promise<void> {
    const target = currentInstallTarget();
    installModelsBtn.disabled = true;
    installModelsBtn.textContent = "Installing…";
    let runningLabel = "CLAP install running";
    if (target === "required") runningLabel = "required model setup running";
    else if (target === "all") runningLabel = "local model setup running";
    else if (target === "cue") runningLabel = "CUE setup check running";
    $("vmx-lib-model-state").textContent = runningLabel;
    try {
      renderModelSetup(await libraryModels(target));
      await refreshStats();
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "string"
            ? err
            : String(err);
      $("vmx-lib-model-state").textContent = `install failed · ${msg}`;
      installModelsBtn.disabled = false;
      let retryLabel = "Retry CLAP";
      if (target === "all") retryLabel = "Retry Local Models";
      else if (target === "required") retryLabel = "Retry Required Models";
      else if (target === "cue") retryLabel = "Retry Optional CUE";
      installModelsBtn.textContent = retryLabel;
    }
  }

  // ── run actions ──────────────────────────────────────────────────────────

  async function runSearch(runId: number): Promise<void> {
    state = setQuery(state, qInput.value.trim() || state.query);
    echoEl.textContent = state.query;
    const result = await librarySearch(state.query);
    if (!isCurrentRun(runId, "search")) return;
    renderResults(result, "search");
  }

  async function runSimilar(runId: number): Promise<void> {
    echoEl.textContent = state.seed;
    const result = await librarySimilar(state.seed);
    if (!isCurrentRun(runId, "similar")) return;
    renderResults(result, "similar");
  }

  async function runCurate(runId: number): Promise<void> {
    state = setTheme(state, themeInput.value.trim() || state.theme);
    echoEl.textContent = state.theme;
    renderCurateLoading(state.theme); // working state before the (slow) agent call
    const result = await libraryCurate(state.theme);
    if (!isCurrentRun(runId, "curate")) return;
    renderCurate(result);
  }

  async function runBuildSet(runId: number): Promise<void> {
    state = setBrief(state, briefInput.value.trim() || state.brief);
    echoEl.textContent = state.brief;
    renderBuildSetLoading(state.brief); // working state before the (slow) agent call
    const result = await libraryBuildSet(state.brief, state.curve);
    if (!isCurrentRun(runId, "build")) return;
    renderBuildSet(result);
  }

  async function runCueExport(runId: number): Promise<void> {
    state = setCueFolder(
      state,
      cueFolderInput.value.trim() || state.cueFolder,
    );
    echoEl.textContent = state.cueFolder;
    renderCueLoading(state.cueFolder);
    const result = await libraryCueFolder(state.cueFolder, state.cueExport);
    if (!isCurrentRun(runId, "cue")) return;
    renderCueExport(result);
  }

  async function runChat(runId: number): Promise<void> {
    state = setChatMessage(state, chatInput.value.trim());
    if (!state.chatMessage) {
      renderChatIdleSide();
      return;
    }
    const message = state.chatMessage;
    const priorHistory = chatHistory.slice();

    appendChatTurn(chatThread, "you", message);
    chatHistory.push({ role: "you", text: message });
    chatInput.value = "";
    state = setChatMessage(state, "");
    echoEl.textContent = "conversation";

    const pending = appendChatTurn(chatThread, "viber", "", true);
    cancelActiveRun = () => {
      pending.remove();
      const lastTurn = chatHistory[chatHistory.length - 1];
      if (lastTurn?.role === "you" && lastTurn.text === message) {
        chatHistory.pop();
      }
    };
    renderChatBusy();
    try {
      const liveContext = liveContextForChat(latestLiveContext);
      const result = liveContext
        ? await libraryChat(message, priorHistory, liveContext)
        : await libraryChat(message, priorHistory);
      if (!isCurrentRun(runId, "chat")) return;
      const reply = result.reply || "I came back empty.";
      setChatTurnText(pending, reply);
      chatHistory.push({ role: "viber", text: reply });
      renderChatSide(result);
    } catch (err) {
      if (!isCurrentRun(runId, "chat")) return;
      // eslint-disable-next-line no-console
      console.error("[vmx-lib] chat failed:", err);
      const lastTurn = chatHistory[chatHistory.length - 1];
      if (lastTurn?.role === "you" && lastTurn.text === message) {
        chatHistory.pop();
      }
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "string"
            ? err
            : String(err);
      setChatTurnText(pending, `engine error: ${msg}`);
      renderChatError(err);
    }
  }

  /** Reflect the active curve onto the segmented picker's pressed state. */
  function syncCurvePicker(): void {
    document.querySelectorAll<HTMLElement>("[data-curve]").forEach((c) => {
      c.setAttribute("aria-pressed", String(c.dataset.curve === state.curve));
    });
  }

  /** Drive the ingest progress bar + log. If the bridge accepts the job, the
   *  Tauri `library://embed-*` events drive the UI. Otherwise (no bridge) we
   *  replay the real subset-run log so the surface is demoable. */
  async function runIngest(runId: number): Promise<void> {
    state = setFolder(state, folderInput.value.trim() || state.folder);
    $("vmx-lib-loglist").innerHTML = "";
    setProgress(0, DEV_FALLBACK.embedLog.length, 0, "");

    const accepted = await libraryEmbedFolder(state.folder, state.strategy);
    if (!isCurrentRun(runId, "ingest")) return;
    if (accepted) return; // bridge live — events take over via the listeners below

    // dev replay — step through the captured log on a timer
    const log = DEV_FALLBACK.embedLog;
    const total = log.length;
    let i = 0;
    const tick = (): void => {
      if (!isCurrentRun(runId, "ingest")) return;
      if (i >= total) {
        void refreshStats();
        busy = false;
        runBtn.disabled = false;
        return;
      }
      const entry = log[i];
      if (entry) {
        const [status, filename, cost] = entry;
        appendLog(status, filename, cost);
        setProgress(i + 1, total, cost, filename.replace(/\.[a-z0-9]+$/i, ""));
      }
      i++;
      window.setTimeout(tick, 280);
    };
    tick();
  }

  async function run(): Promise<void> {
    if (busy) return;
    busy = true;
    runBtn.disabled = true;
    const runId = ++runSeq;
    const modeAtStart = state.mode;
    cancelActiveRun = null;
    // Reset the live tool tape for the Viber/Codex modes that stream tool calls,
    // so each run's tape starts clean (the listener repopulates it live).
    if (
      modeAtStart === "chat" ||
      modeAtStart === "curate" ||
      modeAtStart === "build"
    ) {
      const liveTools = $("vmx-lib-chat-tools");
      liveTools.replaceChildren();
      delete liveTools.dataset.live;
    }
    try {
      if (modeAtStart === "search") await runSearch(runId);
      else if (modeAtStart === "similar") await runSimilar(runId);
      else if (modeAtStart === "curate") await runCurate(runId);
      else if (modeAtStart === "build") await runBuildSet(runId);
      else if (modeAtStart === "cue") await runCueExport(runId);
      else if (modeAtStart === "chat") await runChat(runId);
      else {
        await runIngest(runId);
        return; // ingest manages its own busy lifecycle (events or replay)
      }
    } catch (err) {
      if (!isCurrentRun(runId, modeAtStart)) return;
      // A REAL backend error (empty cache, missing key, bad strategy) — show it
      // honestly instead of masking it with fake data (anti-slop). The ingest
      // path lands here too on a real bridge error, so we must release its
      // busy/disabled lifecycle here rather than leaving the button wedged.
      // eslint-disable-next-line no-console
      console.error("[vmx-lib] run failed:", err);
      renderError(err);
      if (modeAtStart === "ingest") {
        busy = false;
        runBtn.disabled = false;
      }
    } finally {
      if (isCurrentRun(runId, modeAtStart) && modeAtStart !== "ingest") {
        busy = false;
        runBtn.disabled = false;
        cancelActiveRun = null;
      }
    }
  }

  // ── event wiring ───────────────────────────────────────────────────────────

  runBtn.addEventListener("click", () => void run());
  installModelsBtn.addEventListener("click", () => void installLocalModels());

  qInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.mode === "search") void run();
  });
  folderInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.mode === "ingest") void run();
  });
  cueFolderInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.mode === "cue") void run();
  });
  themeInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.mode === "curate") void run();
  });
  // Brief is a textarea (multi-line set briefs) — Enter SUBMITS, Shift+Enter
  // inserts a newline (the familiar chat-input contract; a brief is usually one
  // line so plain Enter running is the fast path).
  briefInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && state.mode === "build") {
      e.preventDefault();
      void run();
    }
  });
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && state.mode === "chat") {
      e.preventDefault();
      void run();
    }
  });

  document
    .querySelectorAll<HTMLElement>(".vmx-lib-modeswitch button")
    .forEach((b) => {
      b.addEventListener("click", () => {
        const previousMode = state.mode;
        const mode = (b.dataset.mode ?? "search") as LibraryMode;
        if (mode !== previousMode) cancelRun();
        state = setMode(state, mode);
        applyModeVisibility();
        // The set-notes block is shared by curate + build; only clear it when
        // leaving BOTH so a fresh build/curate keeps its own working state.
        if (mode !== "curate" && mode !== "build" && mode !== "cue")
          clearRationale();
        if (
          (mode === "curate" || mode === "build" || mode === "cue") &&
          previousMode !== mode
        ) {
          renderAgentIdle(mode);
        }
        if (mode === "build") syncCurvePicker();
        if (mode === "ingest") {
          // show last-known progress shape, don't auto-run
          $("vmx-lib-loglist").innerHTML = "";
          setProgress(0, DEV_FALLBACK.embedLog.length, 0, "");
        } else if (mode === "chat") {
          ensureChatIntro(chatThread);
        } else if (mode === "search" || mode === "similar") {
          void run();
        }
      });
    });

  // vibe-query suggestion chips (search mode)
  document.querySelectorAll<HTMLElement>("[data-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (state.mode !== "search") return;
      const q = chip.dataset.chip ?? chip.textContent ?? "";
      qInput.value = q;
      state = setQuery(state, q);
      echoEl.textContent = q;
    });
  });

  // theme suggestion chips (curate mode) — set the theme + run.
  document.querySelectorAll<HTMLElement>("[data-theme]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (state.mode !== "curate") return;
      const t = chip.dataset.theme ?? chip.textContent ?? "";
      themeInput.value = t;
      state = setTheme(state, t);
      echoEl.textContent = t;
      void run();
    });
  });

  // strategy chips (ingest mode). The chip's `data-strategy` is the nice
  // user-facing token ("mean" / "cue-anchored"); map it to the EXACT wire
  // value the Rust bridge accepts ("mean_excerpt" / "cue_anchored").
  document.querySelectorAll<HTMLElement>("[data-strategy]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const strat: EmbedStrategy =
        chip.dataset.strategy === "mean" ? "mean_excerpt" : "cue_anchored";
      state = setStrategy(state, strat);
      document.querySelectorAll<HTMLElement>("[data-strategy]").forEach((c) => {
        const wire =
          c.dataset.strategy === "mean" ? "mean_excerpt" : "cue_anchored";
        c.setAttribute("aria-pressed", String(wire === strat));
      });
    });
  });

  document.querySelectorAll<HTMLElement>("[data-cue-export]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const format = (chip.dataset.cueExport ?? "rekordbox") as CueExportFormat;
      state = setCueExport(state, format);
      document.querySelectorAll<HTMLElement>("[data-cue-export]").forEach((c) => {
        c.setAttribute(
          "aria-pressed",
          String((c.dataset.cueExport ?? "rekordbox") === format),
        );
      });
    });
  });

  // energy-curve preset picker (build mode) — a segmented hardware selector.
  // `data-curve` IS the exact wire value the agent's CLI accepts, so no label
  // mapping is needed (unlike the strategy chips).
  document.querySelectorAll<HTMLElement>("[data-curve]").forEach((seg) => {
    seg.addEventListener("click", () => {
      const curve = (seg.dataset.curve ?? "peak_time") as EnergyCurve;
      state = setCurve(state, curve);
      syncCurvePicker();
    });
  });

  // build-set theme chips — set the brief + run (mirrors the curate chips).
  document.querySelectorAll<HTMLElement>("[data-brief]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (state.mode !== "build") return;
      const brief = chip.dataset.brief ?? chip.textContent ?? "";
      briefInput.value = brief;
      state = setBrief(state, brief);
      echoEl.textContent = brief;
      void run();
    });
  });

  document.querySelectorAll<HTMLElement>("[data-chat]").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (state.mode !== "chat") return;
      const message = chip.dataset.chat ?? chip.textContent ?? "";
      chatInput.value = message;
      state = setChatMessage(state, message);
      void run();
    });
  });

  // drop a track to seed the similar search
  void wireDropZone((path) => {
    const name = path.split(/[\\/]/).pop() ?? path;
    state = setSeed(state, name);
    seedNameEl.textContent = name;
    if (state.mode === "similar") void run();
  });

  // Live deck context from the app socket is a bounded hint for chat turns.
  // It is not rendered here; it only prevents Viber from inventing transitions
  // when the live state says one deck is resolved/audible.
  void onLiveDeckContext((context: LibraryLiveContext) => {
    latestLiveContext = mergeLiveContext(latestLiveContext, context);
    if (state.mode === "chat" && !busy) renderChatIdleSide();
  });
  void onLiveMoveContext((moves: string[]) => {
    rememberLiveMoves(moves);
    latestLiveContext = liveContextForChat(latestLiveContext);
    if (state.mode === "chat" && !busy) renderChatIdleSide();
  });

  // ingest progress from the real bridge (no-op listeners in dev)
  void onEmbedProgress((p: EmbedProgress) => {
    if (!busy || state.mode !== "ingest") return;
    appendLog(p.status, p.filename, p.cost_eur);
    setProgress(
      p.n,
      p.total,
      p.cost_eur,
      p.filename.replace(/\.[a-z0-9]+$/i, ""),
    );
  });
  void onEmbedDone((d: EmbedDone) => {
    if (!busy || state.mode !== "ingest") return;
    setProgress(d.total, d.total, d.cost_eur, "done");
    busy = false;
    runBtn.disabled = false;
    void refreshStats();
  });

  // first-run CLAP/CUE model install progress from the real bridge. The final
  // JSON still comes from libraryModels(); this only keeps the setup row alive
  // during long downloads on a clean machine.
  void onModelProgress((p: LibraryModelProgress) => {
    if (!installModelsBtn.disabled) return;
    $("vmx-lib-model-state").textContent = modelProgressStateText(p);
  });

  // The live tool tape: each tool Viber fires (search, sequence, create) streams
  // in as it happens, so a curate/build/chat run is a visible agentic process,
  // not an opaque wait. No-op listener outside Tauri (dev/jsdom).
  void onViberTool((e: LibraryViberToolEvent) => {
    if (!busy) return;
    if (
      state.mode !== "chat" &&
      state.mode !== "curate" &&
      state.mode !== "build"
    ) {
      return;
    }
    appendLiveToolRow(e);
  });

  // initial paint
  applyModeVisibility();
  syncCurvePicker();
  void refreshStats();
  void refreshModels();
  void run();
}

/** Wire the similar-mode drop zone to the Tauri webview drag-drop API. No-op
 *  outside Tauri (plain dev / jsdom). */
async function wireDropZone(onFile: (path: string) => void): Promise<void> {
  try {
    const { getCurrentWebview } = await import("@tauri-apps/api/webview");
    const webview = getCurrentWebview();
    const drop = document.querySelector<HTMLElement>(".vmx-lib-dropzone");
    const seen = new Set<number>();
    await webview.onDragDropEvent((event) => {
      const payload = event.payload as
        | { type: "enter" | "over"; paths: string[] }
        | { type: "leave" }
        | { type: "drop"; paths: string[] };
      if (payload.type === "enter" || payload.type === "over") {
        drop?.classList.add("dragging");
        return;
      }
      if (payload.type === "leave") {
        drop?.classList.remove("dragging");
        return;
      }
      if (payload.type === "drop") {
        drop?.classList.remove("dragging");
        const id = (event as unknown as { id: number }).id;
        // Tauri Issue #14134 — the same drop fires twice; dedupe by event id.
        if (typeof id === "number") {
          if (seen.has(id)) return;
          seen.add(id);
        }
        const audio = payload.paths.find((p) =>
          /\.(wav|mp3|m4a|flac)$/i.test(p),
        );
        if (audio) onFile(audio);
      }
    });
  } catch {
    // Tauri webview API unavailable — drop wiring skipped.
  }
}

// Auto-mount when loaded as the library.html entry (skipped under vitest,
// which imports the pure modules directly).
if (
  typeof document !== "undefined" &&
  document.getElementById("vmx-lib-runbtn")
) {
  mountLibrary();
}
