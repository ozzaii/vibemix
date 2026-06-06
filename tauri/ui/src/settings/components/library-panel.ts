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

export async function renderLibraryPanel(
  opts: LibraryPanelOptions = {},
): Promise<LibraryPanelHandle> {
  const root = document.createElement("section");
  root.className = "vmx-library-panel";
  root.innerHTML = `
    <div class="vmx-library-droptarget" role="region"
         aria-label="Drop a music folder or DJ catalog here">
      Drop music folder or DJ catalog,
      then <button type="button" class="vmx-library-pick-folder-btn">Choose folder</button>
      or <button type="button" class="vmx-library-pick-catalog-btn">Choose catalog</button>
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
    progress.classList.remove("hidden");
    cancelBtn.hidden = false;
    cancelBtn.disabled = false;
    status.textContent = "";
  }
  function hideProgress(): void {
    if (disposed) return;
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
    const parts: string[] = [];
    if (processed > 0) parts.push(`${processed} processed`);
    if (p.cache_hits > 0) parts.push(`${p.cache_hits} cached`);
    return parts.length > 0 ? parts.join(", ") : "Import finished";
  }
  function showImportProgress(p: LibraryImportProgress): void {
    if (!activeJob || disposed) return;
    const pct = p.total > 0 ? (Math.min(p.done, p.total) / p.total) * 100 : 0;
    fill.style.width = `${pct.toFixed(1)}%`;
    label.textContent = sourceProgressNote(p);
    if (p.current_track_name.trim()) appendFileLog(`indexed: ${p.current_track_name}`);
    setStatus(sourceProgressNote(p));
    if (!sourceProgressDone(p)) return;
    activeJob = false;
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
    await ensureProgressSubscription();
    try {
      await start();
    } catch (e) {
      activeJob = false;
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
