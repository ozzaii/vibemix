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
 * Delete confirm: uses Phase 12 confirmDialog with `variant: "danger"`.
 * Mounts on document.body (matches confirm-dialog.ts modal pattern).
 *
 * Token discipline: 100% v5 (zero shim aliases, zero hex literals).
 *
 * Test coverage: ./recording-browser.spec.ts (8 cases).
 */

import { registerStyle } from "../../session/components/_style-registry.js";

import { renderConfirmDialog } from "./confirm-dialog.js";
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

  function openDeleteConfirm(summary: RecordingSummary): void {
    const timestamp = formatTimestamp(summary.started_at_iso);
    let dialogEl: HTMLElement | null = null;
    const close = (): void => {
      if (dialogEl !== null && dialogEl.isConnected) dialogEl.remove();
    };
    dialogEl = renderConfirmDialog({
      heading: `Delete session ${timestamp}?`,
      body: "This cannot be undone.",
      confirmLabel: "DELETE",
      cancelLabel: "CANCEL",
      variant: "danger",
      onConfirm: () => {
        close();
        opts.onDelete(summary.session_dir, timestamp);
      },
      onCancel: () => {
        close();
      },
    });
    document.body.append(dialogEl);
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
        onDelete: () => openDeleteConfirm(summary),
        absoluteWavPathResolver: opts.absoluteWavPathResolver,
      });
      rowHandles.push(handle);
      return handle.root;
    };
  }

  function mountList(sessions: RecordingSummary[]): void {
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
