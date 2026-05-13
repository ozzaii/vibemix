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

import { registerStyle } from "./_style-registry.js";

export type CohostStatus = "LISTENING" | "TALKING" | "IDLE";

export interface TranscriptLine {
  role: "ai" | "user" | "system";
  text: string;
  ts: string;
}

export interface CohostPanelProps {
  status: CohostStatus;
  transcript: TranscriptLine[];
  latencyMs: number | null;
  grounded: boolean;
}

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
  root.append(buildHeader(props.status));
  root.append(buildTranscript(props.transcript));
  root.append(buildFoot(props.grounded));

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

function buildHeader(status: CohostStatus): HTMLElement {
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
  const led = document.createElement("span");
  led.className = "vmx-cohost__status-led";
  led.setAttribute("aria-hidden", "true");
  const lbl = document.createElement("span");
  lbl.textContent = status;
  statusEl.append(led, lbl);
  meta.append(name, statusEl);
  head.append(meta);

  return head;
}

function buildTranscript(lines: TranscriptLine[]): HTMLElement {
  const t = document.createElement("div");
  t.className = "vmx-cohost__transcript";
  t.dataset.sticky = "true";
  t.setAttribute("role", "log");
  t.setAttribute("aria-live", "polite");
  populateTranscript(t, lines);
  return t;
}

function populateTranscript(el: HTMLElement, lines: TranscriptLine[]): void {
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
  });
}

function buildFoot(grounded: boolean): HTMLElement {
  const foot = document.createElement("div");
  foot.className = "vmx-cohost__foot";
  foot.dataset.grounded = grounded ? "true" : "false";

  const led = document.createElement("span");
  led.className = "vmx-cohost__foot-led";
  led.setAttribute("aria-hidden", "true");
  foot.append(led);

  const lbl = document.createElement("span");
  lbl.className = "vmx-cohost__foot-lbl";
  lbl.textContent = grounded ? "GROUNDED ON AUDIO + SCREEN" : "WARMING UP";
  foot.append(lbl);

  return foot;
}

/** Idempotent hot-update. Rebuilds transcript content but preserves the
 *  scroll position when sticky=false. Foot + status are pokes only. */
export function setCohost(el: HTMLElement, props: CohostPanelProps): void {
  // Status
  const statusEl = el.querySelector<HTMLElement>(".vmx-cohost__status");
  if (statusEl && statusEl.dataset.state !== props.status) {
    statusEl.dataset.state = props.status;
    const lbl = statusEl.querySelector<HTMLElement>("span:last-child");
    if (lbl) lbl.textContent = props.status;
  }

  // Foot
  const foot = el.querySelector<HTMLElement>(".vmx-cohost__foot");
  if (foot) {
    foot.dataset.grounded = props.grounded ? "true" : "false";
    const footLbl = foot.querySelector<HTMLElement>(".vmx-cohost__foot-lbl");
    if (footLbl) {
      footLbl.textContent = props.grounded ? "GROUNDED ON AUDIO + SCREEN" : "WARMING UP";
    }
  }

  // Transcript — rebuild lines. Preserve scroll-anchor if not sticky.
  const tr = el.querySelector<HTMLElement>(".vmx-cohost__transcript");
  if (tr) {
    const sticky = tr.dataset.sticky !== "false";
    const prevScrollTop = tr.scrollTop;
    tr.replaceChildren();
    populateTranscript(tr, props.transcript);
    if (sticky) tr.scrollTop = tr.scrollHeight;
    else tr.scrollTop = prevScrollTop;
  }
}
