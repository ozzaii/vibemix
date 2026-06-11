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

export interface DebriefDockOptions {
  /** When false, mount the dock cold and wait for the user to ask for sessions. */
  readonly autoRefresh?: boolean;
}

const MIN_DEBRIEF_SECONDS = 300;
const MIN_DEBRIEF_EVENTS = 5;
const MAX_VISIBLE_SESSIONS = 5;

const CSS = `
  /* Stage-as-page: the shell surface behind IS the room. The dock owns no
   * plate of its own — the readiness card below is the ONE raised object,
   * everything else sits flush on the stage (kills the plates-inside-plates
   * nesting the contract bans). */
  .debrief-dock {
    position: relative;
    width: min(1060px, calc(100vw - var(--sp-8)));
    max-width: 100%;
    min-height: min(640px, calc(100vh - var(--sp-8)));
    display: grid;
    grid-template-columns: minmax(250px, 0.72fr) minmax(0, 1fr);
    gap: var(--sp-6);
    padding: var(--sp-5);
    color: var(--text-secondary);
  }
  .debrief-dock > * {
    min-width: 0;
  }
  .debrief-dock__mast {
    align-self: stretch;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: var(--sp-5);
    padding: var(--sp-2) 0;
  }
  .debrief-dock__kicker,
  .debrief-dock__status,
  .debrief-dock__label,
  .debrief-dock__readiness-kicker,
  .debrief-dock__payback-label,
  .debrief-dock__readiness-metric dt,
  .debrief-dock__meta,
  .debrief-dock__row-state {
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .debrief-dock__reason,
  .debrief-dock__payoff {
    font-family: var(--type-mono);
    font-size: 11px;
    letter-spacing: 0; /* sentences read as sentences; lowercase carries 0em per DESIGN tracking-by-case */
    text-transform: none;
    line-height: 1.4;
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
    box-shadow: inset 0 1px 0 rgba(246, 243, 245, 0.046);
  }
  .debrief-dock__proof-row dt {
    margin: 0;
    color: var(--text-muted);
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
    grid-template-rows: auto auto minmax(0, 1fr);
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
  /* The ONE lead card on the stage — the mock's .nr.lead recipe: brand wash
   * over warm void, full 1px border, machined seat, 2px brand bar at the
   * left edge. */
  .debrief-dock__readiness {
    position: relative;
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--sp-3);
    align-items: start;
    padding: var(--sp-4) var(--sp-4) var(--sp-4) calc(var(--sp-4) + 4px);
    border: 1px solid var(--border-default);
    border-radius: var(--r-sm);
    background:
      linear-gradient(180deg, var(--brand-08) 0%, var(--brand-04) 50%, transparent 100%),
      linear-gradient(180deg, var(--void-8) 0%, var(--void-5) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.35),
      0 8px 24px rgba(0, 0, 0, 0.32);
  }
  .debrief-dock__readiness::before {
    content: "";
    position: absolute;
    left: 0;
    top: 18px;
    bottom: 18px;
    width: 2px;
    border-radius: 0 1px 1px 0;
    background: var(--brand);
    box-shadow: 0 0 6px var(--brand-50);
  }
  .debrief-dock__readiness[data-state="ready"] {
    border-color: var(--brand-22);
  }
  /* Cold boot: one serif line carries it — no wall of pending/checking
   * sentinel cells pretending to be data. */
  .debrief-dock__readiness[data-state="empty"] .debrief-dock__payback,
  .debrief-dock__readiness[data-state="empty"] .debrief-dock__readiness-metrics {
    display: none;
  }
  .debrief-dock__readiness[data-state="empty"]::before {
    background: var(--brand-35);
    box-shadow: none;
  }
  .debrief-dock__readiness-kicker {
    color: var(--brand);
  }
  .debrief-dock__readiness-title {
    margin: 4px 0 0;
    color: var(--text-primary);
    font-family: var(--type-serif);
    font-size: 24px;
    font-weight: 400;
    line-height: 1.1;
    letter-spacing: 0;
    text-shadow: var(--text-3d);
  }
  .debrief-dock__readiness-sub {
    margin: var(--sp-1) 0 0;
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.35;
  }
  .debrief-dock__payback {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
    gap: var(--sp-2);
    min-width: 0;
  }
  /* Flush figure-ground, not a boxed cell. These pairs live INSIDE the
   * readiness card, so per-cell boxes here were nested cards (always wrong) and
   * read as a dashboard stat-grid. The label-over-value pairs carry themselves
   * on the grid gap alone. */
  .debrief-dock__payback-cell {
    min-width: 0;
  }
  .debrief-dock__payback-label {
    display: block;
    color: var(--text-disabled);
  }
  .debrief-dock__payback-value {
    display: block;
    margin-top: 3px;
    color: var(--text-secondary);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 88, "wght" 620;
    font-size: 13px;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .debrief-dock__readiness[data-state="ready"] .debrief-dock__payback-value {
    color: var(--text-primary);
  }
  .debrief-dock__readiness-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--sp-4);
    width: 100%;
    min-width: 0;
    margin: 0;
    padding-top: var(--sp-3);
    /* One machined seam seats the three readouts like a spec line, instead of
     * three boxed cells stacked under the payback pairs. */
    box-shadow: inset 0 1px 0 rgba(246, 243, 245, 0.06);
  }
  .debrief-dock__readiness-metric {
    min-width: 0;
  }
  .debrief-dock__readiness-metric dt {
    margin: 0;
    color: var(--text-disabled);
  }
  .debrief-dock__readiness-metric dd {
    margin: 2px 0 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .debrief-dock__list {
    display: grid;
    align-content: start;
    gap: 0;
    min-height: 0;
    overflow: auto;
  }
  .debrief-dock__empty {
    display: grid;
    place-items: center;
    min-height: 200px;
    padding: var(--sp-5);
    color: var(--text-muted);
    text-align: center;
  }
  /* Hairline list rows on the stage — the mock's .nr: bottom seam, 2px left
   * state bar (transparent at rest, brand when the row is the live one). */
  .debrief-dock__row {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--sp-4);
    align-items: center;
    padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-4);
    border-bottom: 1px solid var(--border-subtle);
    transition: background 200ms var(--ease-brand);
  }
  .debrief-dock__row::before {
    content: "";
    position: absolute;
    left: 0;
    top: 12px;
    bottom: 12px;
    width: 2px;
    border-radius: 0 1px 1px 0;
    background: transparent;
    transition: background 250ms var(--ease-brand);
  }
  .debrief-dock__row:hover {
    background: var(--brand-04);
  }
  .debrief-dock__row:hover::before {
    background: var(--brand-35);
  }
  .debrief-dock__row[data-ready="true"]::before {
    background: var(--brand);
  }
  .debrief-dock__row-head {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: var(--sp-3);
  }
  .debrief-dock__date {
    margin: 0 0 var(--sp-2);
    color: var(--text-primary);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 88, "wght" 600;
    font-size: 15px;
    letter-spacing: 0.02em;
  }
  .debrief-dock__row-state {
    flex: 0 0 auto;
    padding: 4px 7px;
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-sm);
    color: var(--text-disabled);
    background: rgba(0, 0, 0, 0.16);
  }
  .debrief-dock__row[data-ready="true"] .debrief-dock__row-state {
    color: var(--brand);
    border-color: var(--brand-22);
    background: var(--brand-04);
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
  .debrief-dock__payoff {
    margin-top: var(--sp-1);
    color: var(--text-muted);
  }
  .debrief-dock__row[data-ready="true"] .debrief-dock__payoff {
    color: var(--brand);
  }
  /* Squared recessed rail with a flat fill — not the rounded-gradient-glow
   * loading pill this surface's own contract bans. */
  .debrief-dock__meter {
    position: relative;
    height: 3px;
    margin-top: var(--sp-3);
    overflow: hidden;
    border-radius: 1px;
    background: rgba(0, 0, 0, 0.4);
    box-shadow:
      inset 0 1px 2px rgba(0, 0, 0, 0.55),
      0 1px 0 rgba(255, 255, 255, 0.03);
  }
  .debrief-dock__meter::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: var(--ready-pct, 0%);
    background: var(--brand-50);
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
    box-shadow: inset 0 1px 0 rgba(246, 243, 245, 0.10);
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
    .debrief-dock__readiness {
      grid-template-columns: 1fr;
    }
    .debrief-dock__payback {
      grid-template-columns: 1fr;
    }
    .debrief-dock__readiness-metrics {
      min-width: 0;
      grid-template-columns: 1fr;
    }
  }
`;

registerStyle("shell-debrief-dock", CSS);

export function mountDebriefDock(
  host: HTMLElement,
  options: DebriefDockOptions = {},
): DebriefDockHandle {
  const autoRefresh = options.autoRefresh ?? true;
  const root = document.createElement("div");
  root.className = "debrief-dock";
  root.dataset.wire = "shell.debrief.dock";

  const mast = document.createElement("section");
  mast.className = "debrief-dock__mast";
  mast.innerHTML =
    '<div><div class="debrief-dock__kicker">debrief dock</div>' +
    '<h2 class="debrief-dock__title">Look back at your last set.</h2>' +
    '<p class="debrief-dock__sub">I replay the real moments, show you the why behind each call, then hand you one thing to drill.</p></div>' +
    '<dl class="debrief-dock__proof">' +
    '<div class="debrief-dock__proof-row"><dt>Timeline</dt><dd>drops, recoveries, energy shape</dd></div>' +
    '<div class="debrief-dock__proof-row"><dt>The why</dt><dd>every call tied to what I actually heard</dd></div>' +
    '<div class="debrief-dock__proof-row"><dt>Next</dt><dd>one drill or one Viber move</dd></div>' +
    "</dl>";

  const sessions = document.createElement("section");
  sessions.className = "debrief-dock__sessions";
  sessions.innerHTML =
    '<div class="debrief-dock__toolbar">' +
    '<div class="debrief-dock__status" role="status" aria-live="polite">ready when you are</div>' +
    '<button class="debrief-dock__refresh" type="button">Refresh</button>' +
    "</div>" +
    '<section class="debrief-dock__readiness" aria-label="next debrief readiness" data-state="empty">' +
    '<div><div class="debrief-dock__readiness-kicker">next debrief</div>' +
    '<h3 class="debrief-dock__readiness-title">checking recorder</h3>' +
    '<p class="debrief-dock__readiness-sub">Waiting for local session evidence.</p></div>' +
    '<div class="debrief-dock__payback" aria-label="fastest payback path">' +
    '<div class="debrief-dock__payback-cell"><span class="debrief-dock__payback-label">last set</span><strong class="debrief-dock__payback-value" data-payback="target">pending</strong></div>' +
    '<div class="debrief-dock__payback-cell"><span class="debrief-dock__payback-label">waiting on</span><strong class="debrief-dock__payback-value" data-payback="blocker">checking</strong></div>' +
    '<div class="debrief-dock__payback-cell"><span class="debrief-dock__payback-label">action</span><strong class="debrief-dock__payback-value" data-payback="action">wait</strong></div>' +
    '<div class="debrief-dock__payback-cell"><span class="debrief-dock__payback-label">you get</span><strong class="debrief-dock__payback-value" data-payback="unlocks">debrief</strong></div>' +
    "</div>" +
    '<dl class="debrief-dock__readiness-metrics">' +
    '<div class="debrief-dock__readiness-metric"><dt>length</dt><dd>pending</dd></div>' +
    '<div class="debrief-dock__readiness-metric"><dt>events</dt><dd>pending</dd></div>' +
    '<div class="debrief-dock__readiness-metric"><dt>ready</dt><dd>warming</dd></div>' +
    "</dl>" +
    "</section>" +
    '<div class="debrief-dock__list"></div>';

  root.append(mast, sessions);
  host.replaceChildren(root);

  const status = root.querySelector<HTMLElement>(".debrief-dock__status")!;
  const refreshButton = root.querySelector<HTMLButtonElement>(".debrief-dock__refresh")!;
  const readiness = root.querySelector<HTMLElement>(".debrief-dock__readiness")!;
  const list = root.querySelector<HTMLElement>(".debrief-dock__list")!;
  let disposed = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const renderColdState = (): void => {
    status.textContent = "ready when you are";
    list.replaceChildren(renderEmpty("Refresh when you want the latest local set receipts."));
    renderReadiness(readiness, null);
  };

  const refresh = async (attempt = 0): Promise<void> => {
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    status.textContent = "loading sessions";
    list.replaceChildren(renderEmpty("Checking recordings…"));
    refreshButton.disabled = true;
    try {
      const reply = await sendIpcRequest<RecordingsListResult>(
        "ipc.recordings.list",
        {},
        "ipc.recordings.list_result",
      );
      if (disposed) return;
      renderSessions(reply.payload.sessions, reply.payload.bytes_total, status, readiness, list);
    } catch (err) {
      if (disposed) return;
      if (attempt < 3) {
        status.textContent = "waiting for recorder";
        list.replaceChildren(renderEmpty("The session bus is still waking up. Checking again…"));
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
  if (autoRefresh) {
    void refresh();
  } else {
    renderColdState();
  }

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
  readiness: HTMLElement,
  list: HTMLElement,
): void {
  const visible = sessions.slice(0, MAX_VISIBLE_SESSIONS);
  status.textContent =
    sessions.length === 0
      ? "no sessions recorded"
      : `${sessions.length} sessions, ${formatBytes(bytesTotal)} stored`;

  if (visible.length === 0) {
    renderReadiness(readiness, null);
    list.replaceChildren(
      renderEmpty("Run a real set from Deck. When the recording closes, the debrief opens here."),
    );
    return;
  }

  // All recent sets are stopped-early / ineligible (none ready, none even
  // recoverable): show one calm "nothing to review yet" instead of a per-row
  // wall of warming gates. A stopped set is not a fault, just not reviewable.
  const anyReady = visible.some((session) => debriefEligibility(session).ready);
  const anyRecoverable = visible.some((session) => !session.crashed);
  if (!anyReady && !anyRecoverable) {
    renderReadiness(readiness, null, true);
    list.replaceChildren(...visible.map(renderSessionRow));
    return;
  }

  renderReadiness(readiness, bestReviewCandidate(visible));
  list.replaceChildren(...visible.map(renderSessionRow));
}

function renderSessionRow(summary: RecordingSummary): HTMLElement {
  const eligibility = debriefEligibility(summary);
  const readiness = reviewReadiness(summary);
  const row = document.createElement("article");
  row.className = "debrief-dock__row";
  row.dataset.ready = String(eligibility.ready);
  row.style.setProperty("--ready-pct", `${readiness.percent}%`);

  const copy = document.createElement("div");
  copy.className = "debrief-dock__copy";
  const reason = eligibility.ready
    ? "ready to review"
    : eligibility.reason;

  const date = document.createElement("h3");
  date.className = "debrief-dock__date";
  date.textContent = formatTimestamp(summary.started_at_iso);

  const state = document.createElement("div");
  state.className = "debrief-dock__row-state";
  state.textContent = eligibility.ready ? "debrief ready" : "capture more";

  const head = document.createElement("div");
  head.className = "debrief-dock__row-head";
  head.append(date, state);

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

  const payoff = document.createElement("div");
  payoff.className = "debrief-dock__payoff";
  payoff.textContent = rowPayoffLine(summary, eligibility.ready, readiness);

  const meter = document.createElement("div");
  meter.className = "debrief-dock__meter";
  meter.setAttribute("aria-label", `debrief readiness ${readiness.percent}%`);
  copy.append(head, meta, reasonEl, payoff, meter);

  const open = document.createElement("button");
  open.className = "debrief-dock__open";
  open.type = "button";
  open.disabled = !eligibility.ready;
  open.textContent = eligibility.ready ? "Open debrief" : "Not ready";
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

function renderReadiness(
  readiness: HTMLElement,
  summary: RecordingSummary | null,
  allStoppedEarly = false,
): void {
  const title = readiness.querySelector<HTMLElement>(".debrief-dock__readiness-title")!;
  const sub = readiness.querySelector<HTMLElement>(".debrief-dock__readiness-sub")!;
  const metrics = Array.from(
    readiness.querySelectorAll<HTMLElement>(".debrief-dock__readiness-metric dd"),
  );
  const payback = paybackTargets(readiness);

  if (!summary) {
    if (allStoppedEarly) {
      readiness.dataset.state = "empty";
      title.textContent = "nothing to review yet";
      sub.textContent =
        "Every recent set stopped before it sealed. Run one start to finish and your debrief opens here.";
      setPayback(payback, {
        target: "your next set",
        blocker: "none saved yet",
        action: "record start to finish",
        unlocks: "your first debrief",
      });
      setMetric(metrics[0], "0m");
      setMetric(metrics[1], "0 events");
      setMetric(metrics[2], "waiting");
      return;
    }
    readiness.dataset.state = "empty";
    title.textContent = "record a real set";
    sub.textContent = "Debrief arms after five minutes and enough evidence events.";
    setPayback(payback, {
      target: "no recording yet",
      blocker: "needs a set",
      action: "record from Deck",
      unlocks: "timeline, the why, drill",
    });
    setMetric(metrics[0], "0m");
    setMetric(metrics[1], "0 events");
    setMetric(metrics[2], "waiting");
    return;
  }

  const eligibility = debriefEligibility(summary);
  const progress = reviewReadiness(summary);
  const path = paybackPath(summary, eligibility.ready, progress);
  readiness.dataset.state = eligibility.ready ? "ready" : "warming";
  if (eligibility.ready) {
    title.textContent = "debrief is armed";
    sub.textContent = `${formatTimestamp(summary.started_at_iso)} is ready, with the why behind every call.`;
  } else if (summary.crashed) {
    title.textContent = "this set stopped early";
    sub.textContent = "It ended before the recording sealed, so I can't review it fairly. Run one full set and I'll have it.";
  } else {
    title.textContent = `capture ${progress.remainingLabel} more`;
    sub.textContent = "Keep Deck running until the recorder has enough context to judge fairly.";
  }
  setPayback(payback, path);
  setMetric(metrics[0], formatDuration(summary.duration_s));
  setMetric(metrics[1], `${summary.event_count} events`);
  setMetric(metrics[2], eligibility.ready ? "open" : progress.gateLabel);
}

function setMetric(target: HTMLElement | undefined, value: string): void {
  if (target) target.textContent = value;
}

type PaybackSlot = "target" | "blocker" | "action" | "unlocks";

function paybackTargets(readiness: HTMLElement): Record<PaybackSlot, HTMLElement | null> {
  return {
    target: readiness.querySelector<HTMLElement>('[data-payback="target"]'),
    blocker: readiness.querySelector<HTMLElement>('[data-payback="blocker"]'),
    action: readiness.querySelector<HTMLElement>('[data-payback="action"]'),
    unlocks: readiness.querySelector<HTMLElement>('[data-payback="unlocks"]'),
  };
}

function setPayback(
  targets: Record<PaybackSlot, HTMLElement | null>,
  values: Record<PaybackSlot, string>,
): void {
  if (targets.target) targets.target.textContent = values.target;
  if (targets.blocker) targets.blocker.textContent = values.blocker;
  if (targets.action) targets.action.textContent = values.action;
  if (targets.unlocks) targets.unlocks.textContent = values.unlocks;
}

function paybackPath(
  summary: RecordingSummary,
  ready: boolean,
  progress: ReturnType<typeof reviewReadiness>,
): Record<PaybackSlot, string> {
  const target = formatTimestamp(summary.started_at_iso);
  if (ready) {
    return {
      target,
      blocker: "none",
      action: "open your debrief",
      unlocks: "one drill or Viber move",
    };
  }
  if (summary.crashed) {
    return {
      target,
      blocker: "stopped early",
      action: "record a full set",
      unlocks: "your debrief",
    };
  }
  return {
    target,
    blocker: `${progress.remainingLabel} short`,
    action: "keep Deck running",
    unlocks: "your debrief",
  };
}

function rowPayoffLine(
  summary: RecordingSummary,
  ready: boolean,
  readiness: ReturnType<typeof reviewReadiness>,
): string {
  if (ready) return "Payback: open the debrief to leave with one drill or Viber move.";
  if (summary.crashed) return "Record one full set start to finish and I can review it.";
  return `${readiness.remainingLabel} more and I can review this set.`;
}

function bestReviewCandidate(sessions: RecordingSummary[]): RecordingSummary | null {
  if (sessions.length === 0) return null;
  const ready = sessions.find((session) => debriefEligibility(session).ready);
  if (ready) return ready;
  return sessions.reduce((best, session) =>
    reviewCandidateScore(session) > reviewCandidateScore(best) ? session : best,
  );
}

function reviewCandidateScore(summary: RecordingSummary): number {
  if (summary.crashed) return -1;
  const durationPct = Math.min(1, Math.max(0, summary.duration_s / MIN_DEBRIEF_SECONDS));
  const eventPct = Math.min(1, Math.max(0, summary.event_count / MIN_DEBRIEF_EVENTS));
  return durationPct + eventPct;
}

function reviewReadiness(summary: RecordingSummary): {
  percent: number;
  remainingLabel: string;
  gateLabel: string;
} {
  if (summary.crashed) {
    return { percent: 30, remainingLabel: "reliable evidence", gateLabel: "partial" };
  }
  const durationPct = Math.min(1, Math.max(0, summary.duration_s / MIN_DEBRIEF_SECONDS));
  const eventPct = Math.min(1, Math.max(0, summary.event_count / MIN_DEBRIEF_EVENTS));
  const percent = Math.round(Math.min(durationPct, eventPct) * 100);
  const remainingSeconds = Math.max(0, MIN_DEBRIEF_SECONDS - summary.duration_s);
  const remainingEvents = Math.max(0, MIN_DEBRIEF_EVENTS - summary.event_count);
  if (remainingSeconds > 0) {
    return {
      percent,
      remainingLabel: formatDurationCeil(remainingSeconds),
      gateLabel: "too short",
    };
  }
  if (remainingEvents > 0) {
    return {
      percent,
      remainingLabel: `${remainingEvents} events`,
      gateLabel: "more moves",
    };
  }
  return { percent: 100, remainingLabel: "0m", gateLabel: "open" };
}

function debriefEligibility(summary: RecordingSummary): { ready: boolean; reason: string } {
  if (summary.crashed) return { ready: false, reason: "stopped before it was saved" };
  if (summary.duration_s < MIN_DEBRIEF_SECONDS) {
    return { ready: false, reason: "needs at least 5 minutes" };
  }
  if (summary.event_count < MIN_DEBRIEF_EVENTS) {
    return { ready: false, reason: "needs more evidence events" };
  }
  return { ready: true, reason: "ready to review" };
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

function formatDurationCeil(seconds: number): string {
  const total = Math.max(0, Math.ceil(seconds));
  const minutes = Math.ceil(total / 60);
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
