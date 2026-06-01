// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — typed invoke()/event client for the library surface.
 *
 * The Rust bridge agent owns the matching `#[tauri::command]` handlers and the
 * `library://embed-*` event emitters (tauri/src-tauri/**). This module is the
 * webview-side typed gateway against that exact contract:
 *
 *   invoke("library_search",  { query, k })       -> SearchResult
 *   invoke("library_similar", { seed,  k })       -> SearchResult   (same shape)
 *   invoke("library_chat", { message, history, liveContext }) -> LibraryChatResult
 *   invoke("library_build_set", { brief, curve }) -> BuildSetResult
 *   invoke("library_cue_folder", { path, exportFormat, out, name, maxCues })
 *        -> LibraryCueResult
 *   invoke("library_stats")                        -> LibraryStats
 *   invoke("library_embed_folder", { path, strategy })
 *        -> kicks off a folder embed; progress arrives as Tauri events:
 *           listen("library://embed-progress")  EmbedProgress
 *           listen("library://embed-done")      EmbedDone
 *
 * Unlike the wizard's schema-gated WS path (ipc/client.ts), the Vibe Engine
 * commands are direct Tauri commands. Rust owns the one-shot CLI subprocess
 * bridge + event stream, so there is no JSON-schema validator on this seam.
 *
 * DEV FALLBACK: when `invoke()` is genuinely UNAVAILABLE (plain `vite` dev,
 * jsdom tests — `getInvoke()` returns null), every call resolves with the real
 * sample data captured from the 2026-05-25 subset run — the same numbers baked
 * into mocks/vibemix-library-ui.html — so the window renders fully without Rust.
 *
 * CRITICAL (anti-slop): the fallback fires ONLY for the no-Tauri case. When
 * invoke IS available (real app) and the backend call THROWS — empty cache,
 * missing local model, bad strategy, agent setup — we PROPAGATE the error
 * instead of masking it with canned sample data, so the UI can show a real
 * error state. Silently returning fake 142-track data on a real failure would
 * make a broken backend look like success — exactly the AI-slop failure mode
 * this product blocks on.
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
  /** Cosine score in [0,1]. Higher = closer in the active vibe space. */
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
  embedding_backend?: string;
  embedding_dim?: number;
  clap_model_installed?: boolean;
  clap_model_path?: string;
  clap_model_missing?: string[];
  library_freshness?: {
    status?: string;
    stale?: boolean;
    reason?: string;
    age_days?: number;
    cache_path?: string;
    source_path?: string | null;
    source_age_days?: number | null;
    cache_mtime?: number | null;
    source_mtime?: number | null;
  };
  library_freshness_status?: string;
  library_stale?: boolean;
  library_staleness_reason?: string;
  library_age_days?: number;
  agent_backend?: "codex" | string;
  agent_ready?: boolean;
  agent_status?: string;
  agent_hint?: string;
  library_setup_candidates?: LibrarySetupCandidate[];
  spent_eur: number;
  failed: number;
}

export interface LibraryImportAction {
  type: "ipc.library.import";
  payload: {
    path: string;
    schema_version: "1";
  };
}

export interface LibrarySetupCandidate {
  kind: string;
  path: string;
  confidence?: string;
  reason?: string;
  command?: string;
  audio_files_seen?: number;
  import_action?: LibraryImportAction;
}

export type LibraryModelInstallTarget =
  | "required"
  | "clap"
  | "moss"
  | "cue"
  | "all";

export interface LibraryModelAsset {
  id: "clap" | "moss-tts" | "cue-detr" | string;
  label: string;
  role: string;
  required: boolean;
  env: string;
  installed: boolean;
  installable?: boolean;
  path: string;
  missing: string[];
  mismatched?: string[];
}

export interface LibraryModelInstallFile {
  rel_path: string;
  source_rel_path?: string;
  path: string;
  status: "downloaded" | "skipped" | string;
  size: number;
  sha256: string;
  url: string;
}

export interface LibraryModelInstallItem {
  id: string;
  installed: boolean;
  path: string;
  files: LibraryModelInstallFile[];
  errors: string[];
}

export interface LibraryModelInstallSummary {
  target: LibraryModelInstallTarget;
  results: LibraryModelInstallItem[];
  ok: boolean;
}

export interface LibraryModelProgress {
  target: LibraryModelInstallTarget;
  id: "clap" | "moss-tts" | "cue-detr" | string;
  n: number;
  total: number;
  status: "downloading" | "downloaded" | "verified" | "error" | string;
  rel_path: string;
  downloaded: number;
  size: number;
  error?: string;
}

export interface LibraryModelsResult {
  models: LibraryModelAsset[];
  required_ready: boolean;
  all_ready: boolean;
  install?: LibraryModelInstallSummary;
}

/** One curated track row. `meta` is a short mono caption (artist, or
 *  `track <id>` when the CLI gave only the id — never a fabricated title). */
export interface CurateTrack {
  track_id: string;
  title: string;
  meta: string;
}

/** Result of an AI-curated playlist (`library curate <theme> --json`, mapped by
 *  the Rust bridge into `{ name, rationale, stop_reason, tracks, count }`).
 *  When Viber needs disambiguation, `stop_reason` is `clarification_needed`
 *  and `question` + `choices` carry the prompt that should be shown inline. */
export interface CurateResult {
  /** Agent-chosen playlist name (falls back to the theme). */
  name: string;
  /** The agent's plain-language explanation of the set it built. */
  rationale: string;
  /** Backend stop reason, e.g. "created", "model_done", "exported", or an honest failure code. */
  stop_reason: string;
  /** Optional clarification prompt from Viber's `request_clarification` tool. */
  question?: string;
  /** Numbered choices that can be appended to the next prompt. */
  choices?: string[];
  tracks: CurateTrack[];
  count: number;
}

/** Energy-curve preset for the Viber set-prep agent (`--curve <preset>`). The EXACT
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

/** Portable cue export format for the GUI-safe folder cue bridge. The app
 *  exposes file exports only; Serato tag writes remain CLI-only because they
 *  mutate audio files and require explicit operator consent. */
export type CueExportFormat = "rekordbox" | "m3u8" | "both";

export interface LibraryCueResult {
  ok: boolean;
  mode: "export" | string;
  tracks_cued: number;
  cues_total: number;
  skipped: number;
  outputs: Partial<Record<"rekordbox" | "m3u8", string>>;
}

/** One previous Viber chat turn, oldest first. */
export interface LibraryChatTurn {
  role: "you" | "viber";
  text: string;
}

export interface LibraryLiveDeck {
  title?: string | null;
  track_id?: string | null;
  camelot?: string | null;
  key?: string | null;
  bpm?: number | null;
  confidence?: number | null;
  source?: string | null;
}

export interface LibraryLiveDeckControls {
  vol?: number;
  eq_low?: number;
  eq_mid?: number;
  eq_hi?: number;
  filter?: number;
  play?: boolean;
}

export interface LibraryLiveDeckMixer {
  connected?: boolean;
  xfader?: number;
  deck_confidence?: number;
  A?: LibraryLiveDeckControls;
  B?: LibraryLiveDeckControls;
}

export interface LibraryLiveMidiEvidence {
  key: string;
  t: number;
}

export interface LibraryLiveEvidence {
  mix?: string[];
  midi?: LibraryLiveMidiEvidence[];
  refs?: string[];
}

export interface LibraryAudioWindowAnchor {
  label: string;
  token: string;
  age_s: number | null;
  relation: string;
}

export type LibraryAudioWindowDeckAudio = "not_attached" | `P${number}`;

export interface LibraryAudioWindowMap {
  p1: "master_global_mix";
  p1_heard: true;
  timeline: "past_action_future";
  together_audio: "P1_global_mix";
  decks_together: true;
  deckA_audio: LibraryAudioWindowDeckAudio;
  deckB_audio: LibraryAudioWindowDeckAudio;
  per_deck_audio: "structured_text_only" | "deck_pair_parts";
  duplicate_audio:
    | "same_master_not_deck_split"
    | "separate_deck_pair_parts";
  deck_audio_separation?: "not_attached" | "deck_audio_separation_context";
  deck_part_span_s?: [number, number];
  deck_part_activity?: Partial<Record<"A" | "B", "active" | "silent">>;
  deck_separation: "deck_lanes_context";
  lane_aliases: "deck1:A,deck2:B";
  pre_s: [number, number];
  current_s: [number, number];
  action_s: [number, number];
  move_anchors: LibraryAudioWindowAnchor[];
  future: Record<string, unknown>;
  rule: "time_alignment_not_outcome_verdict";
}

export interface LibraryLiveContext {
  live_context_schema_version?: number;
  live_context_capabilities?: string[];
  deck?: string;
  audible?: boolean;
  phase?: string;
  bpm?: number | null;
  music?: number | null;
  deck_state?: Record<string, LibraryLiveDeck>;
  deck_mixer?: LibraryLiveDeckMixer;
  deck_source_status?: Record<string, string>;
  deck_lanes_context?: string;
  deck_reference_context?: string;
  deck_source_context?: string;
  deck_audio_context?: string;
  deck_audio_separation_context?: string;
  deck_audio_features_context?: string;
  deck_audio_delta_context?: string;
  deck_audio_window_context?: string;
  audio_part_context?: string;
  audio_window_context?: string;
  audio_window_map?: LibraryAudioWindowMap;
  audio_delta?: string[];
  live_evidence?: LibraryLiveEvidence;
  recent_moves?: string[];
}

/** One grounded tool call shown by the chat surface. */
export interface LibraryChatToolTrace {
  name: string;
  arg: string;
  ok: boolean;
}

export interface LibraryChatPlaylist {
  name: string;
  track_ids: string[];
  m3u_path: string;
  json_path: string;
  dropped_ids: string[];
}

export type LibraryMoveGradeSlug =
  | "negative"
  | "mid"
  | "clean"
  | "sexy"
  | "bomb"
  | "lit_aff";

export interface LibraryChatMoveGrade {
  candidate_id: string;
  track_id: string;
  title: string;
  slug: LibraryMoveGradeSlug;
  label: string;
  xp: number;
  reason: string;
  overdrive: boolean;
  streak?: number;
  total_xp?: number;
  level?: number;
  level_xp?: number;
  next_level_xp?: number;
  level_up?: boolean;
  levels_gained?: number;
}

export interface LibraryLiveVerification {
  ok: boolean;
  violations: string[];
  reply: string;
  corrected: boolean;
  corrected_reply: string | null;
  claim_policy: string;
  transport_status: string;
  move_grades_allowed: boolean;
  move_grades_seen: number;
  guard_applied?: boolean;
  guard_violations?: string[];
}

/** Result of one conversational Viber turn (`library chat ... --json`). */
export interface LibraryChatResult {
  reply: string;
  tool_trace: LibraryChatToolTrace[];
  playlist: LibraryChatPlaylist | null;
  export_path: string | null;
  seen_track_ids: string[];
  move_grades: LibraryChatMoveGrade[];
  live_verification?: LibraryLiveVerification;
  iterations: number;
  stop_reason: string;
  /** Optional clarification prompt from Viber's `request_clarification` tool. */
  question?: string;
  /** Numbered choices that can be appended to the next chat message. */
  choices?: string[];
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

// ── Runtime response guards ────────────────────────────────────────────────

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label}: malformed response`);
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${label}: expected array`);
  return value;
}

function asString(value: unknown, label: string): string {
  if (typeof value !== "string") throw new Error(`${label}: expected string`);
  return value;
}

function asBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${label}: expected boolean`);
  return value;
}

function asFiniteNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${label}: expected finite number`);
  }
  return value;
}

function asNullableString(value: unknown, label: string): string | null {
  if (value == null) return null;
  return asString(value, label);
}

function asStringArray(value: unknown, label: string): string[] {
  return asArray(value, label).map((item, index) =>
    asString(item, `${label}[${index}]`),
  );
}

function optionalString(
  record: Record<string, unknown>,
  key: string,
): string | undefined {
  const value = record[key];
  if (value === undefined || value === null) return undefined;
  return asString(value, key);
}

function optionalBoolean(
  record: Record<string, unknown>,
  key: string,
): boolean | undefined {
  const value = record[key];
  if (value === undefined || value === null) return undefined;
  return asBoolean(value, key);
}

function optionalNumber(
  record: Record<string, unknown>,
  key: string,
): number | undefined {
  const value = record[key];
  if (value === undefined || value === null) return undefined;
  return asFiniteNumber(value, key);
}

function optionalRecordBoolean(
  record: Record<string, unknown>,
  key: string,
  label: string,
): boolean | undefined {
  const value = record[key];
  if (value === undefined || value === null) return undefined;
  return asBoolean(value, label);
}

function optionalRecordNumber(
  record: Record<string, unknown>,
  key: string,
  label: string,
): number | undefined {
  const value = record[key];
  if (value === undefined || value === null) return undefined;
  return asFiniteNumber(value, label);
}

function stringOrNull(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim().replace(/\s+/g, " ");
  return text ? text : null;
}

function finiteOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

const LIVE_DECK_SOURCES = new Set([
  "rekordbox_xml",
  "folder_cache",
  "screen_vision",
  "numpy_key",
  "nowplaying",
  "live_context",
  "unknown",
]);

function normalizeLiveDeck(value: unknown): LibraryLiveDeck | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const deck: LibraryLiveDeck = {};
  const title = stringOrNull(row.title);
  const trackId = stringOrNull(row.track_id);
  const camelot = stringOrNull(row.camelot);
  const key = stringOrNull(row.key);
  const bpm = finiteOrNull(row.bpm);
  const confidence = finiteOrNull(row.confidence);
  const source = stringOrNull(row.source);
  if (title) deck.title = title;
  if (trackId) deck.track_id = trackId;
  if (camelot) deck.camelot = camelot;
  if (key) deck.key = key;
  if (bpm !== null && bpm > 0) deck.bpm = bpm;
  if (confidence !== null)
    deck.confidence = Math.max(0, Math.min(1, confidence));
  if (Object.keys(deck).length > 0 && source && LIVE_DECK_SOURCES.has(source))
    deck.source = source;
  return Object.keys(deck).length > 0 ? deck : null;
}

function int0To127OrNull(value: unknown): number | null {
  const raw = finiteOrNull(value);
  if (raw === null) return null;
  return Math.max(0, Math.min(127, Math.trunc(raw)));
}

function normalizeLiveDeckControls(
  value: unknown,
): LibraryLiveDeckControls | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const controls: LibraryLiveDeckControls = {};
  for (const key of ["vol", "eq_low", "eq_mid", "eq_hi", "filter"] as const) {
    const next = int0To127OrNull(row[key]);
    if (next !== null) controls[key] = next;
  }
  if (typeof row.play === "boolean") controls.play = row.play;
  return Object.keys(controls).length > 0 ? controls : null;
}

function normalizeLiveDeckMixer(value: unknown): LibraryLiveDeckMixer | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const mixer: LibraryLiveDeckMixer = {};
  if (typeof row.connected === "boolean") mixer.connected = row.connected;
  const xfader = int0To127OrNull(row.xfader);
  if (xfader !== null) mixer.xfader = xfader;
  const deckConfidence = finiteOrNull(row.deck_confidence);
  if (deckConfidence !== null) {
    mixer.deck_confidence = Math.max(0, Math.min(1, deckConfidence));
  }
  const deckA = normalizeLiveDeckControls(row.A);
  if (deckA) mixer.A = deckA;
  const deckB = normalizeLiveDeckControls(row.B);
  if (deckB) mixer.B = deckB;
  return Object.keys(mixer).length > 0 ? mixer : null;
}

const LIVE_EVIDENCE_TOKEN_RE = /^[A-Za-z0-9_:.=@+-]{1,128}$/;
const LIVE_EVIDENCE_CAP = 10;
const LIVE_EVIDENCE_REFS_CAP = 14;

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

function boundedLiveEvidenceList(value: unknown, cap: number): string[] {
  if (!Array.isArray(value)) return [];
  const out: Array<{ priority: number; index: number; token: string }> = [];
  const seen = new Set<string>();
  let index = 0;
  for (const item of value) {
    const text = stringOrNull(item)?.slice(0, 128);
    if (!text || !LIVE_EVIDENCE_TOKEN_RE.test(text) || seen.has(text)) continue;
    out.push({ priority: liveEvidencePriority(text), index, token: text });
    seen.add(text);
    index += 1;
  }
  if (out.length <= cap) return out.map((item) => item.token);
  return [...out]
    .sort((a, b) => a.priority - b.priority || a.index - b.index)
    .slice(0, cap)
    .sort((a, b) => a.index - b.index)
    .map((item) => item.token);
}

function normalizeLiveEvidence(value: unknown): LibraryLiveEvidence | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const evidence: LibraryLiveEvidence = {};

  const mix = boundedLiveEvidenceList(row.mix, LIVE_EVIDENCE_CAP);
  if (mix.length > 0) evidence.mix = mix;

  const midi: LibraryLiveMidiEvidence[] = [];
  if (Array.isArray(row.midi)) {
    for (const item of row.midi.slice(-4)) {
      if (item == null || typeof item !== "object" || Array.isArray(item))
        continue;
      const midiRow = item as Record<string, unknown>;
      const key = stringOrNull(midiRow.key)?.slice(0, 96);
      const t = finiteOrNull(midiRow.t);
      if (!key || !LIVE_EVIDENCE_TOKEN_RE.test(key) || t === null) continue;
      midi.push({ key, t: Math.max(0, Math.round(t * 10) / 10) });
    }
  }
  if (midi.length > 0) evidence.midi = midi;

  const refs = boundedLiveEvidenceList(
    [
      ...(Array.isArray(row.refs) ? row.refs : []),
      ...midi.map((item) => `midi:${item.key}@${item.t.toFixed(1)}`),
      ...mix.map((item) => `mix:${item}`),
    ],
    LIVE_EVIDENCE_REFS_CAP,
  );
  if (refs.length > 0) evidence.refs = refs;

  return Object.keys(evidence).length > 0 ? evidence : null;
}

function evidenceToken(text: string): string {
  return text
    .replace(/→/g, "_to_")
    .replace(/%/g, "pct")
    .replace(/[^A-Za-z0-9_.:+-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 96);
}

function isResolvedLiveDeck(deck?: LibraryLiveDeck): boolean {
  if (!deck) return false;
  return (
    (deck.confidence ?? 0) >= 0.3 &&
    Boolean(deck.title || deck.track_id || deck.camelot)
  );
}

function routeTier(score: number): string {
  if (score <= 0.04) return "muted";
  if (score < 0.2) return "low";
  if (score < 0.45) return "present";
  return "dominant";
}

function xfaderFactor(side: "A" | "B", xfader: number): number {
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

function liveRouteScores(context: LibraryLiveContext): Array<[string, number]> {
  const mixer = context.deck_mixer;
  if (!mixer?.connected) return [];
  const xfader = Math.max(0, Math.min(127, Math.round(mixer.xfader ?? 64)));
  return (["A", "B"] as const).map((side) => {
    const row = mixer[side];
    if (!row) return [side, 0];
    const volume = Math.max(0, Math.min(127, Math.round(row.vol ?? 0))) / 127;
    let score = volume * xfaderFactor(side, xfader);
    if (volume < 0.1) score = 0;
    return [side, Math.max(0, Math.min(1, score))];
  });
}

function routeSupport(scores: Array<[string, number]>): string {
  const lookup = new Map(scores);
  const aScore = lookup.get("A") ?? 0;
  const bScore = lookup.get("B") ?? 0;
  if (aScore <= 0.04 && bScore <= 0.04) return "no_deck_route";
  if (aScore > 0.2 && bScore > 0.2) return "two_deck_route";
  return aScore >= bScore ? "single_deck_A" : "single_deck_B";
}

function transitionStatus(
  context: LibraryLiveContext,
  resolvedSides: string[],
  scores: Array<[string, number]>,
): string {
  if (resolvedSides.length === 0) return "transition_block=no_resolved_decks";
  if (resolvedSides.length === 1)
    return "transition_block=single_resolved_deck";
  const lookup = new Map(scores);
  const hasTwoDeckRoute =
    (lookup.get("A") ?? 0) > 0.2 && (lookup.get("B") ?? 0) > 0.2;
  if (context.deck === "mix" || hasTwoDeckRoute)
    return "transition_candidate=two_resolved_decks_mixing";
  if (context.deck === "A" || context.deck === "B")
    return `transition_watch=two_resolved_decks_single_audible_${context.deck}`;
  return "transition_watch=two_resolved_decks_audible_unknown";
}

function deckIdentityStatus(resolvedSides: string[]): string {
  if (resolvedSides.length === 0) return "second_deck_identity=blocked";
  if (resolvedSides.length === 1)
    return "second_deck_identity=unknown_or_suppressed";
  return "second_deck_identity=observed";
}

function deriveLiveEvidence(
  context: LibraryLiveContext,
): LibraryLiveEvidence | null {
  const deckState = context.deck_state ?? {};
  const hasDeckStatePayload = context.deck_state !== undefined;
  const deckSides = ["A", "B", "C", "D"] as const;
  const resolvedSides = deckSides.filter((side) =>
    isResolvedLiveDeck(deckState[side]),
  );
  const scores = liveRouteScores(context);
  const scoreMap = new Map(scores);
  const hasIdentityReference =
    Object.keys(deckState).length > 0 ||
    (hasDeckStatePayload && context.deck_mixer?.connected === true);
  const mix: string[] = [];

  if (scores.length > 0) {
    mix.push(`deck_audio_support=${routeSupport(scores)}`);
  }
  if (hasIdentityReference) {
    mix.push(transitionStatus(context, resolvedSides, scores));
    mix.push(deckIdentityStatus(resolvedSides));
  }

  const sideSet = new Set<string>();
  if (
    hasDeckStatePayload &&
    (context.deck_mixer?.connected || deckState.A || deckState.B)
  ) {
    sideSet.add("A");
    sideSet.add("B");
  }
  for (const side of deckSides) {
    if (deckState[side]) sideSet.add(side);
  }
  const sides = [...sideSet].sort();
  if (sides.length > 0) {
    const lanes = sides.map((side) => {
      const ident = isResolvedLiveDeck(deckState[side])
        ? "known"
        : deckState[side]
          ? "unresolved"
          : "unknown";
      const route = scoreMap.has(side)
        ? routeTier(scoreMap.get(side) ?? 0)
        : "unknown";
      return `${side}_${ident}_route_${route}`;
    });
    mix.push(`deck_lanes=${lanes.join("+")}`);
  }

  if (hasIdentityReference) {
    const references = (["A", "B"] as const).map((side, index) => {
      const ident = isResolvedLiveDeck(deckState[side])
        ? "known"
        : deckState[side]
          ? "unresolved"
          : "unknown";
      const route = scoreMap.has(side)
        ? routeTier(scoreMap.get(side) ?? 0)
        : "unknown";
      return `deck${index + 1}_${side}_${ident}_route_${route}`;
    });
    mix.push(`deck_reference=${references.join("+")}`);

    const sources = (["A", "B"] as const).map((side, index) => {
      const deck = deckState[side];
      const ident = isResolvedLiveDeck(deck)
        ? "known"
        : deck
          ? "unresolved"
          : "unknown";
      const source = deck ? deck.source || "unknown" : "none";
      return `deck${index + 1}_${side}_${ident}_src_${
        evidenceToken(source) || "unknown"
      }`;
    });
    mix.push(`deck_source=${sources.join("+")}`);
  }

  if (scores.length > 0) {
    mix.push(
      `deck_route=${scores
        .map(([side, score]) => `${side}_${routeTier(score)}`)
        .join("+")}`,
    );
  }
  const boundedMix = boundedLiveEvidenceList(mix, LIVE_EVIDENCE_CAP);
  if (boundedMix.length === 0) return null;
  return {
    mix: boundedMix,
    refs: boundedLiveEvidenceList(
      boundedMix.map((item) => `mix:${item}`),
      LIVE_EVIDENCE_REFS_CAP,
    ),
  };
}

function mergeLiveEvidencePayload(
  existing?: LibraryLiveEvidence,
  incoming?: LibraryLiveEvidence | null,
): LibraryLiveEvidence | null {
  const mix = boundedLiveEvidenceList(
    [...(existing?.mix ?? []), ...(incoming?.mix ?? [])],
    LIVE_EVIDENCE_CAP,
  );
  const midi: LibraryLiveMidiEvidence[] = [];
  const seenMidi = new Set<string>();
  for (const item of [...(existing?.midi ?? []), ...(incoming?.midi ?? [])]) {
    const ident = `${item.key}@${item.t.toFixed(1)}`;
    if (seenMidi.has(ident)) continue;
    seenMidi.add(ident);
    midi.push(item);
  }
  const boundedMidi = midi.slice(-4);
  const refs = boundedLiveEvidenceList(
    [
      ...(existing?.refs ?? []),
      ...(incoming?.refs ?? []),
      ...boundedMidi.map((item) => `midi:${item.key}@${item.t.toFixed(1)}`),
      ...mix.map((item) => `mix:${item}`),
    ],
    LIVE_EVIDENCE_REFS_CAP,
  );
  const out: LibraryLiveEvidence = {};
  if (mix.length > 0) out.mix = mix;
  if (boundedMidi.length > 0) out.midi = boundedMidi;
  if (refs.length > 0) out.refs = refs;
  return Object.keys(out).length > 0 ? out : null;
}

function normalizeAudioWindowContext(value: unknown): string | null {
  const text = stringOrNull(value)?.slice(0, 900);
  if (!text?.startsWith("audio_window_context[")) return null;
  const required = [
    "P1=master_global_mix",
    "P1_heard=true",
    "timeline=past_action_future",
    "deck_separation=deck_lanes_context",
    "lane_aliases=deck1:A,deck2:B",
    "action=-1.0..0.0",
    "rule=time_alignment_not_outcome_verdict",
  ];
  if (!required.every((atom) => text.includes(atom))) return null;
  const globalOnly = [
    "deckA_audio=not_attached",
    "deckB_audio=not_attached",
    "per_deck_audio=structured_text_only",
    "duplicate_audio=same_master_not_deck_split",
  ].every((atom) => text.includes(atom));
  const deckPairParts =
    text.includes("per_deck_audio=deck_pair_parts") &&
    text.includes("duplicate_audio=separate_deck_pair_parts") &&
    text.includes("deck_audio_separation=deck_audio_separation_context") &&
    /\bdeckA_audio=P[2-9][0-9]?\b/.test(text) &&
    /\bdeckB_audio=P[2-9][0-9]?\b/.test(text) &&
    audioWindowDeckLabelsAreDistinct(text);
  if (!globalOnly && !deckPairParts) return null;
  const forbidden = [
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
  ];
  if (forbidden.some((atom) => text.includes(atom))) return null;
  return text;
}

function audioWindowDeckLabelsAreDistinct(text: string): boolean {
  const deckA = /\bdeckA_audio=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  const deckB = /\bdeckB_audio=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  return Boolean(deckA && deckB && deckA !== deckB);
}

type DeckAudioPartLabels = Readonly<{ A: string; B: string }>;

function audioPartDeckLabelsForContext(
  text: string | null,
): DeckAudioPartLabels | null {
  if (!text?.includes("per_deck_audio=deck_pair_parts")) return null;
  const deckA = /\bdeckA_part=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  const deckB = /\bdeckB_part=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  if (!deckA || !deckB || deckA === deckB) return null;
  return { A: deckA, B: deckB };
}

function audioWindowDeckLabelsForContext(
  text: string | null,
): DeckAudioPartLabels | null {
  if (!text?.includes("per_deck_audio=deck_pair_parts")) return null;
  const deckA = /\bdeckA_audio=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  const deckB = /\bdeckB_audio=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  if (!deckA || !deckB || deckA === deckB) return null;
  return { A: deckA, B: deckB };
}

function audioWindowMatchesAudioPartLabels(
  audioWindowContext: string | null,
  partLabels: DeckAudioPartLabels | null,
): boolean {
  const windowLabels = audioWindowDeckLabelsForContext(audioWindowContext);
  if (!partLabels) return windowLabels === null;
  return (
    windowLabels !== null &&
    windowLabels.A === partLabels.A &&
    windowLabels.B === partLabels.B
  );
}

function normalizeAudioPartContext(value: unknown): string | null {
  const text = stringOrNull(value)?.slice(0, 1400);
  if (!text?.startsWith("audio_part_context[")) return null;
  const required = [
    "P1=live_global_mix",
    "P1_runtime_observed=true",
    "P1_audience_heard=true",
    "P1_deck_audio=global_mix_not_stems",
    "deck1=A",
    "deck2=B",
    "together_audio=P1",
    "rule=part_labels_not_outcome_verdict",
  ];
  if (!required.every((atom) => text.includes(atom))) return null;
  const globalOnly = [
    "per_deck_audio=not_attached",
    "duplicate_audio=same_master_not_deck_split",
  ].every((atom) => text.includes(atom));
  const deckPairParts = [
    "per_deck_audio=deck_pair_parts",
    "duplicate_audio=separate_deck_pair_parts",
  ].every((atom) => text.includes(atom));
  if (!globalOnly && !deckPairParts) return null;
  if (globalOnly && /\bdeck[AB]_part=P[2-9][0-9]?\b/.test(text)) return null;
  if (deckPairParts && !audioPartDeckPairMapIsValid(text)) return null;
  const forbidden = [
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "isolated_decks=true",
    "P1_deck_audio=stems",
    "deck_audio=stems",
  ];
  if (forbidden.some((atom) => text.includes(atom))) return null;
  return text;
}

function audioPartDeckPairMapIsValid(text: string): boolean {
  const deckA = /\bdeckA_part=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  const deckB = /\bdeckB_part=(P[2-9][0-9]?)\b/.exec(text)?.[1] ?? null;
  if (!deckA || !deckB || deckA === deckB) return false;

  const orderMatch = /\bpart_order=(P1(?:,P[2-9][0-9]?)*)\b/.exec(text);
  if (!orderMatch) return false;
  const orderText = orderMatch[1];
  if (!orderText) return false;
  const partOrder = orderText.split(",");
  const ordered = [...partOrder].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
  if (
    partOrder[0] !== "P1" ||
    new Set(partOrder).size !== partOrder.length ||
    partOrder.join(",") !== ordered.join(",") ||
    !partOrder.includes(deckA) ||
    !partOrder.includes(deckB)
  ) {
    return false;
  }

  return (
    audioPartDeckLabelIsValid(text, "A", deckA) &&
    audioPartDeckLabelIsValid(text, "B", deckB)
  );
}

function audioPartDeckLabelIsValid(
  text: string,
  side: "A" | "B",
  label: string,
): boolean {
  const expectedRole = `deck${side}_configured_capture`;
  const atoms = [
    `deck${side}_part=${label}`,
    `${label}=${expectedRole}`,
    `${label}_model_heard=true`,
    `${label}_audience_heard=false`,
    `${label}_deck_audio=${expectedRole}`,
    `${label}_rule=deck_pair_capture_reference_not_quality_verdict`,
  ];
  if (!atoms.every((atom) => audioPartHasAtom(text, atom))) return false;
  const roles = new Set(
    [...text.matchAll(new RegExp(`\\b${label}=([A-Za-z0-9_]+)\\b`, "g"))]
      .map((match) => match[1])
      .filter((role): role is string => typeof role === "string"),
  );
  return roles.size === 1 && roles.has(expectedRole);
}

function audioPartHasAtom(text: string, atom: string): boolean {
  return ` ${text.replaceAll("[", " ").replaceAll("]", " ")} `.includes(
    ` ${atom} `,
  );
}

function normalizeSpanPair(value: unknown): [number, number] | null {
  if (!Array.isArray(value) || value.length < 2) return null;
  const a = finiteOrNull(value[0]);
  const b = finiteOrNull(value[1]);
  if (a === null || b === null) return null;
  return [Math.round(a * 10) / 10, Math.round(b * 10) / 10];
}

function normalizeAudioPartLabel(
  value: unknown,
): LibraryAudioWindowDeckAudio | null {
  const label = stringOrNull(value)?.toUpperCase();
  if (!label) return null;
  if (!/^P[2-9][0-9]?$/.test(label)) return null;
  return label as LibraryAudioWindowDeckAudio;
}

function normalizeAudioWindowActivity(
  value: unknown,
): Partial<Record<"A" | "B", "active" | "silent">> | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const out: Partial<Record<"A" | "B", "active" | "silent">> = {};
  for (const side of ["A", "B"] as const) {
    const activity = stringOrNull(row[side])?.toLowerCase();
    if (activity === "active" || activity === "silent") out[side] = activity;
  }
  return Object.keys(out).length > 0 ? out : null;
}

function normalizeAudioWindowMap(value: unknown): LibraryAudioWindowMap | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  if (
    row.p1 !== "master_global_mix" ||
    row.p1_heard !== true ||
    row.timeline !== "past_action_future" ||
    row.together_audio !== "P1_global_mix" ||
    row.decks_together !== true ||
    row.deck_separation !== "deck_lanes_context" ||
    row.lane_aliases !== "deck1:A,deck2:B" ||
    row.rule !== "time_alignment_not_outcome_verdict"
  ) {
    return null;
  }
  let deckAAudio: LibraryAudioWindowDeckAudio;
  let deckBAudio: LibraryAudioWindowDeckAudio;
  let perDeckAudio: "structured_text_only" | "deck_pair_parts";
  let duplicateAudio:
    | "same_master_not_deck_split"
    | "separate_deck_pair_parts";
  let deckAudioSeparation:
    | "not_attached"
    | "deck_audio_separation_context"
    | undefined;
  let deckPartSpan = normalizeSpanPair(row.deck_part_span_s);
  let deckPartActivity = normalizeAudioWindowActivity(
    row.deck_part_activity,
  );
  if (
    row.deckA_audio === "not_attached" &&
    row.deckB_audio === "not_attached" &&
    row.per_deck_audio === "structured_text_only" &&
    row.duplicate_audio === "same_master_not_deck_split" &&
    (row.deck_audio_separation === undefined ||
      row.deck_audio_separation === "not_attached")
  ) {
    deckAAudio = "not_attached";
    deckBAudio = "not_attached";
    perDeckAudio = "structured_text_only";
    duplicateAudio = "same_master_not_deck_split";
    deckAudioSeparation =
      row.deck_audio_separation === "not_attached" ? "not_attached" : undefined;
    deckPartSpan = null;
    deckPartActivity = null;
  } else {
    const deckALabel = normalizeAudioPartLabel(row.deckA_audio);
    const deckBLabel = normalizeAudioPartLabel(row.deckB_audio);
    if (
      !deckALabel ||
      !deckBLabel ||
      deckALabel === deckBLabel ||
      row.per_deck_audio !== "deck_pair_parts" ||
      row.duplicate_audio !== "separate_deck_pair_parts" ||
      row.deck_audio_separation !== "deck_audio_separation_context"
    ) {
      return null;
    }
    deckAAudio = deckALabel;
    deckBAudio = deckBLabel;
    perDeckAudio = "deck_pair_parts";
    duplicateAudio = "separate_deck_pair_parts";
    deckAudioSeparation = "deck_audio_separation_context";
  }
  const pre = normalizeSpanPair(row.pre_s);
  const current = normalizeSpanPair(row.current_s);
  const action = normalizeSpanPair(row.action_s);
  if (!pre || !current || !action) return null;

  const anchors: LibraryAudioWindowAnchor[] = [];
  if (Array.isArray(row.move_anchors)) {
    for (const item of row.move_anchors.slice(-3)) {
      if (item == null || typeof item !== "object" || Array.isArray(item))
        continue;
      const anchor = item as Record<string, unknown>;
      const token = normalizeSourceStatusToken(anchor.token);
      const label = stringOrNull(anchor.label)?.slice(0, 72);
      const relation = normalizeSourceStatusToken(anchor.relation);
      if (!token || !label || !relation) continue;
      anchors.push({
        label,
        token,
        age_s: finiteOrNull(anchor.age_s),
        relation,
      });
    }
  }
  const future =
    row.future != null &&
    typeof row.future === "object" &&
    !Array.isArray(row.future)
      ? (row.future as Record<string, unknown>)
      : {};
  if (future.heard !== false) return null;
  const futureOut: Record<string, unknown> = { heard: false };
  for (const key of ["span", "part", "source", "span_s", "rule"]) {
    if (future[key] !== undefined) futureOut[key] = future[key];
  }

  const out: LibraryAudioWindowMap = {
    p1: "master_global_mix",
    p1_heard: true,
    timeline: "past_action_future",
    together_audio: "P1_global_mix",
    decks_together: true,
    deckA_audio: deckAAudio,
    deckB_audio: deckBAudio,
    per_deck_audio: perDeckAudio,
    duplicate_audio: duplicateAudio,
    deck_separation: "deck_lanes_context",
    lane_aliases: "deck1:A,deck2:B",
    pre_s: pre,
    current_s: current,
    action_s: action,
    move_anchors: anchors,
    future: futureOut,
    rule: "time_alignment_not_outcome_verdict",
  };
  if (deckAudioSeparation) out.deck_audio_separation = deckAudioSeparation;
  if (deckPartSpan) out.deck_part_span_s = deckPartSpan;
  if (deckPartActivity) out.deck_part_activity = deckPartActivity;
  return out;
}

function audioWindowMapDeckLabels(
  audioWindowMap: LibraryAudioWindowMap | null,
): DeckAudioPartLabels | null {
  if (!audioWindowMap || audioWindowMap.per_deck_audio !== "deck_pair_parts")
    return null;
  const deckA =
    typeof audioWindowMap.deckA_audio === "string" &&
    /^P[2-9][0-9]?$/.test(audioWindowMap.deckA_audio)
      ? audioWindowMap.deckA_audio
      : null;
  const deckB =
    typeof audioWindowMap.deckB_audio === "string" &&
    /^P[2-9][0-9]?$/.test(audioWindowMap.deckB_audio)
      ? audioWindowMap.deckB_audio
      : null;
  if (!deckA || !deckB || deckA === deckB) return null;
  return { A: deckA, B: deckB };
}

function audioWindowMapMatchesAudioPartLabels(
  audioWindowMap: LibraryAudioWindowMap | null,
  partLabels: DeckAudioPartLabels | null,
): boolean {
  const mapLabels = audioWindowMapDeckLabels(audioWindowMap);
  if (!partLabels) return mapLabels === null;
  return (
    mapLabels !== null &&
    mapLabels.A === partLabels.A &&
    mapLabels.B === partLabels.B
  );
}

function normalizeLiveContextString(
  value: unknown,
  prefix: string,
  requiredAtoms: string[],
  forbiddenAtoms: string[] = [],
  maxLen = 900,
): string | null {
  const text = stringOrNull(value)?.slice(0, maxLen);
  if (!text?.startsWith(`${prefix}[`)) return null;
  if (!requiredAtoms.every((atom) => text.includes(atom))) return null;
  if (forbiddenAtoms.some((atom) => text.includes(atom))) return null;
  return text;
}

function normalizeDeckLanesContext(value: unknown): string | null {
  return normalizeLiveContextString(
    value,
    "deck_lanes_context",
    [
      "lane_aliases=deck1:A,deck2:B",
      "rule=per_lane_identity_route_control_not_outcome",
    ],
    ["isolated_decks=true", "per_deck_audio=attached"],
  );
}

function normalizeDeckReferenceContext(value: unknown): string | null {
  return normalizeLiveContextString(
    value,
    "deck_reference_context",
    [
      "deck1=A",
      "deck2=B",
      "audio=P1_global_mix",
      "per_deck_audio=not_attached",
      "isolated_decks=false",
      "rule=deck1_deck2_reference_not_outcome",
    ],
    [
      "isolated_decks=true",
      "per_deck_audio=attached",
      "deckA_audio=attached",
      "deckB_audio=attached",
      "deckA_audio=stem",
      "deckB_audio=stem",
    ],
  );
}

function normalizeDeckSourceContext(value: unknown): string | null {
  return normalizeLiveContextString(
    value,
    "deck_source_context",
    [
      "identity_state=MusicState.deck_state",
      "second_deck=independent_source_required",
      "rule=unresolved_deck_is_not_transition_evidence",
    ],
    [
      "live_db=read",
      "second_deck=inferred",
      "unresolved_deck_is_transition_evidence",
    ],
  );
}

function normalizeDeckAudioContext(value: unknown): string | null {
  return normalizeLiveContextString(
    value,
    "deck_audio_context",
    [
      "source=global_mix",
      "isolated_decks=false",
      "rule=audio_heard_must_be_mapped_through_deck_context",
    ],
    [
      "isolated_decks=true",
      "source=deckA",
      "source=deckB",
      "per_deck_audio=attached",
      "deckA_audio=attached",
      "deckB_audio=attached",
      "deckA_audio=stem",
      "deckB_audio=stem",
    ],
  );
}

function normalizeDeckAudioSeparationContext(value: unknown): string | null {
  const text = normalizeLiveContextString(
    value,
    "deck_audio_separation_context",
    ["rule=separation_capability_not_outcome"],
    [
      "isolated_decks=true",
      "per_deck_audio=attached",
      "deckA_audio=attached",
      "deckB_audio=attached",
      "deckA_audio=stem",
      "deckB_audio=stem",
    ],
  );
  if (!text) return null;
  const globalOnly = [
    "deckA_audio=not_captured",
    "deckB_audio=not_captured",
    "current_capture=P1_global_mix",
    "per_deck_audio=not_attached",
    "isolated_decks=false",
  ].every((atom) => text.includes(atom));
  const deckPairs = [
    "deckA_audio=captured",
    "deckB_audio=captured",
    "current_capture=P1_global_mix_plus_deck_pairs",
    "per_deck_audio=captured_not_attached",
    "isolated_decks=runtime_capture_available",
  ].every((atom) => text.includes(atom));
  return globalOnly || deckPairs ? text : null;
}

function normalizeDeckAudioFeaturesContext(value: unknown): string | null {
  const text = normalizeLiveContextString(
    value,
    "deck_audio_features_context",
    [
      "source=deck_pair_capture",
      "per_deck_audio=captured_features",
      "rule=deck_audio_features_not_outcome_verdict",
    ],
    [
      "transition_verdict=",
      "quality_verdict=",
      "great_transition",
      "clean_transition",
    ],
  );
  if (!text) return null;
  return /[AB]_activity=/.test(text) && /[AB]_rms=/.test(text) ? text : null;
}

function normalizeDeckAudioDeltaContext(value: unknown): string | null {
  const text = normalizeLiveContextString(
    value,
    "deck_audio_delta_context",
    [
      "source=deck_pair_capture",
      "per_deck_delta=captured_feature_delta",
      "rule=deck_audio_delta_not_causal_proof",
    ],
    [
      "transition_verdict=",
      "quality_verdict=",
      "caused_by_move=true",
      "great_transition",
      "clean_transition",
    ],
  );
  if (!text) return null;
  return /[AB]_delta=/.test(text) ? text : null;
}

function normalizeDeckAudioWindowContext(value: unknown): string | null {
  const text = normalizeLiveContextString(
    value,
    "deck_audio_window_context",
    [
      "source=deck_pair_capture",
      "timeline=pre_action_current",
      "per_deck_audio=captured_window_features",
      "rule=deck_audio_window_not_causal_or_quality_verdict",
    ],
    [
      "transition_verdict=",
      "quality_verdict=",
      "caused_by_move=true",
      "great_transition",
      "clean_transition",
    ],
    1100,
  );
  if (!text) return null;
  return /[AB]_current=/.test(text) ? text : null;
}

const LIVE_SOURCE_STATUS_KEYS = [
  "controller",
  "controller_connection",
  "library",
  "library_tracks",
  "library_source",
  "library_match",
  "nowplaying",
  "nowplaying_owner",
  "nowplaying_title",
  "audible_deck",
  "resolution",
  "resolved_side",
  "second_deck_source",
  "screen_vision",
  "last_known_sides",
  "last_known_rule",
] as const;

function normalizeLiveContextCapabilities(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const item of value) {
    const token = stringOrNull(item)?.slice(0, 48).trim();
    if (!token || !/^[A-Za-z0-9_]+$/.test(token) || seen.has(token)) continue;
    seen.add(token);
    out.push(token);
    if (out.length >= 16) break;
  }
  return out;
}

function normalizeSourceStatusToken(value: unknown): string | null {
  const text = stringOrNull(value)?.slice(0, 96).trim();
  if (!text) return null;
  const token = text
    .toLowerCase()
    .replace(/[^a-z0-9._:\-+=@]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return token || null;
}

function normalizeDeckSourceStatus(
  value: unknown,
): Record<string, string> | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const out: Record<string, string> = {};
  for (const key of LIVE_SOURCE_STATUS_KEYS) {
    const token = normalizeSourceStatusToken(row[key]);
    if (token) out[key] = token;
  }
  return Object.keys(out).length > 0 ? out : null;
}

export function normalizeLiveContextPayload(
  value: unknown,
): LibraryLiveContext | null {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return null;
  const row = value as Record<string, unknown>;
  const context: LibraryLiveContext = {};
  const schemaVersion = finiteOrNull(row.live_context_schema_version);
  if (
    schemaVersion !== null &&
    Number.isInteger(schemaVersion) &&
    schemaVersion >= 1
  ) {
    context.live_context_schema_version = Math.min(99, schemaVersion);
  }
  const capabilities = normalizeLiveContextCapabilities(
    row.live_context_capabilities,
  );
  if (capabilities.length > 0) {
    context.live_context_capabilities = capabilities;
  }
  const deck = stringOrNull(row.deck);
  if (deck) context.deck = deck;
  if (typeof row.audible === "boolean") context.audible = row.audible;
  const phase = stringOrNull(row.phase);
  if (phase) context.phase = phase;
  const bpm = finiteOrNull(row.bpm);
  if (bpm !== null && bpm > 0) context.bpm = bpm;
  const music = finiteOrNull(row.music);
  if (music !== null && music >= 0) context.music = Math.min(1, music);

  const deckState: Record<string, LibraryLiveDeck> = {};
  const rawDecks = row.deck_state;
  const hasDeckStatePayload =
    rawDecks != null &&
    typeof rawDecks === "object" &&
    !Array.isArray(rawDecks);
  if (hasDeckStatePayload) {
    const rawDeckMap = rawDecks as Record<string, unknown>;
    for (const side of ["A", "B", "C", "D"]) {
      const liveDeck = normalizeLiveDeck(rawDeckMap[side]);
      if (liveDeck) deckState[side] = liveDeck;
    }
  }
  if (hasDeckStatePayload) context.deck_state = deckState;

  const hasDeckMixerPayload =
    row.deck_mixer != null &&
    typeof row.deck_mixer === "object" &&
    !Array.isArray(row.deck_mixer);
  const deckMixer = normalizeLiveDeckMixer(row.deck_mixer);
  if (deckMixer) context.deck_mixer = deckMixer;
  else if (hasDeckMixerPayload) context.deck_mixer = {};

  const deckSourceStatus = normalizeDeckSourceStatus(row.deck_source_status);
  if (deckSourceStatus) context.deck_source_status = deckSourceStatus;

  const deckLanesContext = normalizeDeckLanesContext(row.deck_lanes_context);
  if (deckLanesContext) context.deck_lanes_context = deckLanesContext;

  const deckReferenceContext = normalizeDeckReferenceContext(
    row.deck_reference_context,
  );
  if (deckReferenceContext)
    context.deck_reference_context = deckReferenceContext;

  const deckSourceContext = normalizeDeckSourceContext(row.deck_source_context);
  if (deckSourceContext) context.deck_source_context = deckSourceContext;

  const deckAudioContext = normalizeDeckAudioContext(row.deck_audio_context);
  if (deckAudioContext) context.deck_audio_context = deckAudioContext;

  const deckAudioSeparationContext = normalizeDeckAudioSeparationContext(
    row.deck_audio_separation_context,
  );
  if (deckAudioSeparationContext)
    context.deck_audio_separation_context = deckAudioSeparationContext;

  const deckAudioFeaturesContext = normalizeDeckAudioFeaturesContext(
    row.deck_audio_features_context,
  );
  if (deckAudioFeaturesContext)
    context.deck_audio_features_context = deckAudioFeaturesContext;

  const deckAudioDeltaContext = normalizeDeckAudioDeltaContext(
    row.deck_audio_delta_context,
  );
  if (deckAudioDeltaContext)
    context.deck_audio_delta_context = deckAudioDeltaContext;

  const deckAudioWindowContext = normalizeDeckAudioWindowContext(
    row.deck_audio_window_context,
  );
  if (deckAudioWindowContext)
    context.deck_audio_window_context = deckAudioWindowContext;

  const audioPartContext = normalizeAudioPartContext(row.audio_part_context);
  if (audioPartContext) context.audio_part_context = audioPartContext;
  const audioPartDeckLabels = audioPartDeckLabelsForContext(audioPartContext);

  const audioWindowContext = normalizeAudioWindowContext(
    row.audio_window_context,
  );
  if (
    audioWindowContext &&
    audioWindowMatchesAudioPartLabels(audioWindowContext, audioPartDeckLabels)
  ) {
    context.audio_window_context = audioWindowContext;
  }
  const audioWindowMap = normalizeAudioWindowMap(row.audio_window_map);
  if (
    audioWindowMap &&
    audioWindowMapMatchesAudioPartLabels(audioWindowMap, audioPartDeckLabels)
  ) {
    context.audio_window_map = audioWindowMap;
  }

  const audioDelta = normalizeRecentMoves(row.audio_delta).slice(-4);
  if (audioDelta.length > 0) context.audio_delta = audioDelta;

  const liveEvidence = normalizeLiveEvidence(row.live_evidence);
  if (liveEvidence) context.live_evidence = liveEvidence;

  const recentMoves = normalizeRecentMoves(row.recent_moves);
  if (recentMoves.length > 0) context.recent_moves = recentMoves;

  const derivedEvidence = deriveLiveEvidence(context);
  const mergedEvidence = mergeLiveEvidencePayload(
    context.live_evidence,
    derivedEvidence,
  );
  if (mergedEvidence) context.live_evidence = mergedEvidence;

  return context.deck ||
    context.live_context_schema_version !== undefined ||
    context.live_context_capabilities !== undefined ||
    context.deck_state !== undefined ||
    context.deck_mixer !== undefined ||
    context.deck_source_status !== undefined ||
    context.deck_lanes_context ||
    context.deck_reference_context ||
    context.deck_source_context ||
    context.deck_audio_context ||
    context.deck_audio_separation_context ||
    context.deck_audio_features_context ||
    context.deck_audio_delta_context ||
    context.deck_audio_window_context ||
    context.audio_part_context ||
    context.music !== undefined ||
    context.audio_window_context ||
    context.audio_window_map ||
    context.audio_delta ||
    context.live_evidence ||
    context.recent_moves
    ? context
    : null;
}

function normalizeRecentMoves(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => stringOrNull(item))
    .filter((item): item is string => item !== null)
    .slice(-6);
}

export function normalizeLiveMovePayload(value: unknown): string[] {
  if (value == null || typeof value !== "object" || Array.isArray(value))
    return [];
  const row = value as Record<string, unknown>;
  const payload =
    row.payload != null &&
    typeof row.payload === "object" &&
    !Array.isArray(row.payload)
      ? (row.payload as Record<string, unknown>)
      : row;
  const events = payload.midi_events;
  if (!Array.isArray(events)) return [];
  const controls = events
    .map((event) => {
      if (event == null || typeof event !== "object" || Array.isArray(event))
        return null;
      return stringOrNull((event as Record<string, unknown>).control);
    })
    .filter((control): control is string => control !== null);
  return controls.slice(-6);
}

function optionalStringArray(
  record: Record<string, unknown>,
  key: string,
): string[] | undefined {
  const value = record[key];
  if (value === undefined || value === null) return undefined;
  return asStringArray(value, key);
}

function normalizeTrackResult(value: unknown, label: string): TrackResult {
  const row = asRecord(value, label);
  return {
    track_id: asString(row.track_id, `${label}.track_id`),
    title: asString(row.title, `${label}.title`),
    score: asFiniteNumber(row.score, `${label}.score`),
    meta: asString(row.meta, `${label}.meta`),
  };
}

export function normalizeSearchResult(
  value: unknown,
  label = "library_search",
): SearchResult {
  const root = asRecord(value, label);
  return {
    results: asArray(root.results, `${label}.results`).map((row, index) =>
      normalizeTrackResult(row, `${label}.results[${index}]`),
    ),
    centered: asBoolean(root.centered, `${label}.centered`),
    corpus_size: asFiniteNumber(root.corpus_size, `${label}.corpus_size`),
  };
}

function normalizeCurateTrack(value: unknown, label: string): CurateTrack {
  const row = asRecord(value, label);
  return {
    track_id: asString(row.track_id, `${label}.track_id`),
    title: asString(row.title, `${label}.title`),
    meta: asString(row.meta, `${label}.meta`),
  };
}

export function normalizeCurateResult(
  value: unknown,
  label = "library_curate",
): CurateResult {
  const root = asRecord(value, label);
  const result: CurateResult = {
    name: asString(root.name, `${label}.name`),
    rationale: asString(root.rationale, `${label}.rationale`),
    stop_reason: asString(root.stop_reason, `${label}.stop_reason`),
    tracks: asArray(root.tracks, `${label}.tracks`).map((track, index) =>
      normalizeCurateTrack(track, `${label}.tracks[${index}]`),
    ),
    count: asFiniteNumber(root.count, `${label}.count`),
  };
  if (root.question !== undefined && root.question !== null) {
    result.question = asString(root.question, `${label}.question`);
  }
  if (root.choices !== undefined && root.choices !== null) {
    result.choices = asStringArray(root.choices, `${label}.choices`);
  }
  return result;
}

export function normalizeBuildSetResult(value: unknown): BuildSetResult {
  const root = asRecord(value, "library_build_set");
  return {
    ...normalizeCurateResult(root, "library_build_set"),
    export_path: asNullableString(
      root.export_path,
      "library_build_set.export_path",
    ),
  };
}

export function normalizeCueResult(
  value: unknown,
  label = "library_cue_folder",
): LibraryCueResult {
  const root = asRecord(value, label);
  const rawOutputs = asRecord(root.outputs, `${label}.outputs`);
  const outputs: LibraryCueResult["outputs"] = {};
  for (const key of ["rekordbox", "m3u8"] as const) {
    const value = rawOutputs[key];
    if (value !== undefined && value !== null) {
      outputs[key] = asString(value, `${label}.outputs.${key}`);
    }
  }
  return {
    ok: asBoolean(root.ok, `${label}.ok`),
    mode: asString(root.mode, `${label}.mode`),
    tracks_cued: asFiniteNumber(root.tracks_cued, `${label}.tracks_cued`),
    cues_total: asFiniteNumber(root.cues_total, `${label}.cues_total`),
    skipped: asFiniteNumber(root.skipped, `${label}.skipped`),
    outputs,
  };
}

function normalizeToolTrace(
  value: unknown,
  label: string,
): LibraryChatToolTrace {
  const row = asRecord(value, label);
  return {
    name: asString(row.name, `${label}.name`),
    arg: asString(row.arg, `${label}.arg`),
    ok: asBoolean(row.ok, `${label}.ok`),
  };
}

function normalizePlaylist(
  value: unknown,
  label: string,
): LibraryChatPlaylist | null {
  if (value == null) return null;
  const row = asRecord(value, label);
  return {
    name: asString(row.name, `${label}.name`),
    track_ids: asStringArray(row.track_ids, `${label}.track_ids`),
    m3u_path: asString(row.m3u_path, `${label}.m3u_path`),
    json_path: asString(row.json_path, `${label}.json_path`),
    dropped_ids: asStringArray(row.dropped_ids, `${label}.dropped_ids`),
  };
}

function normalizeMoveGradeSlug(
  value: unknown,
  label: string,
): LibraryMoveGradeSlug {
  const slug = asString(value, label);
  if (
    slug === "negative" ||
    slug === "mid" ||
    slug === "clean" ||
    slug === "sexy" ||
    slug === "bomb" ||
    slug === "lit_aff"
  ) {
    return slug;
  }
  throw new Error(`${label}: unknown move grade`);
}

function normalizeChatMoveGrade(
  value: unknown,
  label: string,
): LibraryChatMoveGrade {
  const row = asRecord(value, label);
  const grade: LibraryChatMoveGrade = {
    candidate_id: asString(row.candidate_id, `${label}.candidate_id`),
    track_id: asString(row.track_id, `${label}.track_id`),
    title: asString(row.title, `${label}.title`),
    slug: normalizeMoveGradeSlug(row.slug, `${label}.slug`),
    label: asString(row.label, `${label}.label`),
    xp: asFiniteNumber(row.xp, `${label}.xp`),
    reason: asString(row.reason, `${label}.reason`),
    overdrive: asBoolean(row.overdrive, `${label}.overdrive`),
  };
  const streak = optionalRecordNumber(row, "streak", `${label}.streak`);
  if (streak !== undefined) grade.streak = streak;
  const totalXp = optionalRecordNumber(row, "total_xp", `${label}.total_xp`);
  if (totalXp !== undefined) grade.total_xp = totalXp;
  const level = optionalRecordNumber(row, "level", `${label}.level`);
  if (level !== undefined) grade.level = level;
  const levelXp = optionalRecordNumber(row, "level_xp", `${label}.level_xp`);
  if (levelXp !== undefined) grade.level_xp = levelXp;
  const nextLevelXp = optionalRecordNumber(
    row,
    "next_level_xp",
    `${label}.next_level_xp`,
  );
  if (nextLevelXp !== undefined) grade.next_level_xp = nextLevelXp;
  const levelUp = optionalRecordBoolean(row, "level_up", `${label}.level_up`);
  if (levelUp !== undefined) grade.level_up = levelUp;
  const levelsGained = optionalRecordNumber(
    row,
    "levels_gained",
    `${label}.levels_gained`,
  );
  if (levelsGained !== undefined) grade.levels_gained = levelsGained;
  return grade;
}

function normalizeChatMoveGrades(value: unknown): LibraryChatMoveGrade[] {
  if (value === undefined || value === null) return [];
  return asArray(value, "library_chat.move_grades").map((row, index) =>
    normalizeChatMoveGrade(row, `library_chat.move_grades[${index}]`),
  );
}

function normalizeLiveVerification(
  value: unknown,
): LibraryLiveVerification | undefined {
  if (value === undefined || value === null) return undefined;
  const row = asRecord(value, "library_chat.live_verification");
  const result: LibraryLiveVerification = {
    ok: asBoolean(row.ok, "library_chat.live_verification.ok"),
    violations: asStringArray(
      row.violations,
      "library_chat.live_verification.violations",
    ),
    reply: asString(row.reply, "library_chat.live_verification.reply"),
    corrected: asBoolean(
      row.corrected,
      "library_chat.live_verification.corrected",
    ),
    corrected_reply: asNullableString(
      row.corrected_reply,
      "library_chat.live_verification.corrected_reply",
    ),
    claim_policy: asString(
      row.claim_policy,
      "library_chat.live_verification.claim_policy",
    ),
    transport_status: asString(
      row.transport_status,
      "library_chat.live_verification.transport_status",
    ),
    move_grades_allowed: asBoolean(
      row.move_grades_allowed,
      "library_chat.live_verification.move_grades_allowed",
    ),
    move_grades_seen: asFiniteNumber(
      row.move_grades_seen,
      "library_chat.live_verification.move_grades_seen",
    ),
  };
  const guardApplied = optionalRecordBoolean(
    row,
    "guard_applied",
    "library_chat.live_verification.guard_applied",
  );
  if (guardApplied !== undefined) result.guard_applied = guardApplied;
  if (row.guard_violations !== undefined && row.guard_violations !== null) {
    result.guard_violations = asStringArray(
      row.guard_violations,
      "library_chat.live_verification.guard_violations",
    );
  }
  return result;
}

export function normalizeChatResult(value: unknown): LibraryChatResult {
  const root = asRecord(value, "library_chat");
  const result: LibraryChatResult = {
    reply: asString(root.reply, "library_chat.reply"),
    tool_trace: asArray(root.tool_trace, "library_chat.tool_trace").map(
      (trace, index) =>
        normalizeToolTrace(trace, `library_chat.tool_trace[${index}]`),
    ),
    playlist: normalizePlaylist(root.playlist, "library_chat.playlist"),
    export_path: asNullableString(root.export_path, "library_chat.export_path"),
    seen_track_ids: asStringArray(
      root.seen_track_ids,
      "library_chat.seen_track_ids",
    ),
    move_grades: normalizeChatMoveGrades(root.move_grades),
    live_verification: normalizeLiveVerification(root.live_verification),
    iterations: asFiniteNumber(root.iterations, "library_chat.iterations"),
    stop_reason: asString(root.stop_reason, "library_chat.stop_reason"),
  };
  if (root.question !== undefined && root.question !== null) {
    result.question = asString(root.question, "library_chat.question");
  }
  if (root.choices !== undefined && root.choices !== null) {
    result.choices = asStringArray(root.choices, "library_chat.choices");
  }
  return result;
}

function normalizeLibraryImportAction(
  value: unknown,
  label: string,
): LibraryImportAction | undefined {
  if (value === undefined || value === null) return undefined;
  const action = asRecord(value, label);
  if (action.type !== "ipc.library.import") return undefined;
  const payload = asRecord(action.payload, `${label}.payload`);
  const path = stringOrNull(payload.path);
  if (!path) return undefined;
  const version =
    payload.schema_version === undefined || payload.schema_version === null
      ? "1"
      : asString(payload.schema_version, `${label}.payload.schema_version`);
  if (version !== "1") return undefined;
  return {
    type: "ipc.library.import",
    payload: { path, schema_version: "1" },
  };
}

function normalizeLibrarySetupCandidate(
  value: unknown,
  label: string,
): LibrarySetupCandidate {
  const row = asRecord(value, label);
  const candidate: LibrarySetupCandidate = {
    kind: asString(row.kind, `${label}.kind`),
    path: asString(row.path, `${label}.path`),
    confidence: optionalString(row, "confidence"),
    reason: optionalString(row, "reason"),
    command: optionalString(row, "command"),
    audio_files_seen: optionalNumber(row, "audio_files_seen"),
  };
  const importAction = normalizeLibraryImportAction(
    row.import_action,
    `${label}.import_action`,
  );
  if (importAction) candidate.import_action = importAction;
  return candidate;
}

function normalizeLibrarySetupCandidates(
  value: unknown,
  label: string,
): LibrarySetupCandidate[] {
  if (value === undefined || value === null) return [];
  return asArray(value, label).map((item, index) =>
    normalizeLibrarySetupCandidate(item, `${label}[${index}]`),
  );
}

export function normalizeStats(value: unknown): LibraryStats {
  const root = asRecord(value, "library_stats");
  const freshness =
    root.library_freshness !== undefined && root.library_freshness !== null
      ? asRecord(root.library_freshness, "library_stats.library_freshness")
      : null;
  return {
    indexed: asFiniteNumber(root.indexed, "library_stats.indexed"),
    backend: asString(root.backend, "library_stats.backend"),
    embedding_backend: optionalString(root, "embedding_backend"),
    embedding_dim: optionalNumber(root, "embedding_dim"),
    clap_model_installed: optionalBoolean(root, "clap_model_installed"),
    clap_model_path: optionalString(root, "clap_model_path"),
    clap_model_missing: optionalStringArray(root, "clap_model_missing"),
    library_freshness: freshness
      ? {
          status: optionalString(freshness, "status"),
          stale: optionalBoolean(freshness, "stale"),
          reason: optionalString(freshness, "reason"),
          age_days: optionalNumber(freshness, "age_days"),
          cache_path: optionalString(freshness, "cache_path"),
          source_path:
            freshness.source_path === null
              ? null
              : optionalString(freshness, "source_path"),
          source_age_days:
            freshness.source_age_days === null
              ? null
              : optionalNumber(freshness, "source_age_days"),
          cache_mtime:
            freshness.cache_mtime === null
              ? null
              : optionalNumber(freshness, "cache_mtime"),
          source_mtime:
            freshness.source_mtime === null
              ? null
              : optionalNumber(freshness, "source_mtime"),
        }
      : undefined,
    library_freshness_status: optionalString(root, "library_freshness_status"),
    library_stale: optionalBoolean(root, "library_stale"),
    library_staleness_reason: optionalString(root, "library_staleness_reason"),
    library_age_days: optionalNumber(root, "library_age_days"),
    agent_backend: optionalString(root, "agent_backend"),
    agent_ready: optionalBoolean(root, "agent_ready"),
    agent_status: optionalString(root, "agent_status"),
    agent_hint: optionalString(root, "agent_hint"),
    library_setup_candidates: normalizeLibrarySetupCandidates(
      root.library_setup_candidates,
      "library_stats.library_setup_candidates",
    ),
    spent_eur: asFiniteNumber(root.spent_eur, "library_stats.spent_eur"),
    failed: asFiniteNumber(root.failed, "library_stats.failed"),
  };
}

function normalizeModelFile(
  value: unknown,
  label: string,
): LibraryModelInstallFile {
  const row = asRecord(value, label);
  return {
    rel_path: asString(row.rel_path, `${label}.rel_path`),
    source_rel_path: optionalString(row, "source_rel_path"),
    path: asString(row.path, `${label}.path`),
    status: asString(row.status, `${label}.status`),
    size: asFiniteNumber(row.size, `${label}.size`),
    sha256: asString(row.sha256, `${label}.sha256`),
    url: asString(row.url, `${label}.url`),
  };
}

function normalizeModelInstallItem(
  value: unknown,
  label: string,
): LibraryModelInstallItem {
  const row = asRecord(value, label);
  return {
    id: asString(row.id, `${label}.id`),
    installed: asBoolean(row.installed, `${label}.installed`),
    path: asString(row.path, `${label}.path`),
    files: asArray(row.files, `${label}.files`).map((file, index) =>
      normalizeModelFile(file, `${label}.files[${index}]`),
    ),
    errors: asStringArray(row.errors, `${label}.errors`),
  };
}

function normalizeInstallTarget(
  value: unknown,
  label: string,
): LibraryModelInstallTarget {
  const target = asString(value, label);
  if (
    target === "required" ||
    target === "clap" ||
    target === "moss" ||
    target === "cue" ||
    target === "all"
  ) {
    return target;
  }
  throw new Error(`${label}: unknown target`);
}

function normalizeInstallSummary(
  value: unknown,
): LibraryModelInstallSummary | undefined {
  if (value === undefined || value === null) return undefined;
  const root = asRecord(value, "library_models.install");
  return {
    target: normalizeInstallTarget(
      root.target,
      "library_models.install.target",
    ),
    results: asArray(root.results, "library_models.install.results").map(
      (item, index) =>
        normalizeModelInstallItem(
          item,
          `library_models.install.results[${index}]`,
        ),
    ),
    ok: asBoolean(root.ok, "library_models.install.ok"),
  };
}

function normalizeModelAsset(value: unknown, label: string): LibraryModelAsset {
  const row = asRecord(value, label);
  return {
    id: asString(row.id, `${label}.id`),
    label: asString(row.label, `${label}.label`),
    role: asString(row.role, `${label}.role`),
    required: asBoolean(row.required, `${label}.required`),
    env: asString(row.env, `${label}.env`),
    installed: asBoolean(row.installed, `${label}.installed`),
    installable: optionalBoolean(row, "installable"),
    path: asString(row.path, `${label}.path`),
    missing: asStringArray(row.missing, `${label}.missing`),
    mismatched: optionalStringArray(row, "mismatched"),
  };
}

export function normalizeModelsResult(value: unknown): LibraryModelsResult {
  const root = asRecord(value, "library_models");
  return {
    models: asArray(root.models, "library_models.models").map((model, index) =>
      normalizeModelAsset(model, `library_models.models[${index}]`),
    ),
    required_ready: asBoolean(
      root.required_ready,
      "library_models.required_ready",
    ),
    all_ready: asBoolean(root.all_ready, "library_models.all_ready"),
    install: normalizeInstallSummary(root.install),
  };
}

export function normalizeEmbedProgress(value: unknown): EmbedProgress {
  const root = asRecord(value, "library://embed-progress");
  const status = asString(root.status, "library://embed-progress.status");
  if (status !== "ok" && status !== "skip" && status !== "err") {
    throw new Error("library://embed-progress.status: unknown status");
  }
  return {
    n: asFiniteNumber(root.n, "library://embed-progress.n"),
    total: asFiniteNumber(root.total, "library://embed-progress.total"),
    status,
    filename: asString(root.filename, "library://embed-progress.filename"),
    cost_eur: asFiniteNumber(
      root.cost_eur,
      "library://embed-progress.cost_eur",
    ),
  };
}

export function normalizeEmbedDone(value: unknown): EmbedDone {
  const root = asRecord(value, "library://embed-done");
  return {
    embedded: asFiniteNumber(root.embedded, "library://embed-done.embedded"),
    skipped: asFiniteNumber(root.skipped, "library://embed-done.skipped"),
    failed: asFiniteNumber(root.failed, "library://embed-done.failed"),
    total: asFiniteNumber(root.total, "library://embed-done.total"),
    cost_eur: asFiniteNumber(root.cost_eur, "library://embed-done.cost_eur"),
  };
}

export function normalizeModelProgress(value: unknown): LibraryModelProgress {
  const root = asRecord(value, "library://model-progress");
  return {
    target: normalizeInstallTarget(
      root.target,
      "library://model-progress.target",
    ),
    id: asString(root.id, "library://model-progress.id"),
    n: asFiniteNumber(root.n, "library://model-progress.n"),
    total: asFiniteNumber(root.total, "library://model-progress.total"),
    status: asString(root.status, "library://model-progress.status"),
    rel_path: asString(root.rel_path, "library://model-progress.rel_path"),
    downloaded: asFiniteNumber(
      root.downloaded,
      "library://model-progress.downloaded",
    ),
    size: asFiniteNumber(root.size, "library://model-progress.size"),
    error: optionalString(root, "error"),
  };
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
    {
      track_id: "23381471",
      title: "Raffertie — The Substance",
      score: 0.764,
      meta: "folder:23381471 / vector",
    },
    {
      track_id: "b8d4da96",
      title: "ARTLUS - i like the way you kiss me (Remix)",
      score: 0.758,
      meta: "folder:b8d4da96 / vector",
    },
    {
      track_id: "911ea756",
      title: "Quälgeist",
      score: 0.751,
      meta: "folder:911ea756 / vector",
    },
    {
      track_id: "a8f148f3",
      title: "FLKN - I Need Acid (Original mix)",
      score: 0.739,
      meta: "folder:a8f148f3 / vector",
    },
    {
      track_id: "7f9f9052",
      title: "Charli XCX - Guess (DJ Daddy Trance Edit)",
      score: 0.737,
      meta: "folder:7f9f9052 / vector",
    },
    {
      track_id: "a0b1a41b",
      title: "Brutalismus 3000 - nur mein körper und die angst",
      score: 0.734,
      meta: "folder:a0b1a41b / vector",
    },
  ],
};

const DEV_SIMILAR: SearchResult = {
  centered: true,
  corpus_size: 142,
  results: [
    {
      track_id: "girl-like-me",
      title: "Girl Like Me",
      score: 0.369,
      meta: "centered · cos",
    },
    {
      track_id: "fka-wild-alone",
      title: "FKA Twigs - Wild And Alone",
      score: 0.313,
      meta: "centered · cos",
    },
    {
      track_id: "troye-one-girls",
      title: "Troye Sivan - One of Your Girls",
      score: 0.308,
      meta: "centered · cos",
    },
    {
      track_id: "beatback",
      title: "Beatback",
      score: 0.305,
      meta: "centered · cos",
    },
    {
      track_id: "kylie-stateside",
      title: "Kylie Minogue - Stateside",
      score: 0.299,
      meta: "centered · cos",
    },
    {
      track_id: "i-hate-u-demo",
      title: "i hate u (demo) ft. Tor Miller",
      score: 0.279,
      meta: "centered · cos",
    },
  ],
};

const DEV_STATS: LibraryStats = {
  indexed: 142,
  backend: "sqlite-vec",
  embedding_backend: "clap",
  embedding_dim: 512,
  clap_model_installed: true,
  clap_model_path: "~/.cache/vibemix/clap-onnx",
  clap_model_missing: [],
  library_freshness: {
    status: "fresh",
    stale: false,
    reason: "dev_fixture",
    age_days: 0,
    cache_path: "~/.cache/vibemix/library.pkl",
    source_path: "~/Music/rekordbox/collection.xml",
    source_age_days: 0,
    cache_mtime: null,
    source_mtime: null,
  },
  library_freshness_status: "fresh",
  library_stale: false,
  library_staleness_reason: "dev_fixture",
  library_age_days: 0,
  agent_backend: "codex",
  agent_ready: true,
  agent_status: "ready",
  agent_hint: "",
  library_setup_candidates: [],
  spent_eur: 0.19,
  failed: 0,
};

const DEV_MODELS: LibraryModelsResult = {
  models: [
    {
      id: "clap",
      label: "CLAP ONNX",
      role: "library embeddings/search/similarity",
      required: true,
      installable: true,
      env: "VIBEMIX_CLAP_ONNX_DIR",
      installed: true,
      path: "~/.cache/vibemix/clap-onnx",
      missing: [],
      mismatched: [],
    },
    {
      id: "moss-tts",
      label: "MOSS TTS ONNX",
      role: "local co-host voice",
      required: true,
      installable: false,
      env: "VIBEMIX_MOSS_TTS_DIR",
      installed: true,
      path: "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX",
      missing: [],
      mismatched: [],
    },
    {
      id: "cue-detr",
      label: "CUE-DETR ONNX",
      role: "cue-anchored ingest and structural cue detection",
      required: false,
      installable: false,
      env: "VIBEMIX_CUE_ONNX_PATH",
      installed: true,
      path: "~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx",
      missing: [],
      mismatched: [],
    },
  ],
  required_ready: true,
  all_ready: true,
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
    "floor. Kept the BPM drift under ±4% so the blends stay clean.",
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
    "drift held under ±4% so the transitions stay clean. Each move is the " +
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

// GUI-safe cue export sample. This mirrors `library cue <folder> --json` in
// export mode only: no Serato tag writes, no fake pad-render claim.
const DEV_CUE: LibraryCueResult = {
  ok: true,
  mode: "export",
  tracks_cued: 8,
  cues_total: 42,
  skipped: 1,
  outputs: {
    rekordbox: "~/Library/Application Support/vibemix/exports/vibemix-cues.xml",
  },
};

const DEV_CHAT: LibraryChatResult = {
  reply:
    "For the presentation, keep it tight: open with the pill listening, ask for a darker peak-time bridge, then show the grounded tool trace.",
  tool_trace: [{ name: "search_vibe", arg: "dark peak-time bridge", ok: true }],
  playlist: null,
  export_path: null,
  seen_track_ids: ["7f9f9052", "b8d4da96"],
  move_grades: [
    {
      candidate_id: "tr_demo_001",
      track_id: "7f9f9052",
      title: "7f9f9052",
      slug: "lit_aff",
      label: "LIT AFF",
      xp: 100,
      reason: "everything clicks",
      overdrive: true,
      streak: 4,
      total_xp: 288,
      level: 2,
      level_xp: 38,
      next_level_xp: 250,
      level_up: true,
      levels_gained: 1,
    },
  ],
  iterations: 2,
  stop_reason: "model_done",
};

/** The 8-file embed log from the subset run — replayed in dev to animate the
 *  ingest progress bar + live log without a real folder embed. */
const DEV_EMBED_LOG: Array<[EmbedProgress["status"], string, number]> = [
  ["ok", "jecta — purrr (at the goth club).mp3", 0.191],
  ["ok", "Just Like You.mp3", 0.19],
  ["skip", "Brutalismus 3000 - badthiings.mp3", 0.19],
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
  cue: DEV_CUE,
  chat: DEV_CHAT,
  stats: DEV_STATS,
  models: DEV_MODELS,
  embedLog: DEV_EMBED_LOG,
} as const;

// ── Public client ───────────────────────────────────────────────────────────

/** Text vibe query → ranked tracks + scope geometry. */
export async function librarySearch(
  query: string,
  k = 6,
): Promise<SearchResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_SEARCH; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return normalizeSearchResult(
    await invoke<unknown>("library_search", { query, k }),
    "library_search",
  );
}

/** Seed (track_id or dropped file path) → nearest neighbours. */
export async function librarySimilar(
  seed: string,
  k = 6,
): Promise<SearchResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_SIMILAR; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return normalizeSearchResult(
    await invoke<unknown>("library_similar", { seed, k }),
    "library_similar",
  );
}

/** Theme → AI-curated playlist (one-shot, NOT interactive). */
export async function libraryCurate(theme: string): Promise<CurateResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_CURATE; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return normalizeCurateResult(
    await invoke<unknown>("library_curate", { theme }),
    "library_curate",
  );
}

/** Brief + energy curve → Viber set-prep agent: a discovered + sequenced set,
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
  return normalizeBuildSetResult(
    await invoke<unknown>("library_build_set", { brief, curve }),
  );
}

/** Folder → auto-cued Rekordbox XML/M3U8. GUI-safe export path only: this never
 *  invokes Serato tag writes, which remain an explicit CLI-only mutation. */
export async function libraryCueFolder(
  path: string,
  exportFormat: CueExportFormat = "rekordbox",
  out?: string,
  name = "vibemix cues",
  maxCues = 8,
): Promise<LibraryCueResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_CUE;
  return normalizeCueResult(
    await invoke<unknown>("library_cue_folder", {
      path,
      exportFormat,
      out,
      name,
      maxCues,
    }),
  );
}

/** One conversational Viber turn. `history` is stateless caller-owned memory;
 *  the bridge passes it to the Python CLI as JSON and returns ChatResult as-is. */
export async function libraryChat(
  message: string,
  history: LibraryChatTurn[] = [],
  liveContext?: LibraryLiveContext | null,
): Promise<LibraryChatResult> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_CHAT; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return normalizeChatResult(
    await invoke<unknown>("library_chat", { message, history, liveContext }),
  );
}

/** Corpus readout for the left console. */
export async function libraryStats(): Promise<LibraryStats> {
  const invoke = await getInvoke();
  if (!invoke) return DEV_STATS; // no Tauri (plain vite / jsdom) → demo data
  // Real bridge: let a backend error PROPAGATE — never mask it with fake data.
  return normalizeStats(await invoke<unknown>("library_stats"));
}

/** Local model asset status/install seam. With `install="required"` the backend
 *  downloads/verifies first-run required assets (CLAP + MOSS voice);
 *  `install="cue"` reports/verifies the manual CUE target until hosting exists.
 *  Real backend errors propagate. */
export async function libraryModels(
  install?: LibraryModelInstallTarget,
  force = false,
): Promise<LibraryModelsResult> {
  const invoke = await getInvoke();
  if (!invoke) {
    if (!install) return DEV_MODELS;
    const installModels = DEV_MODELS.models.filter((model) => {
      if (install === "all") return true;
      if (install === "required") return model.required;
      if (install === "clap") return model.id === "clap";
      if (install === "moss") return model.id === "moss-tts";
      return model.id === "cue-detr";
    });
    return {
      ...DEV_MODELS,
      install: {
        target: install,
        ok: true,
        results: installModels.map((model) => ({
          id: model.id,
          installed: model.installed,
          path: model.path,
          files: [],
          errors: [],
        })),
      },
    };
  }
  return normalizeModelsResult(
    await invoke<unknown>("library_models", { install, force }),
  );
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

/** Subscribe to the live flat-frame deck snapshot bridged by ws_client.rs. */
export async function onLiveDeckContext(
  cb: (context: LibraryLiveContext) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<unknown>("live-deck-context", (e) => {
      const context = normalizeLiveContextPayload(e.payload);
      if (context) cb(context);
    });
  } catch {
    return NO_UNLISTEN;
  }
}

/** Subscribe to recent controller moves from the existing session snapshot. */
export async function onLiveMoveContext(
  cb: (moves: string[]) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<unknown>("ipc-session-snapshot", (e) => {
      const moves = normalizeLiveMovePayload(e.payload);
      cb(moves);
    });
  } catch {
    return NO_UNLISTEN;
  }
}

/** Subscribe to per-file embed progress. No-op unlisten in non-Tauri envs. */
export async function onEmbedProgress(
  cb: (p: EmbedProgress) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<unknown>("library://embed-progress", (e) => {
      try {
        cb(normalizeEmbedProgress(e.payload));
      } catch (err) {
        console.warn("[vmx-lib] dropped malformed embed-progress:", err);
      }
    });
  } catch {
    return NO_UNLISTEN;
  }
}

/** Subscribe to embed completion. No-op unlisten in non-Tauri envs. */
export async function onEmbedDone(
  cb: (d: EmbedDone) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<unknown>("library://embed-done", (e) => {
      try {
        cb(normalizeEmbedDone(e.payload));
      } catch (err) {
        console.warn("[vmx-lib] dropped malformed embed-done:", err);
      }
    });
  } catch {
    return NO_UNLISTEN;
  }
}

/** Subscribe to first-run local model install progress. No-op outside Tauri. */
export async function onModelProgress(
  cb: (p: LibraryModelProgress) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<unknown>("library://model-progress", (e) => {
      try {
        cb(normalizeModelProgress(e.payload));
      } catch (err) {
        console.warn("[vmx-lib] dropped malformed model-progress:", err);
      }
    });
  } catch {
    return NO_UNLISTEN;
  }
}

/** One live tool call from Viber's Codex run (the agentic tape). Emitted by the
 *  Rust bridge as `library://viber-tool` while a curate/build/chat runs, so the
 *  conversation can show each tool firing — search, sequence, create — live. */
export interface LibraryViberToolEvent {
  tool: string;
  ok: boolean;
  summary: string;
}

function normalizeViberTool(payload: unknown): LibraryViberToolEvent {
  const p = (payload ?? {}) as Record<string, unknown>;
  return {
    tool: typeof p.tool === "string" ? p.tool : "?",
    ok: p.ok !== false,
    summary: typeof p.summary === "string" ? p.summary : "",
  };
}

export async function onViberTool(
  cb: (e: LibraryViberToolEvent) => void,
): Promise<UnlistenFn> {
  try {
    return await tauriListen<unknown>("library://viber-tool", (e) => {
      try {
        cb(normalizeViberTool(e.payload));
      } catch (err) {
        console.warn("[vmx-lib] dropped malformed viber-tool:", err);
      }
    });
  } catch {
    return NO_UNLISTEN;
  }
}
