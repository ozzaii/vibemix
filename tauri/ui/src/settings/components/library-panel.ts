/* Library panel with drag-drop / native-pick folder embedding.
 *
 * Pure vanilla TypeScript — no framework, no template engine. Mounts under the LIBRARY group in
 * SettingsDrawer alongside the Plan 28-07 staleness banner.
 *
 * Bridge contract:
 *   invoke: library_embed_folder { path, strategy }
 *   inbound: library://embed-progress { n, total, status, filename, cost_eur }
 *   inbound: library://embed-done { embedded, skipped, failed, total, cost_eur }
 *
 * Drag-drop dedupe (Tauri Issue #14134): the same physical drop fires the
 * onDragDropEvent listener TWICE — once from the OS and once from the
 * webview. We dedupe by `event.id` per the Tauri 2 docs.
 */

import { emitIpc } from "../../ipc/client.js";
import {
  libraryEmbedFolder,
  onEmbedDone,
  onEmbedProgress,
  type EmbedDone,
  type EmbedProgress,
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
         aria-label="Drop a music folder here">
      Drop a music folder here,
      or click <button type="button" class="vmx-library-pick-folder-btn">Choose folder</button>
    </div>
    <div class="vmx-library-progress hidden">
      <div class="vmx-library-progress-track" aria-hidden="true">
        <div class="vmx-library-progress-fill"></div>
      </div>
      <div class="vmx-library-progress-label">· / ·</div>
    </div>
    <div class="vmx-library-filelog" aria-live="polite"></div>
    <div class="vmx-library-status" aria-live="polite"></div>
  `;

  const drop = root.querySelector(".vmx-library-droptarget") as HTMLElement;
  const pickFolderBtn = root.querySelector(
    ".vmx-library-pick-folder-btn",
  ) as HTMLButtonElement;
  const progress = root.querySelector(".vmx-library-progress") as HTMLElement;
  const fill = root.querySelector(
    ".vmx-library-progress-fill",
  ) as HTMLElement;
  const label = root.querySelector(
    ".vmx-library-progress-label",
  ) as HTMLElement;
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
  let unsubDone: (() => void) | null = null;
  let unlistenDrop: (() => void) | null = null;

  function showProgress(): void {
    if (disposed) return;
    progress.classList.remove("hidden");
    status.textContent = "";
  }
  function hideProgress(): void {
    if (disposed) return;
    progress.classList.add("hidden");
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
  function showEmbedProgress(p: EmbedProgress): void {
    if (!activeJob || disposed) return;
    const pct = p.total > 0 ? (p.n / p.total) * 100 : 0;
    fill.style.width = `${pct.toFixed(1)}%`;
    label.textContent = `${p.n} / ${p.total} · €${p.cost_eur.toFixed(4)}`;
    const mark = p.status === "err" ? "error" : p.status === "skip" ? "cached" : "indexed";
    appendFileLog(`${mark}: ${p.filename}`);
    setStatus(p.filename);
  }
  function showEmbedDone(d: EmbedDone): void {
    if (!activeJob || disposed) return;
    activeJob = false;
    fill.style.width = "100%";
    label.textContent = `${d.total} / ${d.total} · €${d.cost_eur.toFixed(4)}`;
    hideProgress();
    setStatus(
      `${d.embedded} embedded, ${d.skipped} cached, ${d.failed} failed`,
    );
    opts.onImportComplete?.({
      total: d.total,
      done: d.total,
      cache_hits: d.skipped,
    });
  }

  async function ensureProgressSubscription(): Promise<void> {
    if (!unsubProgress) {
      const unsub = await onEmbedProgress(showEmbedProgress);
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
    if (!unsubDone) {
      const unsub = await onEmbedDone(showEmbedDone);
      const disposeDone = unsub as unknown as () => void;
      if (disposed) {
        try {
          disposeDone();
        } catch {
          /* ignore */
        }
      } else {
        unsubDone = disposeDone;
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
    if (looksLikeFilePath(path)) {
      setStatus("Choose a music folder. Catalog import was removed.");
      return;
    }
    await beginLibraryJob(
      async () => {
        const accepted = await libraryEmbedFolder(path, "mean_excerpt");
        if (!accepted) {
          activeJob = false;
          hideProgress();
          setStatus("Folder indexing needs the desktop bridge.");
        }
      },
      "Folder indexing failed",
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

  function looksLikeFilePath(path: string): boolean {
    const leaf = path.split(/[\\/]/).pop() ?? "";
    return /\.[^./\\]+$/.test(leaf);
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

  pickFolderBtn.addEventListener("click", () => {
    void chooseLibrarySource();
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
        const librarySource = payload.paths.find((p) => !looksLikeFilePath(p));
        if (librarySource) {
          void beginImport(librarySource);
        } else {
          setStatus("Drop a music folder, not a single audio file.");
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
      try {
        unsubDone?.();
      } catch {
        /* ignore */
      }
      seenEventIds.clear();
    },
  };
}
