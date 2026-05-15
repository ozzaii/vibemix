/* Phase 15 Plan 04 Task 1 — recording-row.ts.
 *
 * Pure-function component: one session row in the in-drawer recording browser.
 * Lifecycle obligations from UI-SPEC §Row anatomy + §Row expanded state +
 * 15-RESEARCH.md Pitfall 3 + Pattern 2:
 *
 *   - Lazy-mount <audio> + transcript overlay on first setExpanded(true).
 *   - On collapse: tear down <audio> via removeAttribute("src") + load()
 *     (decoder release per MDN) AND detach the transcript node so a
 *     re-expand re-fetches fresh events.jsonl state (bounded memory).
 *   - 250ms height transition; prefers-reduced-motion: reduce flips to
 *     display: none / display: block per the @media override.
 *   - Delete button is a one-shot — clicking opens the parent's
 *     onDelete callback (parent mounts the confirm dialog at the modal
 *     z-index layer above the drawer body).
 *
 * Token discipline (Phase 14 v5 only — shim deleted in 14-05 commit 79a7208):
 *   - Glass: --glass-2 (row bg), --glass-3 (expand panel bg), --glass-edge,
 *     --amber-22 (open-edge highlight + bold transcript line border).
 *   - Silk: --silk (active text), --silk-65 (timestamp + idle icon),
 *     --silk-40 (dim transcript lines + delete idle).
 *   - Amber accents (7 reserved uses per UI-SPEC §Color, expanded by
 *     Plan 15-03 Task 2 from 5 → 7): replay-hover, reveal-hover,
 *     open-external-hover, <audio> accent-color, expand panel top edge,
 *     bold transcript line border-left, plus the silk-65→amber ink-flip
 *     applied identically across the three "info" buttons (replay,
 *     reveal, open-external). Plan 15-03 SUMMARY documents the expansion
 *     as an accepted scope change (UI-SPEC's §Color reserved-amber list
 *     went 8 → 10 elements when both new icons were introduced).
 *   - Destructive: var(--led-fault) on delete hover (the alias
 *     `var(--rec)` referenced in UI-SPEC was never defined in
 *     tokens.css — Phase 14 deleted the shim but the alias was not
 *     re-introduced; we use --led-fault directly to match the actual
 *     definition + confirm-dialog.ts:175 destructive-variant precedent).
 *   - Only two inline rgba values are allowed (UI-SPEC §Color exception):
 *       rgba(214, 207, 199, 0.06)  — row hover bg (silk derivation)
 *       rgba(212, 65, 58, 0.18)    — delete-hover inset shadow
 *
 * Action cluster (Plan 15-03 Task 2 — was 64px, grew to 128px):
 *   4 buttons × 24px icon + 3 gaps × 8px = 120px + 8px breathing room.
 *   Order left→right: replay (info) · reveal (info) · open-external (info)
 *   · delete (destructive). Replay-style hover ink-flip (silk-65→amber)
 *   applies to all three info buttons; delete keeps its own led-fault
 *   hover discipline.
 *
 * Click handlers fire `revealInOS(session_dir)` / `openInputWav(session_dir)`
 * from `../../ipc/client.ts` — typed thin wrappers over the Tauri Rust
 * commands defined in tauri/src-tauri/src/recordings.rs (Plan 15-03 Task 1).
 *
 * Test coverage: ./recording-row.spec.ts (14 pre-existing + 4 new = 18 cases).
 */

import { convertFileSrc, invoke } from "@tauri-apps/api/core";

import { openInputWav, revealInOS, sendIpcRequest } from "../../ipc/client.js";
import { registerStyle } from "../../session/components/_style-registry.js";

/** Mirror of `RecordingsListResult.payload.sessions[]` (codegen output from
 *  Plan 15-01). Inlined here because the codegen emits an anonymous shape
 *  rather than a named `RecordingSummary` type alias — see
 *  `tauri/ui/src/ipc/messages.ts:310-317`. The browser component (Task 2)
 *  imports this same shape via the type re-export below. */
export interface RecordingSummary {
  session_dir: string;
  started_at_iso: string;
  duration_s: number;
  event_count: number;
  bytes_total: number;
  crashed: boolean;
}

export interface RecordingRowHandle {
  root: HTMLElement;
  setExpanded(open: boolean): void;
  setAudioSrc(absoluteWavPath: string): void;
}

export interface RecordingRowProps {
  summary: RecordingSummary;
  onToggle: () => void;
  onDelete: () => void;
  /** Optional path resolver — Plan 15-05 injects the production recordings
   *  root prefix. Default = `(sd) => sd + "/voice.wav"` for unit tests. */
  absoluteWavPathResolver?: (session_dir: string) => string;
}

/** Format `duration_s` per UI-SPEC §Row anatomy:
 *    <   1h → `{M}m`     (e.g. `48m`)
 *    >= 1h → `{H}h {MM}m` (e.g. `1h 24m`) */
function formatDuration(seconds: number): string {
  const total = Math.floor(seconds);
  if (total < 3600) {
    const m = Math.floor(total / 60);
    return `${m}m`;
  }
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  // Don't zero-pad the minutes per UI-SPEC example "1h 24m" (not "1h 04m"
  // unless minutes < 10 — but the spec example uses no padding either way).
  return `${h}h ${m}m`;
}

/** Slice the ISO timestamp into `YYYY-MM-DD HH:MM` (no seconds, no zone)
 *  per UI-SPEC §Row anatomy — left cell density target. Falls back to the
 *  raw string if the ISO shape is unexpected. */
function formatTimestamp(isoString: string): string {
  // "2026-05-13T21:04:10+02:00" → date "2026-05-13" + time "21:04"
  const t = isoString.indexOf("T");
  if (t === -1) return isoString;
  const date = isoString.slice(0, t);
  const timePart = isoString.slice(t + 1);
  const hhmm = timePart.slice(0, 5); // "21:04"
  return `${date} ${hhmm}`;
}

/** Format a session-relative event timestamp as `[+M:SS]` per UI-SPEC §Row
 *  expanded state + Plan 15-04 §Task 1 §behavior Test 12.
 *  `0.0` → `[+0:00]`, `5.2` → `[+0:05]`, `125.0` → `[+2:05]`. */
function formatRelativeTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  const ss = s < 10 ? `0${s}` : `${s}`;
  return `[+${m}:${ss}]`;
}

/** Map a single events.jsonl record to (display label, bold/dim emphasis).
 *  Per Interfaces §"Transcript event-kind → style mapping" + §"Event line
 *  label derivation" in 15-04-PLAN.md. */
function deriveEventLabel(
  event: { t: number; kind: string; [k: string]: unknown },
): { label: string; emphasis: "bold" | "dim" } {
  const kind = event.kind;
  if (kind === "ai_text") {
    const text = typeof event.text === "string" ? event.text : "";
    const truncated = text.length > 240 ? `${text.slice(0, 240)}…` : text;
    return { label: truncated, emphasis: "bold" };
  }
  if (kind === "trigger" || kind === "trigger_fired") {
    const reason = typeof event.reason === "string" ? event.reason : kind;
    return { label: `trigger: ${reason}`, emphasis: "bold" };
  }
  if (kind === "controller_move" || kind === "midi_event") {
    const control = typeof event.control === "string" ? event.control : null;
    const value = event.value;
    if (control !== null && value !== undefined) {
      const valueStr = typeof value === "number"
        ? (Number.isInteger(value) ? String(value) : value.toFixed(2))
        : String(value);
      return { label: `${control} ${valueStr}`, emphasis: "dim" };
    }
    return { label: kind, emphasis: "dim" };
  }
  if (kind === "session_start") {
    return { label: "session start", emphasis: "dim" };
  }
  return { label: kind, emphasis: "dim" };
}

const REPLAY_SVG = `
<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14">
  <path d="M4 3 L13 8 L4 13 Z" fill="currentColor" />
</svg>
`;
// Folder with a small arrow on the lower-right — "reveal in finder/explorer".
// 16×16 viewBox to match REPLAY/DELETE; 14×14 render for a flush 24px button.
const REVEAL_SVG = `
<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14">
  <path d="M2 4 L6 4 L7.5 5.5 L14 5.5 L14 13 L2 13 Z" fill="none"
        stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
  <path d="M9 9.5 L11.5 9.5 L11.5 12 M11.5 9.5 L9 12" fill="none"
        stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
</svg>
`;
// Square with an arrow exiting the top-right — "open in default app".
const EXTERNAL_SVG = `
<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14">
  <path d="M3 3 L8 3 M3 3 L3 13 L13 13 L13 8" fill="none"
        stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
  <path d="M9 3 L13 3 L13 7 M13 3 L8 8" fill="none"
        stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
</svg>
`;
const DELETE_SVG = `
<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14">
  <path d="M5 2 L11 2 L11 4 M3 4 L13 4 M5 4 L5 14 L11 14 L11 4" fill="none"
        stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>
`;
// Plan 29-06 — speech bubble + small replay arrow inside, "open debrief".
const DEBRIEF_SVG = `
<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14">
  <path d="M2.5 3 L13.5 3 Q14 3 14 3.5 L14 10 Q14 10.5 13.5 10.5 L7 10.5 L4.5 13 L4.5 10.5 L2.5 10.5 Q2 10.5 2 10 L2 3.5 Q2 3 2.5 3 Z"
        fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
  <path d="M6.5 6.5 L8.5 6.5 L8.5 5 L10.5 7 L8.5 9 L8.5 7.5 L6.5 7.5 Z"
        fill="currentColor" />
</svg>
`;

const CSS = `
  .vmx-rec-row {
    position: relative;
    display: flex;
    flex-direction: column;
    background: var(--glass-2);
    border-bottom: 1px solid var(--glass-edge);
    transition: background var(--motion-snap) ease-out;
    cursor: pointer;
    outline: none;
  }
  .vmx-rec-row:hover {
    background: rgba(214, 207, 199, 0.06);  /* silk-22 lower-alpha — documented exception (UI-SPEC §Color) */
  }
  .vmx-rec-row__head {
    display: flex;
    align-items: center;
    min-height: 44px;            /* a11y touch target — documented exception */
    padding: 0 var(--sp-3);
    gap: var(--sp-2);
  }
  .vmx-rec-row__ts {
    flex: 0 0 140px;
    font-family: var(--type-mono);
    font-size: 12px;
    font-weight: 500;
    color: var(--silk-65);
    font-variant-numeric: tabular-nums;
    user-select: none;
  }
  .vmx-rec-row__meta {
    flex: 1 1 auto;
    font-family: var(--type-body);
    font-size: 14px;
    color: var(--silk);
    display: flex;
    align-items: center;
    user-select: none;
  }
  .vmx-rec-row__crashed-led {
    display: inline-block;
    width: 5px;
    height: 5px;
    background: var(--led-warn);
    border-radius: 50%;
    margin-right: var(--sp-2);
    vertical-align: baseline;
    box-shadow: 0 0 4px var(--led-warn);
  }
  .vmx-rec-row__actions {
    /* Plan 15-03 Task 2: was 64px (replay + delete only); grew to 128px to
       host 4 buttons × 24px + 3 gaps × 8px = 120px + 8px breathing room.
       Order left→right: replay · reveal · open-external · delete. */
    flex: 0 0 128px;
    display: flex;
    flex-direction: row;
    justify-content: flex-end;
    gap: var(--sp-2);
  }
  .vmx-rec-row__btn {
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: none;
    color: var(--silk-65);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: color var(--motion-snap) ease-out, filter var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  /* Info-button hover (replay + reveal + open-external) — silk-65→amber
     ink-flip with a faint drop-shadow halo. UI-SPEC §Color reserved-amber
     list: replay-hover (1), reveal-hover (2 — Plan 15-03 expansion),
     open-external-hover (3 — Plan 15-03 expansion). */
  .vmx-rec-row__btn[data-kind="replay"]:hover,
  .vmx-rec-row__btn[data-kind="reveal"]:hover,
  .vmx-rec-row__btn[data-kind="open-external"]:hover,
  .vmx-rec-row__btn[data-kind="debrief"]:not(:disabled):hover {
    color: var(--amber);
    filter: drop-shadow(var(--glow-faint));
  }
  /* Plan 29-06 — disabled debrief button (short or eventless session)
     dims at 50% per CDJ Whisper restraint + sets the not-allowed cursor.
     No glow on hover. */
  .vmx-rec-row__btn[data-kind="debrief"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .vmx-rec-row__btn[data-kind="delete"] {
    color: var(--silk-40);
  }
  .vmx-rec-row__btn[data-kind="delete"]:hover {
    color: var(--led-fault);
    box-shadow: inset 0 0 8px rgba(212, 65, 58, 0.18);  /* destructive-hover exception (UI-SPEC §Color) */
    border-radius: var(--rad-sm);
  }
  /* Expand pattern: parent grid animates grid-template-rows 0fr to 1fr;
   * inner keeps constant padding so the open/close stays off the layout
   * property axis. Parent's overflow: hidden clips the inner while the
   * row is collapsed. min-height: 0 on the inner lets the grid child
   * shrink below its content size. */
  .vmx-rec-row__expand {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 250ms ease-out;
    overflow: hidden;
  }
  .vmx-rec-row__expand[data-open="true"] {
    grid-template-rows: 1fr;
  }
  .vmx-rec-row__expand-inner {
    min-height: 0;
    padding: var(--sp-4);
    background: var(--glass-3);
    border-top: 1px solid var(--amber-22);
    box-shadow: inset 0 1px 0 var(--glass-top);
    max-height: 40vh;
    overflow-y: auto;
  }
  .vmx-rec-row__audio {
    width: 100%;
    accent-color: var(--amber);
    display: block;
    margin-bottom: var(--sp-3);
  }
  .vmx-rec-row__transcript {
    display: flex;
    flex-direction: column;
  }
  .vmx-rec-evt {
    line-height: 1.45;
    padding: var(--sp-1) 0;
    font-family: var(--type-body);
    font-size: 13px;
  }
  .vmx-rec-evt--bold {
    color: var(--silk);
    border-left: 1px solid var(--amber-22);
    padding-left: var(--sp-3);
  }
  .vmx-rec-evt--dim {
    color: var(--silk-40);
  }
  .vmx-rec-evt__ts {
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--silk-40);
    font-variant-numeric: tabular-nums;
    margin-right: var(--sp-2);
  }
  @media (prefers-reduced-motion: reduce) {
    .vmx-rec-row__expand,
    .vmx-rec-row__expand-inner { transition: none; }
    .vmx-rec-row__expand[data-open="false"] .vmx-rec-row__expand-inner { display: none; }
  }
`;

registerStyle("vmx-rec-row", CSS);

export function renderRecordingRow(opts: RecordingRowProps): RecordingRowHandle {
  const { summary, onToggle, onDelete } = opts;
  const resolveWavPath = opts.absoluteWavPathResolver
    ?? ((sd: string) => `${sd}/voice.wav`);

  const root = document.createElement("div");
  root.className = "vmx-rec-row";
  root.setAttribute("role", "button");
  root.setAttribute("aria-expanded", "false");
  root.setAttribute(
    "aria-label",
    `session ${formatTimestamp(summary.started_at_iso)}, `
    + `${formatDuration(summary.duration_s)}, ${summary.event_count} events`,
  );
  root.tabIndex = 0;
  root.dataset.open = "false";
  root.dataset.crashed = summary.crashed ? "true" : "false";

  // --- Header row (3 cells) ---
  const head = document.createElement("div");
  head.className = "vmx-rec-row__head";

  const tsCell = document.createElement("div");
  tsCell.className = "vmx-rec-row__ts";
  tsCell.textContent = formatTimestamp(summary.started_at_iso);
  head.append(tsCell);

  const metaCell = document.createElement("div");
  metaCell.className = "vmx-rec-row__meta";

  if (summary.crashed) {
    const led = document.createElement("span");
    led.className = "vmx-rec-row__crashed-led";
    led.setAttribute("aria-hidden", "true");
    metaCell.append(led);
  }

  // Center label: "{duration} · {N} events".
  const metaText = document.createElement("span");
  metaText.textContent
    = `${formatDuration(summary.duration_s)} · ${summary.event_count} events`;
  metaCell.append(metaText);

  head.append(metaCell);

  const actions = document.createElement("div");
  actions.className = "vmx-rec-row__actions";

  const replayBtn = document.createElement("button");
  replayBtn.type = "button";
  replayBtn.className = "vmx-rec-row__btn";
  replayBtn.dataset.kind = "replay";
  replayBtn.setAttribute(
    "aria-label",
    `replay session ${formatTimestamp(summary.started_at_iso)}`,
  );
  replayBtn.innerHTML = REPLAY_SVG;
  replayBtn.addEventListener("click", (e) => {
    // Replay-button click also toggles expansion (UI-SPEC §Interaction
    // Contracts — Enter on replay icon toggles row).
    e.stopPropagation();
    onToggle();
  });
  actions.append(replayBtn);

  // Plan 15-03 Task 2 — reveal-in-OS (Finder/Explorer) icon button.
  // Per CLAUDE.md §Constraints (macOS + Windows in v1) the aria-label uses
  // "Finder" since macOS is the v0.1.0-rc1 launch target; Plan 15-04 polish
  // wave may platform-detect and swap copy.
  const revealBtn = document.createElement("button");
  revealBtn.type = "button";
  revealBtn.className = "vmx-rec-row__btn";
  revealBtn.dataset.kind = "reveal";
  revealBtn.setAttribute(
    "aria-label",
    `reveal session ${formatTimestamp(summary.started_at_iso)} in Finder`,
  );
  revealBtn.innerHTML = REVEAL_SVG;
  revealBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    revealInOS(summary.session_dir).catch((err) => {
      // eslint-disable-next-line no-console
      console.error("revealInOS failed:", err);
    });
  });
  actions.append(revealBtn);

  // Plan 15-03 Task 2 — open input.wav in OS default audio app.
  const openExtBtn = document.createElement("button");
  openExtBtn.type = "button";
  openExtBtn.className = "vmx-rec-row__btn";
  openExtBtn.dataset.kind = "open-external";
  openExtBtn.setAttribute(
    "aria-label",
    `open input.wav for session ${formatTimestamp(summary.started_at_iso)} in default app`,
  );
  openExtBtn.innerHTML = EXTERNAL_SVG;
  openExtBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    openInputWav(summary.session_dir).catch((err) => {
      // eslint-disable-next-line no-console
      console.error("openInputWav failed:", err);
    });
  });
  actions.append(openExtBtn);

  // Plan 29-06 — Open Debrief button. Slots between open-external and
  // delete. Disabled when the session is too short (< 5 min) OR has
  // too few events (< 5) per CONTEXT D-11 + RESEARCH Pitfall 6.
  const debriefBtn = document.createElement("button");
  debriefBtn.type = "button";
  debriefBtn.className = "vmx-rec-row__btn";
  debriefBtn.dataset.kind = "debrief";
  const tooShort = summary.duration_s < 300;
  const noEvents = summary.event_count < 5;
  const debriefDisabled = tooShort || noEvents;
  debriefBtn.disabled = debriefDisabled;
  if (tooShort) {
    debriefBtn.title = "Session too short for debrief (need ≥ 5 minutes)";
  } else if (noEvents) {
    debriefBtn.title = "No event data for debrief";
  } else {
    debriefBtn.title = "Open debrief";
  }
  debriefBtn.setAttribute(
    "aria-label",
    `open debrief for session ${formatTimestamp(summary.started_at_iso)}`,
  );
  debriefBtn.innerHTML = DEBRIEF_SVG;
  debriefBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (debriefBtn.disabled) return;
    invoke("open_debrief_window", { sessionDir: summary.session_dir }).catch(
      (err: unknown) => {
        // eslint-disable-next-line no-console
        console.error("open_debrief_window failed:", err);
      },
    );
  });
  actions.append(debriefBtn);

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "vmx-rec-row__btn";
  deleteBtn.dataset.kind = "delete";
  deleteBtn.setAttribute(
    "aria-label",
    `delete session ${formatTimestamp(summary.started_at_iso)}`,
  );
  deleteBtn.innerHTML = DELETE_SVG;
  deleteBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    onDelete();
  });
  // Keyboard: Enter on the focused delete button fires onDelete.
  deleteBtn.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      e.stopPropagation();
      onDelete();
    }
  });
  actions.append(deleteBtn);

  head.append(actions);
  root.append(head);

  // Row body click → toggle (excluding action cluster which stopPropagates).
  head.addEventListener("click", (e) => {
    // If the click bubbled from inside the actions cluster, skip — the
    // button handlers above already fired.
    const target = e.target as HTMLElement;
    if (actions.contains(target)) return;
    onToggle();
  });

  // Keyboard: Enter / Space on the row toggles. (Delete button's handler
  // stops propagation so the row's listener does NOT also fire onToggle.)
  root.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onToggle();
    }
  });

  // --- Expand panel (built lazily on first setExpanded(true)) ---
  const expand = document.createElement("div");
  expand.className = "vmx-rec-row__expand";
  expand.dataset.open = "false";
  root.append(expand);

  let inner: HTMLElement | null = null;
  let audioEl: HTMLAudioElement | null = null;
  let transcriptEl: HTMLElement | null = null;
  // Each setExpanded(true) call starts a fresh fetch — increment the token
  // so any in-flight resolver from a prior open knows it was superseded.
  let fetchToken = 0;

  function buildInnerIfNeeded(): HTMLElement {
    if (inner !== null) return inner;
    inner = document.createElement("div");
    inner.className = "vmx-rec-row__expand-inner";
    expand.append(inner);
    return inner;
  }

  function mountAudio(innerEl: HTMLElement): void {
    if (audioEl !== null) return;
    audioEl = document.createElement("audio");
    audioEl.className = "vmx-rec-row__audio";
    audioEl.controls = true;
    audioEl.preload = "metadata";
    audioEl.src = convertFileSrc(resolveWavPath(summary.session_dir));
    innerEl.append(audioEl);
  }

  function mountLoadingTranscript(innerEl: HTMLElement): void {
    transcriptEl = document.createElement("div");
    transcriptEl.className = "vmx-rec-row__transcript";
    const loading = document.createElement("div");
    loading.className = "vmx-rec-evt vmx-rec-evt--dim";
    loading.textContent = "Loading events…";
    transcriptEl.append(loading);
    innerEl.append(transcriptEl);
  }

  function renderTranscriptEvents(
    events: Array<{ t: number; kind: string; [k: string]: unknown }>,
  ): void {
    if (transcriptEl === null) return; // collapsed mid-fetch — no-op
    transcriptEl.replaceChildren();
    for (const evt of events) {
      const { label, emphasis } = deriveEventLabel(evt);
      const line = document.createElement("div");
      line.className = `vmx-rec-evt vmx-rec-evt--${emphasis}`;
      const tsSpan = document.createElement("span");
      tsSpan.className = "vmx-rec-evt__ts";
      tsSpan.textContent = formatRelativeTimestamp(evt.t);
      line.append(tsSpan);
      const labelSpan = document.createElement("span");
      labelSpan.textContent = label;
      line.append(labelSpan);
      transcriptEl.append(line);
    }
  }

  function renderTranscriptError(): void {
    if (transcriptEl === null) return;
    transcriptEl.replaceChildren();
    const err = document.createElement("div");
    err.className = "vmx-rec-evt vmx-rec-evt--dim";
    err.textContent = "Events unavailable.";
    transcriptEl.append(err);
  }

  function tearDownAudio(): void {
    if (audioEl === null) return;
    try {
      audioEl.pause();
    } catch {
      /* jsdom may throw if not playing */
    }
    audioEl.removeAttribute("src");
    try {
      audioEl.load();
    } catch {
      /* jsdom may not implement HTMLMediaElement.load() */
    }
    audioEl.remove();
    audioEl = null;
  }

  function tearDownTranscript(): void {
    if (transcriptEl !== null) {
      transcriptEl.remove();
      transcriptEl = null;
    }
  }

  function setExpanded(open: boolean): void {
    if (open) {
      const innerEl = buildInnerIfNeeded();
      // Defensive: clear any stale children from a prior open cycle.
      if (audioEl === null && transcriptEl === null) {
        // Both refs null → fresh open.
        mountAudio(innerEl);
        mountLoadingTranscript(innerEl);
      } else {
        // Either ref non-null from prior open without an intervening close —
        // re-use as-is.
        mountAudio(innerEl);
        if (transcriptEl === null) mountLoadingTranscript(innerEl);
      }
      expand.dataset.open = "true";
      root.dataset.open = "true";
      root.setAttribute("aria-expanded", "true");

      // Fire the events fetch; the resolver checks the closure refs so a
      // mid-fetch collapse is safe.
      fetchToken += 1;
      const thisToken = fetchToken;
      sendIpcRequest(
        "ipc.recordings.events",
        { session_dir: summary.session_dir },
        "ipc.recordings.events_result",
      ).then(
        (resp) => {
          if (thisToken !== fetchToken) return; // superseded by a later open
          if (transcriptEl === null) return;     // collapsed
          const payload = (resp as { payload?: { events?: unknown } }).payload;
          const events = Array.isArray(payload?.events)
            ? (payload!.events as Array<{ t: number; kind: string; [k: string]: unknown }>)
            : [];
          renderTranscriptEvents(events);
        },
        () => {
          if (thisToken !== fetchToken) return;
          if (transcriptEl === null) return;
          renderTranscriptError();
        },
      );
    } else {
      tearDownAudio();
      tearDownTranscript();
      expand.dataset.open = "false";
      root.dataset.open = "false";
      root.setAttribute("aria-expanded", "false");
      // Bump the token so any in-flight fetch from the open we just closed
      // becomes a no-op when it eventually resolves.
      fetchToken += 1;
    }
  }

  function setAudioSrc(absoluteWavPath: string): void {
    if (audioEl !== null) {
      audioEl.src = convertFileSrc(absoluteWavPath);
    }
  }

  return { root, setExpanded, setAudioSrc };
}
