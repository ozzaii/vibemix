/* Phase 15 Plan 04 Task 2 — recording-browser.ts.
 *
 * Pure-function component: virtualized list of recording rows + disk
 * usage line + empty state. Mounts inside the Phase 12 RECORDING group
 * as a sibling of the retention slider (UI-SPEC §Phase Surface Inventory).
 *
 * Virtualization:
 *   - <=50 sessions  → full mount (simpler + faster per RESEARCH).
 *   -  >50 sessions → IntersectionObserver chunked render (12-row chunks
 *     until exhausted, RESEARCH Code Example lines ~536-565).
 *
 * Sentinel usage values (Plan 15-04 must_haves):
 *   - bytes_total === -1  → "RECORDINGS · LOADING…"
 *   - bytes_total === -2  → "RECORDINGS · UNAVAILABLE"
 *   - otherwise            → "RECORDINGS · {N} SESSIONS · {SIZE} USED"
 *
 * Delete UX — IMPECCABLE WAVE 5.A (2026-05-14):
 *   Previously a modal confirm-dialog blocked the drawer with a
 *   destructive Y/N. The critique flagged this as a Heuristic 3 (User
 *   Control & Freedom) miss: a touring DJ tagging old sets shouldn't be
 *   tapped on the shoulder for every delete. The new flow:
 *     1. Click × → row vanishes immediately.
 *     2. A 4-second toast renders at the bottom-right of the drawer:
 *        "deleted · undo?" (amber-underlined undo).
 *     3. Undo within the window → row restores + delete is cancelled.
 *     4. Timer elapses → fire the real onDelete callback.
 *
 *   Restore is a local client-side cancellation; no `recording.restore`
 *   IPC exists today. When the timer fires we call onDelete which
 *   dispatches the real ipc.recordings.delete.
 *
 * Token discipline: 100% v5 (zero shim aliases, zero hex literals).
 *
 * Test coverage: ./recording-browser.spec.ts (8 cases).
 */

import { registerStyle } from "../../session/components/_style-registry.js";

import {
  renderRecordingRow,
  type RecordingRowHandle,
  type RecordingSummary,
} from "./recording-row.js";

export type { RecordingSummary };

export interface RecordingsUsage {
  sessions: number;
  /** Total bytes used. Sentinels: -1 = LOADING…, -2 = UNAVAILABLE. */
  bytes_total: number;
}

export interface RecordingBrowserHandle {
  root: HTMLElement;
  setSessions(sessions: RecordingSummary[]): void;
  setUsage(usage: RecordingsUsage): void;
}

export interface RecordingBrowserProps {
  initialSessions: RecordingSummary[];
  initialUsage: RecordingsUsage;
  /** Called when a row is expanded (UI-SPEC §Component Contracts). */
  onReplay: (session_dir: string) => void;
  /** Called after the user confirms the delete dialog (NOT on click). */
  onDelete: (session_dir: string, timestamp: string) => void;
  /** Optional resolver for production recordings root prefix. Default OK
   *  for unit tests; Plan 15-05 injects the actual platform path. */
  absoluteWavPathResolver?: (session_dir: string) => string;
}

const GB = 1024 * 1024 * 1024;
const MB = 1024 * 1024;

/** Human-readable size suffix. UI-SPEC §Disk usage line format:
 *    <  1 GB → "{N} MB USED"  (integer MB)
 *    >= 1 GB → "{N.N} GB USED" (one decimal) */
function formatBytes(bytes: number): string {
  if (bytes < GB) {
    const mb = Math.round(bytes / MB);
    return `${mb} MB USED`;
  }
  const gb = bytes / GB;
  return `${gb.toFixed(1)} GB USED`;
}

/** Build the disk-usage line string per the sentinel + normal formats. */
function formatUsageLine(usage: RecordingsUsage): string {
  if (usage.bytes_total === -1) return "RECORDINGS · LOADING…";
  if (usage.bytes_total === -2) return "RECORDINGS · UNAVAILABLE";
  return `RECORDINGS · ${usage.sessions} SESSIONS · ${formatBytes(usage.bytes_total)}`;
}

/** Same slice as recording-row.ts — used for the confirm dialog heading. */
function formatTimestamp(isoString: string): string {
  const t = isoString.indexOf("T");
  if (t === -1) return isoString;
  return `${isoString.slice(0, t)} ${isoString.slice(t + 1, t + 6)}`;
}

const VIRTUALIZATION_THRESHOLD = 50;
const CHUNK_SIZE = 12;

const CSS = `
  .vmx-rec-browser {
    margin-top: var(--sp-4);
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    position: relative;
  }
  .vmx-rec-browser__usage {
    font-family: var(--type-body);
    font-size: 9px;
    font-weight: 500;
    font-stretch: 85%;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    user-select: none;
  }
  .vmx-rec-browser__list {
    display: flex;
    flex-direction: column;
    border-top: 1px solid var(--glass-edge);
  }
  .vmx-rec-browser__empty {
    padding: var(--sp-4) var(--sp-3);
    text-align: center;
    color: var(--silk-40);
    font-family: var(--type-body);
    font-size: 14px;
  }
  .vmx-rec-browser__sentinel {
    height: 1px;
  }

  /* Undo toast — bottom-right of the drawer body. CDJ Whisper restraint:
   * dark glass, single amber accent on "undo?", small + brief. */
  .vmx-rec-browser__toast {
    position: fixed;
    right: var(--sp-5);
    bottom: var(--sp-5);
    z-index: 60;
    display: inline-flex;
    align-items: center;
    gap: var(--sp-3);
    padding: 10px var(--sp-4);
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 8px 24px rgba(0, 0, 0, 0.55);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--silk-65);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    animation: vmx-rec-toast-in 150ms ease-out;
  }
  .vmx-rec-browser__toast-label {
    color: var(--silk-65);
  }
  .vmx-rec-browser__toast-sep {
    color: var(--silk-40);
  }
  .vmx-rec-browser__toast-undo {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    background: transparent;
    border: none;
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    text-decoration: underline;
    text-decoration-color: var(--amber-65);
    text-underline-offset: 3px;
    cursor: pointer;
    padding: 2px 4px;
    transition: color var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  .vmx-rec-browser__toast-undo:hover {
    color: var(--amber-pale);
    text-shadow: 0 0 6px var(--amber-40);
  }
  @keyframes vmx-rec-toast-in {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;

registerStyle("vmx-rec-browser", CSS);

const EMPTY_COPY = "No recordings yet. Sessions appear here after they end.";

export function renderRecordingBrowser(
  opts: RecordingBrowserProps,
): RecordingBrowserHandle {
  const root = document.createElement("div");
  root.className = "vmx-rec-browser";

  const usageLine = document.createElement("div");
  usageLine.className = "vmx-rec-browser__usage";
  usageLine.setAttribute("role", "status");
  usageLine.setAttribute("aria-live", "polite");
  usageLine.textContent = formatUsageLine(opts.initialUsage);
  root.append(usageLine);

  const listEl = document.createElement("div");
  listEl.className = "vmx-rec-browser__list";
  root.append(listEl);

  // Track in-flight virtualization observer so a subsequent setSessions
  // can disconnect it before rebuilding the list.
  let activeObserver: IntersectionObserver | null = null;
  // Track row handles for potential future re-use (currently rebuilt each
  // setSessions call — bounded memory + simpler invariants).
  let rowHandles: RecordingRowHandle[] = [];
  // The current session list — owned here so undo-toast can restore a
  // row optimistically without going through the parent slice.
  let currentSessions: RecordingSummary[] = [];

  // Undo-toast state — at most one pending delete at a time. A second
  // delete during an in-flight undo window commits the prior delete and
  // queues the new one.
  interface PendingDelete {
    summary: RecordingSummary;
    timestamp: string;
    timeoutId: number;
    toastEl: HTMLElement;
  }
  let pending: PendingDelete | null = null;

  const UNDO_WINDOW_MS = 4000;

  /** Fire the real delete callback and tear down the toast. Idempotent. */
  function commitPending(): void {
    if (!pending) return;
    const p = pending;
    pending = null;
    try {
      window.clearTimeout(p.timeoutId);
    } catch {
      /* timer already fired */
    }
    try {
      p.toastEl.remove();
    } catch {
      /* toast already gone */
    }
    opts.onDelete(p.summary.session_dir, p.timestamp);
  }

  /** Restore the row + cancel the pending delete. */
  function undoPending(): void {
    if (!pending) return;
    const p = pending;
    pending = null;
    try {
      window.clearTimeout(p.timeoutId);
    } catch {
      /* timer already fired */
    }
    try {
      p.toastEl.remove();
    } catch {
      /* toast already gone */
    }
    // Restore the row to currentSessions in its original position. We
    // walk the original session_dir list to find the insertion index —
    // session_dir is unique (ISO-timestamped directory name).
    const idx = findRestoreIndex(p.summary, currentSessions);
    const restored = [
      ...currentSessions.slice(0, idx),
      p.summary,
      ...currentSessions.slice(idx),
    ];
    mountList(restored);
  }

  /** Find the index at which to splice a restored row back into the live
   *  session list. We sort by `started_at_iso` desc (newest first — same
   *  as the sidecar's wire order), so we walk forward and insert at the
   *  first index where existing.started_at_iso < restored.started_at_iso. */
  function findRestoreIndex(
    restored: RecordingSummary,
    list: RecordingSummary[],
  ): number {
    for (let i = 0; i < list.length; i++) {
      if (list[i]!.started_at_iso < restored.started_at_iso) return i;
    }
    return list.length;
  }

  /** Open the undo toast for the given pending delete. */
  function openUndoToast(p: Omit<PendingDelete, "toastEl">): HTMLElement {
    const toast = document.createElement("div");
    toast.className = "vmx-rec-browser__toast";
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "polite");

    const label = document.createElement("span");
    label.className = "vmx-rec-browser__toast-label";
    label.textContent = "deleted";
    const sep = document.createElement("span");
    sep.className = "vmx-rec-browser__toast-sep";
    sep.textContent = "·";
    const undoBtn = document.createElement("button");
    undoBtn.type = "button";
    undoBtn.className = "vmx-rec-browser__toast-undo";
    undoBtn.textContent = "undo?";
    undoBtn.addEventListener("click", (e) => {
      e.preventDefault();
      undoPending();
    });

    toast.append(label, sep, undoBtn);
    document.body.append(toast);
    return toast;
  }

  function openDeleteWithUndo(summary: RecordingSummary): void {
    // Stack discipline: any prior pending delete commits before a new one
    // starts. The user has only one undo window in flight at a time —
    // simpler invariants + matches the bottom-right toast's single-slot UX.
    if (pending) commitPending();

    const timestamp = formatTimestamp(summary.started_at_iso);

    // Optimistic remove — the row vanishes from the list before the
    // sidecar IPC fires. If the user clicks undo, we splice it back.
    const nextSessions = currentSessions.filter(
      (s) => s.session_dir !== summary.session_dir,
    );
    mountList(nextSessions);

    // TODO(impeccable Wave 5.B): if/when an `ipc.recordings.restore` IPC
    // exists, fire it from undoPending() to ack the cancellation to the
    // sidecar. Today the local client-side queue is enough because
    // onDelete only fires when the timer elapses.
    const partial = { summary, timestamp } as Omit<
      PendingDelete,
      "toastEl" | "timeoutId"
    >;
    const timeoutId = window.setTimeout(() => {
      commitPending();
    }, UNDO_WINDOW_MS);
    const toastEl = openUndoToast({ ...partial, timeoutId });
    pending = { ...partial, timeoutId, toastEl };
  }

  function makeRowFactory(): (summary: RecordingSummary) => HTMLElement {
    return (summary: RecordingSummary): HTMLElement => {
      const handle = renderRecordingRow({
        summary,
        onToggle: () => {
          opts.onReplay(summary.session_dir);
          // Toggle by inspecting current data-open state.
          const isOpen = handle.root.dataset.open === "true";
          handle.setExpanded(!isOpen);
        },
        onDelete: () => openDeleteWithUndo(summary),
        absoluteWavPathResolver: opts.absoluteWavPathResolver,
      });
      rowHandles.push(handle);
      return handle.root;
    };
  }

  function mountList(sessions: RecordingSummary[]): void {
    currentSessions = sessions;
    // Tear down prior observer + clear list children + row handles.
    if (activeObserver !== null) {
      activeObserver.disconnect();
      activeObserver = null;
    }
    rowHandles = [];
    listEl.replaceChildren();

    if (sessions.length === 0) {
      const empty = document.createElement("div");
      empty.className = "vmx-rec-browser__empty";
      empty.setAttribute("role", "status");
      empty.setAttribute("aria-live", "polite");
      empty.textContent = EMPTY_COPY;
      listEl.append(empty);
      return;
    }

    const rowFactory = makeRowFactory();

    if (sessions.length <= VIRTUALIZATION_THRESHOLD) {
      for (const summary of sessions) listEl.append(rowFactory(summary));
      return;
    }

    // >50 sessions → 12-row chunks gated by IntersectionObserver. Render
    // the first chunk synchronously so the user sees content immediately,
    // then mount remaining chunks as the sentinel scrolls into view.
    let renderedCount = 0;
    const firstChunk = sessions.slice(0, CHUNK_SIZE);
    for (const summary of firstChunk) listEl.append(rowFactory(summary));
    renderedCount += firstChunk.length;

    const sentinel = document.createElement("div");
    sentinel.className = "vmx-rec-browser__sentinel";
    sentinel.setAttribute("aria-hidden", "true");
    listEl.append(sentinel);

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.length === 0 || !entries[0]!.isIntersecting) return;
        const nextChunk = sessions.slice(
          renderedCount,
          renderedCount + CHUNK_SIZE,
        );
        for (const summary of nextChunk) sentinel.before(rowFactory(summary));
        renderedCount += nextChunk.length;
        if (renderedCount >= sessions.length) {
          observer.disconnect();
          sentinel.remove();
          activeObserver = null;
        }
      },
      { root: null, rootMargin: "200px" },
    );
    observer.observe(sentinel);
    activeObserver = observer;
  }

  // Initial mount.
  mountList(opts.initialSessions);

  return {
    root,
    setSessions(sessions: RecordingSummary[]): void {
      mountList(sessions);
    },
    setUsage(usage: RecordingsUsage): void {
      usageLine.textContent = formatUsageLine(usage);
    },
  };
}
