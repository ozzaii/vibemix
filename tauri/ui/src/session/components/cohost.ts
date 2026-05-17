/* cohost.ts — full right column: transcript header + transcript + foot
 * status (UI-SPEC §§9-11).
 *
 * The transcript is dark-glass (v5 — the original receipt-paper concept
 * was retired in Phase 14). Lines tier as `.now / .faded / .old` —
 * latest gets an amber left-edge insetshadow + caret, older lines fade
 * toward --silk-40.
 *
 * Phase 13-03: the 42×42 mascot placeholder bubble was removed from the
 * transcript header — the mascot lives ONLY as the Phase 13 always-on-top
 * overlay window (see 13-CONTEXT.md Open Q 2: "corner dropped entirely").
 *
 * Critique 2026-05-14: dropped the latency-in-amber readout from the foot
 * — real DJs don't read latency, and a tabular-mono number competed with
 * the drop-chip beat-pulse for attention. The foot is now GROUNDED LED +
 * single line, nothing else. Latency stays on `CohostPanelProps` for
 * callers but is unused in render.
 *
 * Components:
 *   - "AVERY" Workbench 13px name + LISTENING/TALKING/IDLE status row
 *     (single horizontal row, left-aligned, no leading bubble)
 *   - Tiered transcript (.now / .faded / .old)
 *   - Foot strip: GROUNDED / WARMING UP indicator (latency-free)
 *
 * Pure-function. Transcript handles sticky-bottom scroll behaviour: when
 * the user has scrolled up, new lines do NOT auto-scroll. We track this
 * via a `data-sticky` attribute on the transcript root; SessionLayout
 * (Wave 3) sets it false when the user manually scrolls. */

/* VIS-02 (43-02): --glow-faint on hover/focus-visible per CONTEXT.
 * The H9 retry button is the only interactive surface in the cohost
 * panel (the panel is a read-only transcript otherwise); it carries
 * the faint amber halo additively on top of its hot inset stack. */

import { registerStyle } from "./_style-registry.js";
import {
  renderCitationStrip,
  type CitationChip,
} from "./citation-strip.js";

export type CohostStatus = "LISTENING" | "TALKING" | "IDLE";

export interface TranscriptLine {
  role: "ai" | "user" | "system";
  text: string;
  ts: string;
}

/** Phase 44-03 / LAUNCH-02 — per-reaction citation chips keyed by
 *  transcript line `ts`. The cohost panel receives a map (not an
 *  array) so the chip-strip render is O(1) per transcript line — a
 *  full transcript walk on every rAF tick would be O(N×M) otherwise. */
export type ReactionsByTs = ReadonlyMap<string, readonly CitationChip[]>;

export interface CohostPanelProps {
  status: CohostStatus;
  transcript: TranscriptLine[];
  latencyMs: number | null;
  grounded: boolean;
  /** Push-to-mute state. When true, an inline "● MUTED" pill sits next to
   *  the AVERY status row so the mute is visible without scanning to the
   *  banner above the transcript. Wave 6 (impeccable critique) — closes
   *  H3 "user control & freedom" by giving cmd+m a clear visual ack.
   *  Defaults to false on existing callers via the destructure below. */
  muted?: boolean;
  /** Elapsed milliseconds since `grounded` transitioned to false. When >
   *  5000ms the foot swaps from "WARMING UP" to "COULDN'T REACH GEMINI"
   *  + retry button so the user has a recovery path. Wave 6 closes H9
   *  "error recovery". The render-loop computes this; the cohost is
   *  presentation-only. Defaults to null. */
  failureElapsedMs?: number | null;
  /** Click handler for the retry button shown after the failure threshold
   *  elapses. Wave 6 — callers wire this to whatever reconnect IPC exists
   *  (currently `restart_sidecar`; a dedicated `ipc.cohost.reconnect` is
   *  a TODO). */
  onRetry?: () => void;
  /** Phase 44-03 / LAUNCH-02 — citation chip strips keyed by transcript
   *  line `ts`. Optional + defaults to an empty map; missing keys just
   *  render the transcript line without chips (backward compat with
   *  callers that don't yet wire reactions). */
  reactions?: ReactionsByTs;
  /** Phase 44-03 / LAUNCH-02 — chip click handler. Wired by the caller
   *  to `invoke("open_debrief_window", { sessionDir, deepLink })`. When
   *  undefined the chip still renders but click is a no-op (defensive —
   *  the strip should never crash if the wiring is incomplete). */
  onChipClick?: (chip: CitationChip) => void;
}

/** Empty reactions sentinel — shared singleton so renderCohostPanel
 *  defaults don't allocate a fresh Map every call. */
const EMPTY_REACTIONS: ReactionsByTs = new Map();

const MAX_TRANSCRIPT_LINES = 200;
const FADED_WINDOW = 5;

const CSS = `
  .vmx-cohost {
    display: flex;
    flex-direction: column;
    flex: 1;
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    position: relative;
    overflow: hidden;
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.5),
      0 24px 60px rgba(0, 0, 0, 0.55);
  }
  .vmx-cohost__topstrip {
    padding: 8px var(--sp-4);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    border-bottom: 1px solid var(--glass-edge);
    background: rgba(0, 0, 0, 0.4);
    position: relative;
    z-index: 2;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-cohost__topstrip-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
  }
  .vmx-cohost__topstrip-tag::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow: var(--glow-strong);
    animation: vmx-cohost-talk-pulse 1.4s ease-in-out infinite;
  }
  .vmx-cohost__topstrip-meta {
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.08em;
    color: var(--silk-40);
    text-transform: none;
  }
  .vmx-cohost__header {
    padding: var(--sp-3) var(--sp-4);
    display: flex;
    align-items: center;
    gap: var(--sp-4);
    border-bottom: 1px solid var(--glass-edge);
    background: rgba(0, 0, 0, 0.25);
    position: relative;
    z-index: 2;
  }
  .vmx-cohost__meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  /* AVERY — display-weight character moniker, not a label. The first
   * letter gets a pale highlight (mock §03 type specimen treatment)
   * so the name reads as a co-host's signature, not status text. */
  .vmx-cohost__name {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 82, "wght" 700;
    font-size: 17px;
    color: var(--silk);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6);
    display: inline-flex;
    align-items: baseline;
    gap: 1px;
  }
  .vmx-cohost__name__lead {
    color: var(--amber);
    font-variation-settings: "wdth" 82, "wght" 800;
    text-shadow: 0 0 6px var(--amber-40), 0 0 14px var(--amber-22);
  }
  .vmx-cohost__status {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    color: var(--silk-40);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-cohost__status-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(15, 18, 24, 0.85);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .vmx-cohost__status[data-state="LISTENING"] .vmx-cohost__status-led {
    background: var(--led-ok);
    box-shadow:
      0 0 3px var(--led-ok),
      0 0 6px rgba(109, 212, 74, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  .vmx-cohost__status[data-state="TALKING"] .vmx-cohost__status-led {
    background: var(--amber);
    box-shadow: var(--glow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.3);
    animation: vmx-cohost-talk-pulse 0.9s ease-in-out infinite;
  }
  @keyframes vmx-cohost-talk-pulse {
    0%, 70% { opacity: 1; }
    85% { opacity: 0.35; }
    100% { opacity: 1; }
  }
  /* === Transcript — dark glass display (v5) === */
  .vmx-cohost__transcript {
    flex: 1;
    padding: var(--sp-4) var(--sp-4) var(--sp-5);
    background: var(--glass-3);
    border: 0;
    color: var(--silk);
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 13.5px;
    line-height: 1.55;
    letter-spacing: 0;
    position: relative;
    overflow-y: auto;
    overflow-x: hidden;
    z-index: 1;
  }
  .vmx-cohost__transcript::after {
    /* Fade to bottom — long transcripts breathe into the void */
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 32px;
    background: linear-gradient(180deg, transparent, rgba(2, 3, 6, 0.88));
    pointer-events: none;
  }
  .vmx-cohost__msg {
    margin-bottom: var(--sp-3);
    padding: 4px 8px 4px 22px;
    margin-left: -8px;
    margin-right: -4px;
    position: relative;
    letter-spacing: 0;
    border-radius: var(--rad-sm);
    transition: background 400ms ease-out, box-shadow 400ms ease-out;
  }
  .vmx-cohost__msg::before {
    content: "›";
    position: absolute;
    left: 8px;
    top: 4px;
    color: var(--amber);
    font-weight: 700;
    font-family: var(--type-mono);
    text-shadow: 0 0 4px var(--amber-22);
  }
  /* Latest line — eye is drawn via TWO amber signals only: the 1px
   * inset edge on the left and the lead glyph (defined globally on
   * .vmx-cohost__msg::before). Critique pass 2 (2026-05-14) dropped
   * the amber gradient backdrop AND the blinking cursor caret —
   * stacking 4 amber signals on a single line read louder than the
   * rest of the surface. The remaining two carry the "this is the
   * latest" semantic alone. */
  .vmx-cohost__msg[data-tier="now"] {
    color: var(--silk);
    box-shadow: inset 1px 0 0 var(--amber-40);
  }
  .vmx-cohost__msg[data-tier="faded"] {
    color: var(--silk-65);
  }
  .vmx-cohost__msg[data-tier="old"] {
    color: var(--silk-40);
  }
  .vmx-cohost__ts {
    display: inline-block;
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    color: var(--silk-40);
    background: rgba(255, 138, 61, 0.05);
    border: 1px solid var(--silk-12);
    padding: 1px 5px;
    border-radius: var(--rad-sm);
    margin-right: 6px;
    vertical-align: 1px;
    text-transform: uppercase;
  }
  .vmx-cohost__msg em {
    font-family: inherit;
    font-style: normal;
    color: var(--amber);
    font-weight: 600;
    text-shadow: 0 0 4px var(--amber-22);
  }
  /* vmx-cohost-cursor keyframe retired with the blinking caret —
   * see [data-tier="now"] above (critique pass 2). */
  /* === Foot strip === */
  .vmx-cohost__foot {
    padding: var(--sp-3) var(--sp-4);
    background: rgba(0, 0, 0, 0.4);
    border-top: 1px solid var(--glass-edge);
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    color: var(--silk-40);
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    position: relative;
    z-index: 2;
  }
  .vmx-cohost__foot-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(15, 18, 24, 0.85);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .vmx-cohost__foot[data-grounded="true"] .vmx-cohost__foot-led {
    background: var(--led-ok);
    box-shadow:
      0 0 3px var(--led-ok),
      0 0 6px rgba(109, 212, 74, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  .vmx-cohost__foot[data-grounded="false"] .vmx-cohost__foot-led {
    background: var(--amber);
    box-shadow: var(--glow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.3);
    animation: vmx-cohost-talk-pulse 1.4s ease-in-out infinite;
  }
  /* Failure state — foot[data-failed="true"] swaps the amber LED to fault
   * and renders a compact retry button. Wave 6 closes H9 "error recovery"
   * by giving the user a way out when grounding has been false for >5s. */
  .vmx-cohost__foot[data-failed="true"] .vmx-cohost__foot-led {
    background: var(--led-fault);
    box-shadow:
      0 0 3px var(--led-fault),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
    animation: vmx-cohost-talk-pulse 1.4s ease-in-out infinite;
  }
  .vmx-cohost__foot[data-failed="true"] .vmx-cohost__foot-lbl {
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.28), 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-cohost__foot-retry {
    margin-left: auto;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 4px 10px;
    border: 1px solid var(--amber-40);
    border-radius: var(--rad-sm);
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 12px var(--amber-22);
    cursor: pointer;
    line-height: 1;
    text-shadow: 0 0 4px var(--amber-65);
    transition: border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  /* VIS-02 (43-02) — retry button keeps its existing amber inset
   * stack and additively gains --glow-faint as an outer halo on
   * hover/focus-visible. The button only renders during the H9
   * "couldn't reach gemini" failure window so the glow reads as a
   * recovery affordance, not a routine hover. */
  .vmx-cohost__foot-retry:hover,
  .vmx-cohost__foot-retry:focus-visible {
    border-color: var(--amber);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 var(--amber-65),
      inset 0 0 18px var(--amber-40),
      var(--glow-faint);
  }
  .vmx-cohost__foot-retry:focus-visible { outline: none; }
  /* MUTED pill — sits inside the cohost header next to the AVERY status
   * row. Same dome-LED + Saira-9-022 vocabulary as the titlebar pills,
   * fault-tinted. Wave 6 closes H3 "user control & freedom" — cmd+m
   * gets a visible ack without scanning to the banner. */
  .vmx-cohost__muted-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    margin-left: auto;
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(212, 65, 58, 0.35);
    border-radius: var(--rad-sm);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--led-fault);
    line-height: 1;
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.28), 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-cohost__muted-pill-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--led-fault);
    box-shadow:
      0 0 3px var(--led-fault),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
    animation: vmx-cohost-talk-pulse 1.4s ease-in-out infinite;
  }
`;

registerStyle("vmx-cohost", CSS);

export function renderCohostPanel(props: CohostPanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-cohost";
  root.setAttribute("aria-label", "ai cohost");

  // Critique 2026-05-14: the cohost no longer carries its own
  // border-anim sweep. The SessionLayout root already breathes
  // (one CDJ, one breathing light); a second sweep on the right column
  // diluted the sign-of-life into a nervous tic. The glass-fingerprint
  // streak was also dropped (texture-as-decoration → AI-defaultism).
  //
  // The cohost reads as a quiet inner glass tile inside the breathing
  // session shell.

  root.append(buildTopStrip());
  root.append(buildHeader(props.status, props.muted ?? false));
  root.append(
    buildTranscript(
      props.transcript,
      props.reactions ?? EMPTY_REACTIONS,
      props.onChipClick,
    ),
  );
  root.append(
    buildFoot(
      props.grounded,
      props.failureElapsedMs ?? null,
      props.onRetry,
    ),
  );

  return root;
}

function buildTopStrip(): HTMLElement {
  const strip = document.createElement("div");
  strip.className = "vmx-cohost__topstrip";
  const tag = document.createElement("span");
  tag.className = "vmx-cohost__topstrip-tag";
  tag.textContent = "AI COHOST";
  const meta = document.createElement("span");
  meta.className = "vmx-cohost__topstrip-meta";
  meta.textContent = "grounded · audio + screen";
  strip.append(tag, meta);
  return strip;
}

function buildHeader(status: CohostStatus, muted: boolean): HTMLElement {
  const head = document.createElement("header");
  head.className = "vmx-cohost__header";

  // Phase 13-03: mascot bubble dropped — the AVERY chip is the only header
  // content now. The mascot lives in the always-on-top overlay window.
  const meta = document.createElement("div");
  meta.className = "vmx-cohost__meta";
  // AVERY rendered as a display moniker — first letter highlighted in
  // amber as the character's accent stroke.
  const name = document.createElement("span");
  name.className = "vmx-cohost__name";
  const lead = document.createElement("span");
  lead.className = "vmx-cohost__name__lead";
  lead.textContent = "A";
  const rest = document.createElement("span");
  rest.textContent = "VERY";
  name.append(lead, rest);
  const statusEl = document.createElement("span");
  statusEl.className = "vmx-cohost__status";
  statusEl.dataset.state = status;
  // Wave 6 (H6 recognition over recall) — native browser tooltip on
  // hover. aria-label kept identical for screen readers.
  statusEl.setAttribute("title", titleForStatus(status));
  statusEl.setAttribute("aria-label", titleForStatus(status));
  const led = document.createElement("span");
  led.className = "vmx-cohost__status-led";
  led.setAttribute("aria-hidden", "true");
  const lbl = document.createElement("span");
  lbl.textContent = status;
  statusEl.append(led, lbl);
  meta.append(name, statusEl);
  head.append(meta);

  // Wave 6 (H3) — inline MUTED pill. Renders only when muted=true.
  // setCohost mounts/unmounts via the same path so diff-renders flip it.
  if (muted) {
    head.append(buildMutedPill());
  }

  return head;
}

function buildMutedPill(): HTMLElement {
  const pill = document.createElement("span");
  pill.className = "vmx-cohost__muted-pill";
  pill.setAttribute("role", "status");
  pill.setAttribute("aria-live", "polite");
  pill.setAttribute(
    "title",
    "cohost is muted. press the push-to-mute hotkey to resume.",
  );
  const dot = document.createElement("span");
  dot.className = "vmx-cohost__muted-pill-led";
  dot.setAttribute("aria-hidden", "true");
  const lbl = document.createElement("span");
  lbl.textContent = "MUTED";
  pill.append(dot, lbl);
  return pill;
}

function titleForStatus(status: CohostStatus): string {
  switch (status) {
    case "LISTENING":
      return "AVERY is listening to the room";
    case "TALKING":
      return "AVERY is talking. mic auto-gated until they finish.";
    case "IDLE":
      return "AVERY is idle. waiting for an event to react to.";
  }
}

function buildTranscript(
  lines: TranscriptLine[],
  reactions: ReactionsByTs,
  onChipClick: ((chip: CitationChip) => void) | undefined,
): HTMLElement {
  const t = document.createElement("div");
  t.className = "vmx-cohost__transcript";
  t.dataset.sticky = "true";
  t.setAttribute("role", "log");
  t.setAttribute("aria-live", "polite");
  populateTranscript(t, lines, reactions, onChipClick);
  return t;
}

function populateTranscript(
  el: HTMLElement,
  lines: TranscriptLine[],
  reactions: ReactionsByTs,
  onChipClick: ((chip: CitationChip) => void) | undefined,
): void {
  // Cap to last MAX_TRANSCRIPT_LINES. Tier: last line `.now`, next FADED_WINDOW
  // are `.faded`, everything older is `.old`.
  const capped = lines.slice(-MAX_TRANSCRIPT_LINES);
  const total = capped.length;
  capped.forEach((line, idx) => {
    const msg = document.createElement("div");
    msg.className = "vmx-cohost__msg";
    msg.dataset.role = line.role;
    const fromEnd = total - 1 - idx;
    let tier: "now" | "faded" | "old" = "old";
    if (fromEnd === 0) tier = "now";
    else if (fromEnd >= 1 && fromEnd <= FADED_WINDOW) tier = "faded";
    msg.dataset.tier = tier;
    if (line.ts) {
      const ts = document.createElement("span");
      ts.className = "vmx-cohost__ts";
      ts.textContent = line.ts;
      msg.append(ts);
    }
    const body = document.createElement("span");
    body.className = "vmx-cohost__msg-body";
    body.textContent = line.text;
    msg.append(body);
    el.append(msg);

    // Phase 44-03 / LAUNCH-02 — chip strip below AI reactions only.
    // User + system lines never carry citations. The strip mounts as a
    // sibling of .vmx-cohost__msg so the renderer can hot-swap chips
    // independently of the message body if needed (v2.x). For v1 the
    // chip strip is rebuilt alongside the transcript via setCohost().
    if (line.role === "ai") {
      const chips = reactions.get(line.ts);
      if (chips && chips.length > 0) {
        const strip = renderCitationStrip({
          chips: chips as CitationChip[],
          // Defensive: a missing handler renders the chip but no-ops on
          // click — the ws-bridge gate is the source of truth for chip
          // visibility; click wiring lives in the caller (SessionLayout).
          onChipClick: onChipClick ?? (() => {}),
        });
        if (strip) el.append(strip);
      }
    }
  });
}

/** Wave 6 (H9) — threshold (ms) after which a sustained grounded=false
 *  flips the foot from "WARMING UP" to "COULDN'T REACH GEMINI" + retry.
 *  Exported for the spec's fake-timer assertions. */
export const GROUNDING_FAILURE_MS = 5000;

function buildFoot(
  grounded: boolean,
  failureElapsedMs: number | null,
  onRetry: (() => void) | undefined,
): HTMLElement {
  const foot = document.createElement("div");
  foot.className = "vmx-cohost__foot";
  foot.dataset.grounded = grounded ? "true" : "false";
  const failed = !grounded && (failureElapsedMs ?? 0) >= GROUNDING_FAILURE_MS;
  foot.dataset.failed = failed ? "true" : "false";

  const led = document.createElement("span");
  led.className = "vmx-cohost__foot-led";
  led.setAttribute("aria-hidden", "true");
  foot.append(led);

  const lbl = document.createElement("span");
  lbl.className = "vmx-cohost__foot-lbl";
  lbl.textContent = footLabelFor(grounded, failed);
  foot.append(lbl);
  // Wave 6 (H6 recognition over recall) — native browser tooltip on
  // hover explaining the LED state.
  foot.setAttribute("title", footTooltipFor(grounded, failed));

  if (failed) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "vmx-cohost__foot-retry";
    retry.textContent = "↻ RETRY";
    retry.setAttribute("aria-label", "retry connecting to gemini");
    retry.setAttribute("title", "retry connecting to gemini");
    if (onRetry) {
      retry.addEventListener("click", (e) => {
        e.preventDefault();
        onRetry();
      });
    }
    foot.append(retry);
  }

  return foot;
}

function footLabelFor(grounded: boolean, failed: boolean): string {
  if (grounded) return "GROUNDED ON AUDIO + SCREEN";
  if (failed) return "COULDN'T REACH GEMINI";
  return "WARMING UP";
}

function footTooltipFor(grounded: boolean, failed: boolean): string {
  if (grounded) {
    return "grounded on audio + screen capture. cohost can hear you.";
  }
  if (failed) {
    return "couldn't reach gemini. press retry to reconnect.";
  }
  return "warming up. initializing audio + screen capture.";
}

/** Idempotent hot-update. Rebuilds transcript content but preserves the
 *  scroll position when sticky=false. Foot + status are pokes only. */
export function setCohost(el: HTMLElement, props: CohostPanelProps): void {
  // Status
  const statusEl = el.querySelector<HTMLElement>(".vmx-cohost__status");
  if (statusEl && statusEl.dataset.state !== props.status) {
    statusEl.dataset.state = props.status;
    const title = titleForStatus(props.status);
    statusEl.setAttribute("title", title);
    statusEl.setAttribute("aria-label", title);
    const lbl = statusEl.querySelector<HTMLElement>("span:last-child");
    if (lbl) lbl.textContent = props.status;
  }

  // Muted pill mount/unmount (H3 — visual ack for cmd+m).
  const header = el.querySelector<HTMLElement>(".vmx-cohost__header");
  if (header) {
    const existing = header.querySelector<HTMLElement>(".vmx-cohost__muted-pill");
    const muted = props.muted ?? false;
    if (muted && !existing) {
      header.append(buildMutedPill());
    } else if (!muted && existing) {
      existing.remove();
    }
  }

  // Foot — grounded + failure recovery copy (H9).
  const foot = el.querySelector<HTMLElement>(".vmx-cohost__foot");
  if (foot) {
    const failed =
      !props.grounded &&
      (props.failureElapsedMs ?? 0) >= GROUNDING_FAILURE_MS;
    foot.dataset.grounded = props.grounded ? "true" : "false";
    foot.dataset.failed = failed ? "true" : "false";
    const footLbl = foot.querySelector<HTMLElement>(".vmx-cohost__foot-lbl");
    if (footLbl) footLbl.textContent = footLabelFor(props.grounded, failed);
    foot.setAttribute("title", footTooltipFor(props.grounded, failed));

    // Retry button mount/unmount.
    const existingBtn = foot.querySelector<HTMLElement>(".vmx-cohost__foot-retry");
    if (failed && !existingBtn) {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "vmx-cohost__foot-retry";
      retry.textContent = "↻ RETRY";
      retry.setAttribute("aria-label", "retry connecting to gemini");
      retry.setAttribute("title", "retry connecting to gemini");
      if (props.onRetry) {
        retry.addEventListener("click", (e) => {
          e.preventDefault();
          props.onRetry?.();
        });
      }
      foot.append(retry);
    } else if (!failed && existingBtn) {
      existingBtn.remove();
    }
  }

  // Transcript — rebuild lines. Preserve scroll-anchor if not sticky.
  // Phase 44-03 / LAUNCH-02 — chip strips rebuild alongside transcript
  // since populateTranscript() now interleaves them under AI messages.
  const tr = el.querySelector<HTMLElement>(".vmx-cohost__transcript");
  if (tr) {
    const sticky = tr.dataset.sticky !== "false";
    const prevScrollTop = tr.scrollTop;
    tr.replaceChildren();
    populateTranscript(
      tr,
      props.transcript,
      props.reactions ?? EMPTY_REACTIONS,
      props.onChipClick,
    );
    if (sticky) tr.scrollTop = tr.scrollHeight;
    else tr.scrollTop = prevScrollTop;
  }
}
