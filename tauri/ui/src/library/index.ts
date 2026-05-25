// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — library window entry point.
 *
 * Mounts into #app of library.html (the 5th Tauri webview, opened by the Rust
 * bridge's `open_library_window` command). Thin DOM renderer over the pure
 * state-machine.ts; all backend I/O goes through api.ts (typed invoke/event
 * client with a dev fallback so this window renders fully in plain `vite` dev).
 *
 * Three modes (mode switch in the left console):
 *   - search   text query → librarySearch → results + scope
 *   - similar  seed (drop a file or keep the current) → librarySimilar → results + scope
 *   - ingest   folder + strategy → libraryEmbedFolder → progress bar + live log + running €
 *
 * Wire-vs-dev: every api.ts call falls back to the real 2026-05-25 subset-run
 * sample when `invoke()` is unavailable or throws, so the surface is demoable
 * before the Rust bridge lands. The ingest replay below drives the same bar +
 * log from DEV_FALLBACK.embedLog when the bridge isn't there.
 */

import {
  DEV_FALLBACK,
  libraryEmbedFolder,
  librarySearch,
  librarySimilar,
  libraryStats,
  onEmbedDone,
  onEmbedProgress,
  type EmbedDone,
  type EmbedProgress,
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
  setFolder,
  setMode,
  setQuery,
  setSeed,
  setStrategy,
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

function renderStats(stats: LibraryStats): void {
  $("vmx-lib-stat-indexed").innerHTML = `${stats.indexed}<small> / 1547</small>`;
  $("vmx-lib-stat-backend").textContent = stats.backend;
  $("vmx-lib-stat-spent").textContent = `€${stats.spent_eur.toFixed(2)}`;
  $("vmx-lib-stat-failed").textContent = String(stats.failed);
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

// ── Bootstrap ───────────────────────────────────────────────────────────────

export function mountLibrary(): void {
  let state: LibraryState = initialLibraryState;
  let busy = false;

  const qInput = $("vmx-lib-q") as HTMLInputElement;
  const folderInput = $("vmx-lib-folder") as HTMLInputElement;
  const runBtn = $("vmx-lib-runbtn") as HTMLButtonElement;
  const echoEl = $("vmx-lib-echo");
  const qlabelEl = $("vmx-lib-qlabel");
  const seedNameEl = $("vmx-lib-seed-name");

  // restore initial field values from state
  qInput.value = state.query;
  folderInput.value = state.folder;
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
    runBtn.textContent = runLabel(state.mode);
    echoEl.textContent = echoText(state);
  }

  async function refreshStats(): Promise<void> {
    renderStats(await libraryStats());
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
      else {
        await runIngest();
        return; // ingest manages its own busy lifecycle (events or replay)
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("[vmx-lib] run failed:", err);
    } finally {
      if (state.mode !== "ingest") {
        busy = false;
        runBtn.disabled = false;
      }
    }
  }

  // ── event wiring ───────────────────────────────────────────────────────────

  runBtn.addEventListener("click", () => void run());

  qInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.mode === "search") void run();
  });
  folderInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.mode === "ingest") void run();
  });

  document.querySelectorAll<HTMLElement>(".vmx-lib-modeswitch button").forEach((b) => {
    b.addEventListener("click", () => {
      const mode = (b.dataset.mode ?? "search") as LibraryMode;
      state = setMode(state, mode);
      applyModeVisibility();
      if (mode === "ingest") {
        // show last-known progress shape, don't auto-run
        $("vmx-lib-loglist").innerHTML = "";
        setProgress(0, DEV_FALLBACK.embedLog.length, 0, "");
      } else {
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

  // strategy chips (ingest mode)
  document.querySelectorAll<HTMLElement>("[data-strategy]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const strat = chip.dataset.strategy === "mean" ? "mean" : "cue-anchored";
      state = setStrategy(state, strat);
      document.querySelectorAll<HTMLElement>("[data-strategy]").forEach((c) => {
        c.setAttribute("aria-pressed", String(c.dataset.strategy === strat));
      });
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

  // initial paint
  applyModeVisibility();
  void refreshStats();
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
