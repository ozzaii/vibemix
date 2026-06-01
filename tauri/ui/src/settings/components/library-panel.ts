/* Phase 28 Plan 06 — Library panel with drag-drop XML import.
 *
 * Pure vanilla TypeScript — no framework, no template engine. Mounts under the LIBRARY group in
 * SettingsDrawer alongside the Plan 28-07 staleness banner.
 *
 * IPC contract (Plan 28-09):
 *   outbound: ipc.library.import { path }
 *   outbound: ipc.library.import_cancel {}
 *   inbound:  ipc.library.import_progress { total, done, current_track_name,
 *                                           cache_hits, cancelled, schema_version }
 *
 * Drag-drop dedupe (Tauri Issue #14134): the same physical drop fires the
 * onDragDropEvent listener TWICE — once from the OS and once from the
 * webview. We dedupe by `event.id` per the Tauri 2 docs.
 */

import { emitIpc, subscribeIpc } from "../../ipc/client.js";
import type { LibraryImportProgress } from "../../ipc/messages.js";

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
         aria-label="Drop Rekordbox XML here">
      Drop Rekordbox XML here, or click <button type="button"
        class="vmx-library-pick-btn">Choose file</button>
    </div>
    <div class="vmx-library-progress hidden">
      <div class="vmx-library-progress-track" aria-hidden="true">
        <div class="vmx-library-progress-fill"></div>
      </div>
      <div class="vmx-library-progress-label">· / ·</div>
      <button type="button" class="vmx-library-cancel-btn">Cancel</button>
    </div>
    <div class="vmx-library-status" aria-live="polite"></div>
  `;

  const drop = root.querySelector(".vmx-library-droptarget") as HTMLElement;
  const pickBtn = root.querySelector(".vmx-library-pick-btn") as HTMLButtonElement;
  const progress = root.querySelector(".vmx-library-progress") as HTMLElement;
  const fill = root.querySelector(
    ".vmx-library-progress-fill",
  ) as HTMLElement;
  const label = root.querySelector(
    ".vmx-library-progress-label",
  ) as HTMLElement;
  const cancelBtn = root.querySelector(
    ".vmx-library-cancel-btn",
  ) as HTMLButtonElement;
  const status = root.querySelector(".vmx-library-status") as HTMLElement;

  let disposed = false;
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

  async function ensureProgressSubscription(): Promise<void> {
    if (!unsubProgress) {
      const unsub = await subscribeIpc<LibraryImportProgress>(
        "ipc.library.import_progress",
        (msg) => {
          if (disposed) return;
          const p = msg.payload;
          const pct = p.total > 0 ? (p.done / p.total) * 100 : 0;
          fill.style.width = `${pct.toFixed(1)}%`;
          label.textContent = `${p.done} / ${p.total} (${p.cache_hits} cached)`;
          if (p.current_track_name) {
            setStatus(p.current_track_name);
          }
          if (p.cancelled) {
            hideProgress();
            setStatus(`Cancelled at ${p.done}/${p.total}`);
          } else if (p.done >= p.total) {
            hideProgress();
            setStatus(
              `${p.total} tracks indexed (${p.cache_hits} from cache)`,
            );
            opts.onImportComplete?.({
              total: p.total,
              done: p.done,
              cache_hits: p.cache_hits,
            });
          }
        },
      );
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
    label.textContent = "Loading…";
    await ensureProgressSubscription();
    try {
      await start();
    } catch (e) {
      hideProgress();
      setStatus(`${failureLabel}: ${(e as Error).message ?? e}`);
    }
  }

  async function beginImport(path: string): Promise<void> {
    await beginLibraryJob(
      () => emitIpc("ipc.library.import", { path, schema_version: "1" }),
      "Import failed",
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

  cancelBtn.addEventListener("click", () => {
    if (disposed) return;
    void emitIpc("ipc.library.import_cancel", { schema_version: "1" });
  });

  pickBtn.addEventListener("click", () => {
    if (disposed) return;
    // Drag-drop is the primary UX. A click-to-pick fallback requires
    // tauri-plugin-dialog which isn't bundled in v1 — show a prompt to
    // drag instead. (Phase 28.x can add the plugin if Kaan wants
    // single-click-pick.)
    setStatus("Drag the Rekordbox XML onto this panel.");
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
        const xml = payload.paths.find((p) => /\.xml$/i.test(p));
        if (xml) {
          void beginImport(xml);
        } else {
          setStatus("Need a .xml file (Rekordbox export).");
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
