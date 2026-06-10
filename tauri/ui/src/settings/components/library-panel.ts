/* Library panel with drag-drop / native-pick folder embedding.
 *
 * Pure vanilla TypeScript — no framework, no template engine. Mounts under the LIBRARY group in
 * SettingsDrawer alongside the Plan 28-07 staleness banner.
 *
 * Bridge contract:
 *   outbound: ipc.library.import { path, schema_version }
 *   outbound: ipc.library.import_cancel { schema_version }
 *   inbound: ipc.library.import_progress { total, done, current_track_name, cache_hits, cancelled }
 *
 * Drag-drop dedupe (Tauri Issue #14134): the same physical drop fires the
 * onDragDropEvent listener TWICE — once from the OS and once from the
 * webview. We dedupe by `event.id` per the Tauri 2 docs.
 */

import { emitIpc } from "../../ipc/client.js";
import {
  libraryCancelImport,
  libraryImport,
  onLibraryImportProgress,
  type LibraryImportProgress,
} from "../../library/api.js";
import { registerStyle } from "../../session/components/_style-registry.js";

export interface LibraryPanelHandle {
  element: HTMLElement;
  beginImport(path: string): Promise<void>;
  beginFolderReindex(): Promise<void>;
  dispose(): void;
}

interface LibraryPanelOptions {
  onImportComplete?: (info: {
    total: number;
    done: number;
    cache_hits: number;
  }) => void;
}

const CSS = `
  .vmx-library-panel {
    display: grid;
    gap: var(--sp-3);
    min-width: 0;
    font-family: var(--type-body);
  }
  .vmx-library-panel__hero {
    position: relative;
    overflow: hidden;
    padding: var(--sp-4);
    border-radius: var(--rad-md);
    background:
      radial-gradient(circle at 16% 0%, var(--brand-12), transparent 36%),
      linear-gradient(180deg, rgba(255, 251, 244, 0.024), transparent 52%, rgba(0, 0, 0, 0.18)),
      var(--glass-2);
    box-shadow:
      var(--chrome-highlight),
      inset 0 -18px 34px rgba(0, 0, 0, 0.20),
      var(--shadow-raised);
  }
  .vmx-library-panel__eyebrow {
    margin-bottom: var(--sp-2);
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--brand);
    text-shadow: 0 0 8px var(--brand-22);
  }
  .vmx-library-panel__title {
    margin: 0;
    font-family: var(--type-serif);
    font-size: 34px;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: 0;
    color: var(--silk);
  }
  .vmx-library-panel__copy {
    margin: var(--sp-2) 0 0;
    max-width: 42ch;
    color: var(--silk-65);
    font-size: 12px;
    line-height: 1.45;
  }
  .vmx-library-formats {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-1);
    margin-top: var(--sp-3);
  }
  .vmx-library-format-chip {
    min-height: 22px;
    display: inline-flex;
    align-items: center;
    padding: 0 var(--sp-2);
    border-radius: var(--rad-sm);
    background: var(--void-8);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    color: var(--silk-65);
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .vmx-library-droptarget {
    position: relative;
    display: grid;
    grid-template-columns: 52px minmax(0, 1fr);
    gap: var(--sp-3);
    align-items: center;
    min-width: 0;
    padding: var(--sp-3);
    border: 0;
    border-radius: var(--rad-md);
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.020), transparent 54%, rgba(0, 0, 0, 0.22)),
      var(--void-10);
    box-shadow:
      var(--chrome-highlight),
      inset 0 -18px 36px rgba(0, 0, 0, 0.24),
      var(--shadow-raised);
    transition:
      background var(--motion-transition) var(--ease-brand),
      box-shadow var(--motion-transition) var(--ease-brand),
      transform var(--motion-transition) var(--ease-brand);
  }
  .vmx-library-droptarget.dragging,
  .vmx-library-droptarget:hover {
    background:
      linear-gradient(180deg, var(--brand-06), transparent 56%, rgba(0, 0, 0, 0.22)),
      var(--void-10);
    box-shadow:
      var(--chrome-highlight),
      inset 0 0 24px var(--brand-06),
      inset 0 -18px 36px rgba(0, 0, 0, 0.24),
      var(--shadow-float);
  }
  .vmx-library-droptarget__badge {
    width: 52px;
    height: 52px;
    display: grid;
    place-items: center;
    border-radius: var(--rad-md);
    background:
      radial-gradient(circle at 34% 24%, var(--brand-22), transparent 36%),
      linear-gradient(145deg, var(--glass-3), var(--void-8));
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.055),
      inset 0 -10px 20px rgba(0, 0, 0, 0.34);
    color: var(--silk);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.06em;
  }
  .vmx-library-droptarget__headline {
    color: var(--silk);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.10em;
    line-height: 1.25;
    text-transform: uppercase;
  }
  .vmx-library-droptarget__hint {
    margin-top: var(--sp-1);
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1.35;
  }
  .vmx-library-actions {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--sp-2);
  }
  .vmx-library-panel :is(.vmx-library-pick-folder-btn, .vmx-library-pick-catalog-btn, .vmx-library-cancel-btn) {
    min-height: 34px;
    border: 0;
    border-radius: var(--rad-sm);
    background:
      linear-gradient(180deg, var(--brand-16), var(--brand-04)),
      var(--glass-3);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.065),
      inset 0 -1px 0 rgba(0, 0, 0, 0.42),
      var(--glow-faint);
    color: var(--brand-glow);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    cursor: pointer;
    transition:
      color var(--motion-snap) var(--ease-brand),
      background var(--motion-snap) var(--ease-brand),
      box-shadow var(--motion-snap) var(--ease-brand),
      transform var(--motion-snap) var(--ease-brand);
  }
  .vmx-library-panel :is(.vmx-library-pick-folder-btn, .vmx-library-pick-catalog-btn, .vmx-library-cancel-btn):hover,
  .vmx-library-panel :is(.vmx-library-pick-folder-btn, .vmx-library-pick-catalog-btn, .vmx-library-cancel-btn):focus-visible {
    color: var(--silk);
    background:
      linear-gradient(180deg, var(--brand-22), var(--brand-06)),
      var(--glass-3);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.085),
      inset 0 -1px 0 rgba(0, 0, 0, 0.42),
      var(--glow-soft);
  }
  .vmx-library-progress {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--sp-2);
    align-items: center;
    padding: var(--sp-3);
    border-radius: var(--rad-md);
    background: var(--glass-2);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.035),
      inset 0 -14px 26px rgba(0, 0, 0, 0.20);
  }
  .vmx-library-progress.hidden {
    display: none;
  }
  .vmx-library-progress-track {
    grid-column: 1 / -1;
    height: 6px;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.36);
    box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.5);
  }
  .vmx-library-progress-fill {
    width: 0%;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--brand-40), var(--brand));
    box-shadow: 0 0 14px var(--brand-22);
    transition: width var(--motion-transition) var(--ease-brand);
  }
  .vmx-library-progress-label,
  .vmx-library-status,
  .vmx-library-filelog-row {
    color: var(--silk-65);
    font-size: 11px;
    line-height: 1.35;
  }
  .vmx-library-filelog {
    display: grid;
    gap: var(--sp-1);
  }
  .vmx-library-filelog-row {
    padding: 7px var(--sp-2);
    border-radius: var(--rad-sm);
    background: rgba(0, 0, 0, 0.18);
    font-family: var(--type-mono);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-library-status:not(:empty) {
    padding: 8px var(--sp-2);
    border-radius: var(--rad-sm);
    background: rgba(0, 0, 0, 0.18);
    box-shadow: inset 0 1px 0 rgba(255, 251, 244, 0.025);
  }
`;

registerStyle("vmx-library-panel", CSS);

// Module-scope import-job memory. The drawer rebuilds its WHOLE body on any
// settings-UI state change (close/reopen, recordings push, hotkey capture),
// disposing this panel mid-import while the backend keeps embedding — the
// fresh mount used to show the idle "Choose folder" state with no progress
// and no Cancel, and re-clicking import got the silent already-running
// rejection. A new mount rehydrates from here instead.
let moduleJobActive = false;
let moduleLastProgress: LibraryImportProgress | null = null;

export async function renderLibraryPanel(
  opts: LibraryPanelOptions = {},
): Promise<LibraryPanelHandle> {
  const root = document.createElement("section");
  root.className = "vmx-library-panel";
  root.dataset.state = "idle";
  root.innerHTML = `
    <div class="vmx-library-panel__hero">
      <div class="vmx-library-panel__eyebrow">local library</div>
      <h3 class="vmx-library-panel__title">Feed Viber real tracks</h3>
      <p class="vmx-library-panel__copy">
        Index the music you own so set prep, cue export, and Viber choices stay grounded.
      </p>
      <div class="vmx-library-formats" aria-label="supported library formats">
        <span class="vmx-library-format-chip">folders</span>
        <span class="vmx-library-format-chip">rekordbox</span>
        <span class="vmx-library-format-chip">traktor</span>
        <span class="vmx-library-format-chip">engine</span>
      </div>
    </div>
    <div class="vmx-library-droptarget" role="region"
         aria-label="Drop a music folder or DJ catalog here">
      <div class="vmx-library-droptarget__badge" aria-hidden="true">m.db</div>
      <div class="vmx-library-droptarget__body">
        <div class="vmx-library-droptarget__headline">Drop music folder or DJ catalog</div>
        <div class="vmx-library-droptarget__hint">
          Rekordbox XML, Traktor NML, VirtualDJ XML, Engine DB, or a plain music folder.
        </div>
      </div>
      <div class="vmx-library-actions">
        <button type="button" class="vmx-library-pick-folder-btn">Choose folder</button>
        <button type="button" class="vmx-library-pick-catalog-btn">Choose catalog</button>
      </div>
    </div>
    <div class="vmx-library-progress hidden">
      <div class="vmx-library-progress-track" aria-hidden="true">
        <div class="vmx-library-progress-fill"></div>
      </div>
      <div class="vmx-library-progress-label">· / ·</div>
      <button type="button" class="vmx-library-cancel-btn" hidden>Cancel</button>
    </div>
    <div class="vmx-library-filelog" aria-live="polite"></div>
    <div class="vmx-library-status" aria-live="polite"></div>
  `;

  const drop = root.querySelector(".vmx-library-droptarget") as HTMLElement;
  const pickFolderBtn = root.querySelector(
    ".vmx-library-pick-folder-btn",
  ) as HTMLButtonElement;
  const pickCatalogBtn = root.querySelector(
    ".vmx-library-pick-catalog-btn",
  ) as HTMLButtonElement;
  const progress = root.querySelector(".vmx-library-progress") as HTMLElement;
  const fill = root.querySelector(
    ".vmx-library-progress-fill",
  ) as HTMLElement;
  const label = root.querySelector(
    ".vmx-library-progress-label",
  ) as HTMLElement;
  const cancelBtn = root.querySelector(".vmx-library-cancel-btn") as HTMLButtonElement;
  const fileLog = root.querySelector(".vmx-library-filelog") as HTMLElement;
  const status = root.querySelector(".vmx-library-status") as HTMLElement;

  let disposed = false;
  let activeJob = false;
  const seenEventIds = new Set<number>();
  // Tauri Issue #14134 dedupe: cap to last N ids — Set iteration is
  // insertion-order so dropping `.values().next()` evicts the oldest.
  // Long-lived Settings drawer (multi-week session) would otherwise leak.
  const SEEN_CAP = 64;
  function rememberId(id: number): boolean {
    if (seenEventIds.has(id)) return false;
    seenEventIds.add(id);
    if (seenEventIds.size > SEEN_CAP) {
      const oldest = seenEventIds.values().next().value;
      if (oldest !== undefined) seenEventIds.delete(oldest);
    }
    return true;
  }
  let unsubProgress: (() => void) | null = null;
  let unlistenDrop: (() => void) | null = null;

  function showProgress(): void {
    if (disposed) return;
    root.dataset.state = "indexing";
    progress.classList.remove("hidden");
    cancelBtn.hidden = false;
    cancelBtn.disabled = false;
    status.textContent = "";
  }
  function hideProgress(): void {
    if (disposed) return;
    root.dataset.state = "idle";
    progress.classList.add("hidden");
    cancelBtn.hidden = true;
    cancelBtn.disabled = false;
  }
  function setStatus(text: string): void {
    if (disposed) return;
    status.textContent = text;
  }
  function appendFileLog(text: string): void {
    if (disposed) return;
    const row = document.createElement("div");
    row.className = "vmx-library-filelog-row";
    row.textContent = text;
    fileLog.prepend(row);
    while (fileLog.childElementCount > 5) {
      fileLog.lastElementChild?.remove();
    }
  }
  function sourceProgressDone(p: LibraryImportProgress): boolean {
    if (p.cancelled) return true;
    // failure_reason rides ONLY the terminal frame (api.ts contract) — it
    // covers the sidecar's exception/rejection frames, which arrive with
    // total=0 and would otherwise never settle the progress UI.
    if ((p.failure_reason ?? "").trim() !== "") return true;
    if (p.total <= 0) return false;
    return p.done >= p.total || p.current_track_name.trim() === "";
  }
  function sourceProgressNote(p: LibraryImportProgress): string {
    if (p.cancelled) return "import cancelled";
    const count = p.total > 0 ? `${Math.min(p.done, p.total)} / ${p.total}` : String(p.done);
    const cache = p.cache_hits > 0 ? ` · ${p.cache_hits} cached` : "";
    const name = p.current_track_name.trim();
    return name ? `${count} · ${name}${cache}` : `${count}${cache}`;
  }
  function sourceDoneNote(p: LibraryImportProgress): string {
    if (p.cancelled) return "Import cancelled";
    const processed = p.total > 0 ? p.total : p.done;
    // The sidecar deliberately carries failed/failure_reason on the terminal
    // frame so an all-failed run can't walk the bar to 100% and read as
    // success (the packaged-ffprobe wipeout shape). Honor it here — "N
    // processed" with zero tracks indexed is the exact lie that guard exists
    // to prevent.
    const failed = p.failed ?? 0;
    const reason = (p.failure_reason ?? "").trim();
    // total=0 failure frame = the run died before counting files (exception
    // or rejected re-index) — name the reason, never "Import finished".
    if (failed > 0 && processed === 0) {
      return reason ? `Import failed (${reason})` : "Import failed";
    }
    if (failed > 0 && failed >= processed && processed > 0) {
      return reason
        ? `Couldn't index any of the ${processed} files (${reason})`
        : `Couldn't index any of the ${processed} files`;
    }
    const parts: string[] = [];
    if (processed > 0) parts.push(`${processed - failed} indexed`);
    if (failed > 0) parts.push(`${failed} skipped${reason ? ` (${reason})` : ""}`);
    if (p.cache_hits > 0) parts.push(`${p.cache_hits} cached`);
    return parts.length > 0 ? parts.join(", ") : "Import finished";
  }
  function showImportProgress(p: LibraryImportProgress): void {
    if (!activeJob || disposed) return;
    moduleLastProgress = p;
    const pct = p.total > 0 ? (Math.min(p.done, p.total) / p.total) * 100 : 0;
    fill.style.width = `${pct.toFixed(1)}%`;
    label.textContent = sourceProgressNote(p);
    if (p.current_track_name.trim()) appendFileLog(`indexed: ${p.current_track_name}`);
    setStatus(sourceProgressNote(p));
    if (!sourceProgressDone(p)) return;
    activeJob = false;
    moduleJobActive = false;
    moduleLastProgress = null;
    fill.style.width = p.cancelled ? fill.style.width : "100%";
    hideProgress();
    setStatus(sourceDoneNote(p));
    opts.onImportComplete?.({
      total: p.total,
      done: p.done,
      cache_hits: p.cache_hits,
    });
  }

  async function ensureProgressSubscription(): Promise<void> {
    if (!unsubProgress) {
      const unsub = await onLibraryImportProgress(showImportProgress);
      const disposeProgress = unsub as unknown as () => void;
      if (disposed) {
        try {
          disposeProgress();
        } catch {
          /* ignore */
        }
      } else {
        unsubProgress = disposeProgress;
      }
    }
  }

  async function beginLibraryJob(
    start: () => Promise<void>,
    failureLabel: string,
  ): Promise<void> {
    if (disposed) return;
    showProgress();
    fill.style.width = "0%";
    label.textContent = "Preparing folder…";
    fileLog.replaceChildren();
    activeJob = true;
    moduleJobActive = true;
    moduleLastProgress = null;
    await ensureProgressSubscription();
    try {
      await start();
    } catch (e) {
      activeJob = false;
      moduleJobActive = false;
      hideProgress();
      setStatus(`${failureLabel}: ${(e as Error).message ?? e}`);
    }
  }

  async function beginImport(path: string): Promise<void> {
    if (looksLikeAudioFilePath(path)) {
      setStatus("Drop a music folder or DJ catalog, not a single audio file.");
      return;
    }
    if (looksLikeUnsupportedFilePath(path)) {
      setStatus("Choose a folder, Rekordbox XML, Traktor NML, VirtualDJ XML, or Engine DB.");
      return;
    }
    await beginLibraryJob(
      async () => {
        const accepted = await libraryImport(path);
        if (!accepted) {
          activeJob = false;
          hideProgress();
          setStatus("Library import needs the desktop bridge.");
        }
      },
      "Library import failed",
    );
  }

  async function beginFolderReindex(): Promise<void> {
    await beginLibraryJob(
      () =>
        emitIpc("ipc.library.staleness_action", {
          action: "reindex_folder",
          schema_version: "1",
        }),
      "Re-index failed",
    );
  }

  function looksLikeAudioFilePath(path: string): boolean {
    return /\.(mp3|m4a|wav|flac|aac|aiff?)$/i.test(path);
  }

  function looksLikeSupportedCatalogPath(path: string): boolean {
    const leaf = path.split(/[\\/]/).pop() ?? "";
    const lower = leaf.toLowerCase();
    return (
      lower === "database v2" ||
      lower === "database.xml" ||
      lower === "m.db" ||
      /\.(xml|nml|db)$/i.test(leaf)
    );
  }

  function looksLikeUnsupportedFilePath(path: string): boolean {
    const leaf = path.split(/[\\/]/).pop() ?? "";
    return /\.[^./\\]+$/.test(leaf) && !looksLikeSupportedCatalogPath(path);
  }

  function firstDialogPath(selection: unknown): string | null {
    if (typeof selection === "string" && selection.length > 0) return selection;
    if (Array.isArray(selection)) {
      const first = selection.find(
        (item): item is string => typeof item === "string" && item.length > 0,
      );
      return first ?? null;
    }
    return null;
  }

  async function chooseLibrarySource(): Promise<void> {
    if (disposed) return;
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selection = await open({
        title: "Choose music folder",
        directory: true,
        multiple: false,
      });
      const sourcePath = firstDialogPath(selection);
      if (!sourcePath) {
        setStatus("No music folder selected.");
        return;
      }
      await beginImport(sourcePath);
    } catch (e) {
      const message = (e as Error).message ?? String(e);
      setStatus(`File picker unavailable: ${message}`);
    }
  }

  async function chooseLibraryCatalog(): Promise<void> {
    if (disposed) return;
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selection = await open({
        title: "Choose DJ library catalog",
        directory: false,
        multiple: false,
        filters: [
          {
            name: "DJ library catalogs",
            extensions: ["xml", "nml", "db"],
          },
        ],
      });
      const sourcePath = firstDialogPath(selection);
      if (!sourcePath) {
        setStatus("No DJ library catalog selected.");
        return;
      }
      await beginImport(sourcePath);
    } catch (e) {
      const message = (e as Error).message ?? String(e);
      setStatus(`File picker unavailable: ${message}`);
    }
  }

  pickFolderBtn.addEventListener("click", () => {
    void chooseLibrarySource();
  });
  pickCatalogBtn.addEventListener("click", () => {
    void chooseLibraryCatalog();
  });
  cancelBtn.addEventListener("click", () => {
    if (!activeJob) return;
    cancelBtn.disabled = true;
    setStatus("Cancelling import…");
    void libraryCancelImport().catch((e) => {
      cancelBtn.disabled = false;
      const message = (e as Error).message ?? String(e);
      setStatus(`Cancel failed: ${message}`);
    });
  });

  // Drag-drop wiring — Tauri webview API. The dedupe via seenEventIds is
  // required for Tauri Issue #14134 (same drop fires twice).
  try {
    const { getCurrentWebview } = await import("@tauri-apps/api/webview");
    const webview = getCurrentWebview();
    const off = await webview.onDragDropEvent((event) => {
      if (disposed) return;
      const payload = event.payload as
        | { type: "enter" | "over"; paths: string[] }
        | { type: "leave" }
        | { type: "drop"; paths: string[] };
      if (payload.type === "enter" || payload.type === "over") {
        drop.classList.add("dragging");
        return;
      }
      if (payload.type === "leave") {
        drop.classList.remove("dragging");
        return;
      }
      if (payload.type === "drop") {
        drop.classList.remove("dragging");
        const eventId = (event as unknown as { id: number }).id;
        if (typeof eventId === "number") {
          if (!rememberId(eventId)) {
            return;
          }
        }
        const librarySource = payload.paths.find(
          (p) =>
            !looksLikeAudioFilePath(p) &&
            !looksLikeUnsupportedFilePath(p),
        );
        if (librarySource) {
          void beginImport(librarySource);
        } else {
          setStatus("Drop a music folder or DJ catalog, not a single audio file.");
        }
      }
    });
    const disposeDrop = off as unknown as () => void;
    if (disposed) {
      try {
        disposeDrop();
      } catch {
        /* ignore */
      }
    } else {
      unlistenDrop = disposeDrop;
    }
  } catch (err) {
    // Tauri webview API unavailable (jsdom test env) — drop wiring skipped.
  }

  // Rehydrate a job that survived a drawer rebuild: re-arm the progress UI
  // (incl. Cancel — import_cancel is stateless) and replay the last frame so
  // the bar paints instantly instead of sitting empty until the next tick.
  if (moduleJobActive) {
    activeJob = true;
    showProgress();
    void ensureProgressSubscription();
    if (moduleLastProgress) {
      showImportProgress(moduleLastProgress);
    } else {
      label.textContent = "Preparing folder…";
    }
  }

  return {
    element: root,
    beginImport,
    beginFolderReindex,
    dispose(): void {
      disposed = true;
      try {
        unlistenDrop?.();
      } catch {
        /* ignore */
      }
      try {
        unsubProgress?.();
      } catch {
        /* ignore */
      }
      seenEventIds.clear();
    },
  };
}
