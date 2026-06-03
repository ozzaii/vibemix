// SPDX-License-Identifier: Apache-2.0
//
// Folded Debrief launch surface. The full session review remains the dedicated
// debrief window on port 8766; this dock makes the shell route useful by showing
// recent recordings and opening the real review for eligible sessions.

import { sendIpcRequest } from "../ipc/client.js";
import type { RecordingsListResult } from "../ipc/messages.js";
import { registerStyle } from "../session/components/_style-registry.js";
import { invokeTauri } from "../tauri-runtime.js";

type RecordingSummary = RecordingsListResult["payload"]["sessions"][number];

export interface DebriefDockHandle {
  readonly root: HTMLElement;
  refresh(): Promise<void>;
  teardown(): void;
}

const MIN_DEBRIEF_SECONDS = 300;
const MIN_DEBRIEF_EVENTS = 5;
const MAX_VISIBLE_SESSIONS = 5;

const CSS = `
  .debrief-dock {
    position: relative;
    width: min(1060px, calc(100vw - var(--sp-8)));
    max-width: 100%;
    min-height: min(640px, calc(100vh - var(--sp-8)));
    display: grid;
    grid-template-columns: minmax(250px, 0.72fr) minmax(0, 1fr);
    gap: var(--sp-5);
    padding: var(--sp-5);
    color: var(--text-secondary);
    background:
      linear-gradient(135deg, var(--brand-04), transparent 32%),
      linear-gradient(180deg, var(--void-10), var(--void-2));
    border: 1px solid var(--border-default);
    border-radius: var(--rad-md);
    box-shadow: var(--chrome-highlight), inset 0 -1px 0 rgba(0, 0, 0, 0.58);
    overflow: hidden;
  }
  .debrief-dock::before {
    content: "";
    position: absolute;
    inset: 14px;
    pointer-events: none;
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-sm);
    background:
      repeating-linear-gradient(90deg, transparent 0 80px, rgba(255, 222, 242, 0.022) 80px 81px),
      linear-gradient(90deg, transparent 0 34%, var(--brand-04) 34.2%, transparent 34.6% 100%);
    opacity: 0.7;
  }
  .debrief-dock > * {
    position: relative;
    z-index: 1;
    min-width: 0;
  }
  .debrief-dock__mast {
    align-self: stretch;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: var(--sp-5);
    padding: var(--sp-4);
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-sm);
    background:
      linear-gradient(180deg, rgba(255, 222, 242, 0.022), transparent 28%),
      rgba(0, 0, 0, 0.18);
    box-shadow: inset 0 1px 0 var(--glass-top);
  }
  .debrief-dock__kicker,
  .debrief-dock__status,
  .debrief-dock__label,
  .debrief-dock__meta,
  .debrief-dock__reason {
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .debrief-dock__kicker {
    color: var(--brand);
    text-shadow: 0 0 6px var(--brand-22);
  }
  .debrief-dock__title {
    margin: var(--sp-2) 0 var(--sp-3);
    color: var(--text-primary);
    font-family: var(--type-serif);
    font-size: 34px;
    font-weight: 400;
    line-height: 1.05;
    letter-spacing: 0;
    text-shadow: var(--text-3d);
  }
  .debrief-dock__sub {
    max-width: 32ch;
    margin: 0;
    color: var(--text-muted);
    font-size: 14px;
    line-height: 1.45;
  }
  .debrief-dock__proof {
    display: grid;
    gap: var(--sp-2);
    margin: 0;
  }
  .debrief-dock__proof-row {
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    gap: var(--sp-3);
    padding-top: var(--sp-2);
    border-top: 1px solid var(--border-subtle);
  }
  .debrief-dock__proof-row dt {
    margin: 0;
    color: var(--brand);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .debrief-dock__proof-row dd {
    margin: 0;
    color: var(--text-secondary);
    font-size: 13px;
  }
  .debrief-dock__sessions {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    gap: var(--sp-3);
    min-height: 0;
  }
  .debrief-dock__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    min-height: 36px;
  }
  .debrief-dock__status {
    color: var(--text-muted);
  }
  .debrief-dock__refresh {
    min-width: 92px;
    height: 32px;
    padding: 0 var(--sp-3);
    border-radius: var(--rad-sm);
    border: 1px solid var(--border-default);
    background: rgba(0, 0, 0, 0.22);
    color: var(--text-secondary);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .debrief-dock__refresh:hover {
    color: var(--brand);
    border-color: var(--brand-22);
    background: var(--brand-04);
  }
  .debrief-dock__list {
    display: grid;
    align-content: start;
    gap: var(--sp-2);
    min-height: 0;
    overflow: auto;
  }
  .debrief-dock__empty {
    display: grid;
    place-items: center;
    min-height: 260px;
    padding: var(--sp-5);
    border: 1px dashed var(--border-default);
    border-radius: var(--rad-sm);
    color: var(--text-muted);
    text-align: center;
  }
  .debrief-dock__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--sp-4);
    align-items: center;
    padding: var(--sp-3);
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-sm);
    background:
      linear-gradient(180deg, rgba(255, 222, 242, 0.018), transparent 50%),
      rgba(0, 0, 0, 0.20);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
  }
  .debrief-dock__row[data-ready="true"] {
    border-color: var(--brand-22);
    background:
      linear-gradient(180deg, var(--brand-08), transparent 58%),
      rgba(0, 0, 0, 0.20);
  }
  .debrief-dock__date {
    margin: 0 0 var(--sp-2);
    color: var(--text-primary);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 88, "wght" 600;
    font-size: 15px;
    letter-spacing: 0.02em;
  }
  .debrief-dock__meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-3);
    color: var(--text-muted);
  }
  .debrief-dock__reason {
    margin-top: var(--sp-2);
    color: var(--text-disabled);
  }
  .debrief-dock__open {
    min-width: 128px;
    height: 36px;
    border-radius: var(--rad-sm);
    border: 1px solid var(--brand-40);
    background: linear-gradient(180deg, var(--brand-16), var(--brand-04));
    color: var(--brand);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 700;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    text-shadow: 0 0 6px var(--brand-22);
    box-shadow: inset 0 1px 0 rgba(255, 222, 242, 0.10);
  }
  .debrief-dock__open:disabled {
    cursor: not-allowed;
    opacity: 0.48;
    border-color: var(--border-subtle);
    background: rgba(0, 0, 0, 0.16);
    color: var(--text-disabled);
    text-shadow: none;
  }
  .debrief-dock__error {
    padding: var(--sp-3);
    border: 1px solid rgba(212, 65, 58, 0.34);
    border-radius: var(--rad-sm);
    color: var(--led-fault);
    background: rgba(212, 65, 58, 0.07);
    font-family: var(--type-mono);
    font-size: 11px;
  }
  @media (max-width: 860px) {
    .debrief-dock {
      width: 100%;
      min-height: 0;
      grid-template-columns: 1fr;
      padding: var(--sp-4);
    }
  }
`;

registerStyle("shell-debrief-dock", CSS);

export function mountDebriefDock(host: HTMLElement): DebriefDockHandle {
  const root = document.createElement("div");
  root.className = "debrief-dock";
  root.dataset.wire = "shell.debrief.dock";

  const mast = document.createElement("section");
  mast.className = "debrief-dock__mast";
  mast.innerHTML =
    '<div><div class="debrief-dock__kicker">review dock</div>' +
    '<h2 class="debrief-dock__title">Make the last set pay you back.</h2>' +
    '<p class="debrief-dock__sub">Open a cited review, replay the moment, then leave with one drill or one crate move.</p></div>' +
    '<dl class="debrief-dock__proof">' +
    '<div class="debrief-dock__proof-row"><dt>Timeline</dt><dd>drops, recoveries, energy shape</dd></div>' +
    '<div class="debrief-dock__proof-row"><dt>Receipts</dt><dd>each praise or critique tied to evidence</dd></div>' +
    '<div class="debrief-dock__proof-row"><dt>Next</dt><dd>practice drill or Viber crate follow-up</dd></div>' +
    "</dl>";

  const sessions = document.createElement("section");
  sessions.className = "debrief-dock__sessions";
  sessions.innerHTML =
    '<div class="debrief-dock__toolbar">' +
    '<div class="debrief-dock__status" role="status" aria-live="polite">loading sessions</div>' +
    '<button class="debrief-dock__refresh" type="button">Refresh</button>' +
    "</div>" +
    '<div class="debrief-dock__list"></div>';

  root.append(mast, sessions);
  host.replaceChildren(root);

  const status = root.querySelector<HTMLElement>(".debrief-dock__status")!;
  const refreshButton = root.querySelector<HTMLButtonElement>(".debrief-dock__refresh")!;
  const list = root.querySelector<HTMLElement>(".debrief-dock__list")!;
  let disposed = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const refresh = async (attempt = 0): Promise<void> => {
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    status.textContent = "loading sessions";
    list.replaceChildren(renderEmpty("Checking recordings..."));
    refreshButton.disabled = true;
    try {
      const reply = await sendIpcRequest<RecordingsListResult>(
        "ipc.recordings.list",
        {},
        "ipc.recordings.list_result",
      );
      if (disposed) return;
      renderSessions(reply.payload.sessions, reply.payload.bytes_total, status, list);
    } catch (err) {
      if (disposed) return;
      if (attempt < 3) {
        status.textContent = "waiting for recorder";
        list.replaceChildren(renderEmpty("The session bus is still waking up. Checking again..."));
        retryTimer = setTimeout(() => {
          void refresh(attempt + 1);
        }, 1200);
        return;
      }
      const message = err instanceof Error ? err.message : String(err);
      status.textContent = "recordings unavailable";
      const error = document.createElement("div");
      error.className = "debrief-dock__error";
      error.textContent = message;
      list.replaceChildren(error);
    } finally {
      if (!disposed) refreshButton.disabled = false;
    }
  };

  refreshButton.addEventListener("click", () => {
    void refresh();
  });
  void refresh();

  return {
    root,
    refresh,
    teardown(): void {
      disposed = true;
      if (retryTimer !== null) clearTimeout(retryTimer);
      root.remove();
    },
  };
}

function renderSessions(
  sessions: RecordingSummary[],
  bytesTotal: number,
  status: HTMLElement,
  list: HTMLElement,
): void {
  const visible = sessions.slice(0, MAX_VISIBLE_SESSIONS);
  status.textContent =
    sessions.length === 0
      ? "no sessions recorded"
      : `${sessions.length} sessions, ${formatBytes(bytesTotal)} stored`;

  if (visible.length === 0) {
    list.replaceChildren(
      renderEmpty("Run a real set from Deck. When the recording closes, the review opens here."),
    );
    return;
  }

  list.replaceChildren(...visible.map(renderSessionRow));
}

function renderSessionRow(summary: RecordingSummary): HTMLElement {
  const eligibility = debriefEligibility(summary);
  const row = document.createElement("article");
  row.className = "debrief-dock__row";
  row.dataset.ready = String(eligibility.ready);

  const copy = document.createElement("div");
  copy.className = "debrief-dock__copy";
  const reason = eligibility.ready
    ? "ready for cited review"
    : eligibility.reason;

  const date = document.createElement("h3");
  date.className = "debrief-dock__date";
  date.textContent = formatTimestamp(summary.started_at_iso);

  const meta = document.createElement("div");
  meta.className = "debrief-dock__meta";
  for (const value of [
    formatDuration(summary.duration_s),
    `${summary.event_count} events`,
    formatBytes(summary.bytes_total),
  ]) {
    const item = document.createElement("span");
    item.textContent = value;
    meta.append(item);
  }

  const reasonEl = document.createElement("div");
  reasonEl.className = "debrief-dock__reason";
  reasonEl.textContent = reason;
  copy.append(date, meta, reasonEl);

  const open = document.createElement("button");
  open.className = "debrief-dock__open";
  open.type = "button";
  open.disabled = !eligibility.ready;
  open.textContent = eligibility.ready ? "Open review" : "Not ready";
  open.title = eligibility.ready ? "Open debrief" : eligibility.reason;
  open.addEventListener("click", () => {
    if (!eligibility.ready) return;
    void invokeTauri("open_debrief_window", { sessionDir: summary.session_dir }).catch((err) => {
      // eslint-disable-next-line no-console
      console.error("open_debrief_window failed:", err);
    });
  });

  row.append(copy, open);
  return row;
}

function debriefEligibility(summary: RecordingSummary): { ready: boolean; reason: string } {
  if (summary.crashed) return { ready: false, reason: "session crashed, partial evidence only" };
  if (summary.duration_s < MIN_DEBRIEF_SECONDS) {
    return { ready: false, reason: "needs at least 5 minutes" };
  }
  if (summary.event_count < MIN_DEBRIEF_EVENTS) {
    return { ready: false, reason: "needs more evidence events" };
  }
  return { ready: true, reason: "ready for cited review" };
}

function renderEmpty(text: string): HTMLElement {
  const empty = document.createElement("div");
  empty.className = "debrief-dock__empty";
  empty.textContent = text;
  return empty;
}

function formatTimestamp(isoString: string): string {
  const t = isoString.indexOf("T");
  if (t === -1) return isoString;
  return `${isoString.slice(0, t)} ${isoString.slice(t + 1, t + 6)}`;
}

function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours}h ${rest}m`;
}

function formatBytes(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) return `${Math.max(1, Math.round(mb))} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}
