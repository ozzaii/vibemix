// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — library window entry point.
 *
 * Mounts into #app of library.html (the 5th Tauri webview, opened by the Rust
 * bridge's `open_library_window` command). Thin DOM renderer over the pure
 * state-machine.ts; all backend I/O goes through api.ts (typed invoke/event
 * client with a dev fallback so this window renders fully in plain `vite` dev).
 *
 * Six modes (mode switch in the left console):
 *   - search   text query → librarySearch → results + scope
 *   - similar  seed (drop a file or keep the current) → librarySimilar → results + scope
 *   - ingest   folder + strategy → libraryEmbedFolder → progress bar + live log + running €
 *   - curate   theme → libraryCurate → numbered set + notes
 *   - build    brief + curve → libraryBuildSet → ordered set + Rekordbox export
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
  libraryCurate,
  libraryEmbedFolder,
  libraryModels,
  librarySearch,
  librarySimilar,
  libraryStats,
  onEmbedDone,
  onEmbedProgress,
  onModelProgress,
  type BuildSetResult,
  type CurateResult,
  type EmbedDone,
  type EmbedProgress,
  type EmbedStrategy,
  type EnergyCurve,
  type LibraryStats,
  type LibraryChatResult,
  type LibraryChatTurn,
  type LibraryModelInstallTarget,
  type LibraryModelProgress,
  type LibraryModelsResult,
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

let latestStats: LibraryStats | null = null;
let latestModels: LibraryModelsResult | null = null;

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

  $("vmx-lib-rcount").textContent = `${result.results.length} of ${result.corpus_size}`;
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
    el.innerHTML = `<div class="vmx-lib-empty">No set built (${esc(result.stop_reason)}). Try a different theme, or embed more tracks first.</div>`;
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
    el.innerHTML = `<div class="vmx-lib-empty">No set built (${esc(result.stop_reason)}). Check AI setup, embed more tracks, or refine the brief.</div>`;
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

/** Idle state for agent-backed modes. Search/similar can refresh on tab switch;
 *  Codex-backed curate/build should wait for an explicit run or preset chip so
 *  merely opening the mode does not start a slow tool loop. */
function renderAgentIdle(mode: "curate" | "build"): void {
  clearRationale();
  $("vmx-lib-rationale-body").textContent =
    mode === "build" ? "No set built yet." : "No playlist curated yet.";
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
  const msg =
    err instanceof Error
      ? err.message
      : typeof err === "string"
        ? err
        : String(err);
  const el = $("vmx-lib-results");
  el.innerHTML = `<div class="vmx-lib-error"><div class="vmx-lib-error-title">engine error</div><div class="vmx-lib-error-msg">${esc(msg)}</div></div>`;
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
  const agentLabel = stats.agent_ready === false
    ? `Viber ${agent} setup`
    : `Viber ${agent}`;
  return `${agentLabel} / ${model} / ${dim}d / ${stats.backend}`;
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
  const downloaded = files.filter((file) => file.status === "downloaded").length;
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
  if (downloaded > 0) return `${prefix}: downloaded ${downloaded}/${files.length}`;
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
    clap?.installed === false || clapMismatched || models.required_ready === false;
  const needsCue = cueInstallable && (cue?.installed === false || cueMismatched);
  const installTarget: LibraryModelInstallTarget | null =
    needsClap ? "required" : needsCue ? "cue" : null;
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

function setProgress(n: number, total: number, costEur: number, note: string): void {
  const pct = total > 0 ? (n / total) * 100 : 0;
  ($("vmx-lib-progress-fill") as HTMLElement).style.width = `${pct.toFixed(1)}%`;
  $("vmx-lib-prog-n").innerHTML = `${n}<small> / ${total}${note ? ` · ${esc(note)}` : ""}</small>`;
  $("vmx-lib-prog-cost").textContent = `~€${costEur.toFixed(2)}`;
}

function appendLog(status: EmbedProgress["status"], filename: string, costEur: number): void {
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

function setChatTurnText(turn: HTMLElement, text: string, pending = false): void {
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

function renderChatSide(result: LibraryChatResult): void {
  const tools = $("vmx-lib-chat-tools");
  tools.replaceChildren();
  if (result.tool_trace.length === 0) {
    const empty = document.createElement("div");
    empty.className = "vmx-lib-chat-empty";
    empty.textContent = "no tools this turn";
    tools.append(empty);
  } else {
    result.tool_trace.forEach((tool) => {
      const row = document.createElement("div");
      row.className = "vmx-lib-chat-tool";
      row.dataset.ok = String(tool.ok);
      const gem = document.createElement("span");
      gem.className = "gem";
      const text = document.createElement("div");
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = tool.name;
      const arg = document.createElement("div");
      arg.className = "arg";
      arg.textContent = tool.arg || (tool.ok ? "ok" : "failed");
      text.append(name, arg);
      row.append(gem, text);
      tools.append(row);
    });
  }

  const artifact = $("vmx-lib-chat-artifact");
  artifact.replaceChildren();
  const card = chatArtifactCard(result);
  if (card) artifact.append(card);
  $("vmx-lib-scope-state").textContent = isChatSetupStop(result.stop_reason)
    ? `setup · ${result.stop_reason}`
    : `${result.iterations} iter · ${result.stop_reason}`;
}

function isChatSetupStop(stopReason: string): boolean {
  return (
    stopReason === "codex_not_installed" ||
    stopReason === "codex_auth_required" ||
    stopReason === "codex_mcp_blocked"
  );
}

function chatArtifactCard(result: LibraryChatResult): HTMLElement | null {
  const setupStop = isChatSetupStop(result.stop_reason);
  if (
    !setupStop &&
    !result.playlist &&
    !result.export_path &&
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
      : setupStop
        ? "setup"
        : "receipts";
  cap.append(led, label);
  card.append(cap);

  if (setupStop) {
    appendChatCardLine(card, chatSetupTitle(result.stop_reason));
    if (result.reply) appendChatCardLine(card, result.reply);
  }
  if (result.playlist) {
    appendChatCardLine(card, result.playlist.name);
    appendChatCardLine(card, `${result.playlist.track_ids.length} tracks`);
    if (result.playlist.m3u_path) appendChatCardLine(card, result.playlist.m3u_path);
  }
  if (result.export_path) appendChatCardLine(card, result.export_path);
  if (!result.playlist && result.seen_track_ids.length > 0) {
    appendChatCardLine(card, result.seen_track_ids.slice(0, 6).join(" · "));
  }
  return card;
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

  const qInput = $("vmx-lib-q") as HTMLInputElement;
  const folderInput = $("vmx-lib-folder") as HTMLInputElement;
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
  themeInput.value = state.theme;
  briefInput.value = state.brief;
  chatInput.value = state.chatMessage;
  seedNameEl.textContent = state.seed;

  function applyModeVisibility(): void {
    document.body.dataset.mode = state.mode;
    document.querySelectorAll<HTMLElement>(".vmx-lib-modeswitch button").forEach((b) => {
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
          : state.mode === "curate"
            ? "Curated"
            : state.mode === "ingest"
              ? "Embed"
              : "Pulled";
    $("vmx-lib-side-label").textContent =
      state.mode === "chat" ? "Grounding" : "Vibe scope";
    runBtn.textContent = runLabel(state.mode);
    echoEl.textContent = echoText(state);
    if (state.mode === "chat") ensureChatIntro(chatThread);
  }

  async function refreshStats(): Promise<void> {
    renderStats(await libraryStats());
  }

  async function refreshModels(): Promise<void> {
    renderModelSetup(await libraryModels());
  }

  function currentInstallTarget(): LibraryModelInstallTarget {
    return modelInstallTargetFromDataset(installModelsBtn.dataset.installTarget);
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

  async function runSearch(): Promise<void> {
    state = setQuery(state, qInput.value.trim() || state.query);
    echoEl.textContent = state.query;
    renderResults(await librarySearch(state.query), "search");
  }

  async function runSimilar(): Promise<void> {
    echoEl.textContent = state.seed;
    renderResults(await librarySimilar(state.seed), "similar");
  }

  async function runCurate(): Promise<void> {
    state = setTheme(state, themeInput.value.trim() || state.theme);
    echoEl.textContent = state.theme;
    renderCurateLoading(state.theme); // working state before the (slow) agent call
    renderCurate(await libraryCurate(state.theme));
  }

  async function runBuildSet(): Promise<void> {
    state = setBrief(state, briefInput.value.trim() || state.brief);
    echoEl.textContent = state.brief;
    renderBuildSetLoading(state.brief); // working state before the (slow) agent call
    renderBuildSet(await libraryBuildSet(state.brief, state.curve));
  }

  async function runChat(): Promise<void> {
    state = setChatMessage(state, chatInput.value.trim());
    if (!state.chatMessage) return;
    const message = state.chatMessage;
    const priorHistory = chatHistory.slice();

    appendChatTurn(chatThread, "you", message);
    chatHistory.push({ role: "you", text: message });
    chatInput.value = "";
    state = setChatMessage(state, "");
    echoEl.textContent = "conversation";

    const pending = appendChatTurn(chatThread, "viber", "", true);
    renderChatBusy();
    try {
      const result = await libraryChat(message, priorHistory);
      const reply = result.reply || "I came back empty.";
      setChatTurnText(pending, reply);
      chatHistory.push({ role: "viber", text: reply });
      renderChatSide(result);
    } catch (err) {
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
  async function runIngest(): Promise<void> {
    state = setFolder(state, folderInput.value.trim() || state.folder);
    $("vmx-lib-loglist").innerHTML = "";
    setProgress(0, DEV_FALLBACK.embedLog.length, 0, "");

    const accepted = await libraryEmbedFolder(state.folder, state.strategy);
    if (accepted) return; // bridge live — events take over via the listeners below

    // dev replay — step through the captured log on a timer
    const log = DEV_FALLBACK.embedLog;
    const total = log.length;
    let i = 0;
    const tick = (): void => {
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
    try {
      if (state.mode === "search") await runSearch();
      else if (state.mode === "similar") await runSimilar();
      else if (state.mode === "curate") await runCurate();
      else if (state.mode === "build") await runBuildSet();
      else if (state.mode === "chat") await runChat();
      else {
        await runIngest();
        return; // ingest manages its own busy lifecycle (events or replay)
      }
    } catch (err) {
      // A REAL backend error (empty cache, missing key, bad strategy) — show it
      // honestly instead of masking it with fake data (anti-slop). The ingest
      // path lands here too on a real bridge error, so we must release its
      // busy/disabled lifecycle here rather than leaving the button wedged.
      // eslint-disable-next-line no-console
      console.error("[vmx-lib] run failed:", err);
      renderError(err);
      if (state.mode === "ingest") {
        busy = false;
        runBtn.disabled = false;
      }
    } finally {
      if (state.mode !== "ingest") {
        busy = false;
        runBtn.disabled = false;
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

  document.querySelectorAll<HTMLElement>(".vmx-lib-modeswitch button").forEach((b) => {
    b.addEventListener("click", () => {
      const previousMode = state.mode;
      const mode = (b.dataset.mode ?? "search") as LibraryMode;
      state = setMode(state, mode);
      applyModeVisibility();
      // The set-notes block is shared by curate + build; only clear it when
      // leaving BOTH so a fresh build/curate keeps its own working state.
      if (mode !== "curate" && mode !== "build") clearRationale();
      if ((mode === "curate" || mode === "build") && previousMode !== mode) {
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
        const wire = c.dataset.strategy === "mean" ? "mean_excerpt" : "cue_anchored";
        c.setAttribute("aria-pressed", String(wire === strat));
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

  // ingest progress from the real bridge (no-op listeners in dev)
  void onEmbedProgress((p: EmbedProgress) => {
    appendLog(p.status, p.filename, p.cost_eur);
    setProgress(p.n, p.total, p.cost_eur, p.filename.replace(/\.[a-z0-9]+$/i, ""));
  });
  void onEmbedDone((d: EmbedDone) => {
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
        const audio = payload.paths.find((p) => /\.(wav|mp3|m4a|flac)$/i.test(p));
        if (audio) onFile(audio);
      }
    });
  } catch {
    // Tauri webview API unavailable — drop wiring skipped.
  }
}

// Auto-mount when loaded as the library.html entry (skipped under vitest,
// which imports the pure modules directly).
if (typeof document !== "undefined" && document.getElementById("vmx-lib-runbtn")) {
  mountLibrary();
}
