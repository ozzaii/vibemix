/* cohost.ts — full right column: transcript header + receipt-paper
 * transcript + foot status (UI-SPEC §§9-11).
 *
 * The transcript is the second "paper" surface — locally-scoped
 * `--paper-receipt-*` CSS custom properties carry the only non-charcoal,
 * non-amber colour values in the right column. Per UI-SPEC §Color these
 * are intentionally OUT of the dark-only palette to evoke a receipt-paper
 * printout — the cohost's voice rendered as ink-on-paper.
 *
 * Lifted verbatim from mocks/vibemix-app-ui.html `.cohost-panel`,
 * `.cohost-header`, `.transcript`, `.cohost-foot` (lines 956-1112).
 *
 * Phase 13-03: the 42×42 mascot placeholder bubble was removed from the
 * transcript header — the mascot lives ONLY as the Phase 13 always-on-top
 * overlay window (see 13-CONTEXT.md Open Q 2: "corner dropped entirely").
 * The freed vertical space gives the meters + transcript more breathing
 * room.
 *
 * Components:
 *   - "AVERY" Workbench 13px name + LISTENING/TALKING/IDLE status row
 *     (single horizontal row, left-aligned, no leading bubble)
 *   - Receipt-paper transcript with `.now / .faded / .old` line classes
 *   - Foot strip: GROUNDED / WARMING UP indicator + DSEG7 latency readout
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
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border: 1px solid var(--bezel-1);
    border-radius: 8px;
    position: relative;
    overflow: hidden;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }
  .vmx-cohost__header {
    padding: 14px var(--sp-md);
    display: flex;
    align-items: center;
    gap: var(--sp-md);
    border-bottom: 1px solid var(--bezel-1);
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    position: relative;
  }
  .vmx-cohost__meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .vmx-cohost__name {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 13px;
    color: var(--phosphor);
    letter-spacing: 0.08em;
    text-shadow: var(--phosphor-glow);
    line-height: 1;
  }
  .vmx-cohost__status {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    color: var(--ink-dim);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 5px;
    line-height: 1;
  }
  .vmx-cohost__status-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink-engraved);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .vmx-cohost__status[data-state="LISTENING"] .vmx-cohost__status-led {
    background: var(--ok);
    box-shadow: 0 0 6px var(--ok);
  }
  .vmx-cohost__status[data-state="TALKING"] .vmx-cohost__status-led {
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
  /* === Transcript (paper surface — locally-scoped vars per UI-SPEC §Color) === */
  .vmx-cohost__transcript {
    --paper-receipt-top: #f3ead7;
    --paper-receipt-bot: #ece2c8;
    --paper-receipt-ink: #1a1408;
    --paper-receipt-ink-old: #5a4a30;
    --paper-receipt-ink-older: #7a6749;
    --paper-receipt-ts-bg: rgba(40, 28, 15, 0.06);
    --paper-receipt-ts-ink: #8a7c5e;
    --paper-receipt-em: #a8540a;
    flex: 1;
    padding: 18px 18px 24px;
    background: linear-gradient(180deg, var(--paper-receipt-top) 0%, var(--paper-receipt-bot) 100%);
    border: 0;
    color: var(--paper-receipt-ink);
    font-family: "DM Mono", monospace;
    font-size: 13.5px;
    line-height: 1.55;
    letter-spacing: 0.005em;
    position: relative;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .vmx-cohost__transcript::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='p'><feTurbulence type='fractalNoise' baseFrequency='.75' numOctaves='2'/><feColorMatrix values='0 0 0 0 .4  0 0 0 0 .32  0 0 0 0 .2  0 0 0 .24 0'/></filter><rect width='180' height='180' filter='url(%23p)'/></svg>");
    mix-blend-mode: multiply;
    opacity: 0.55;
  }
  .vmx-cohost__transcript::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 18px;
    background:
      linear-gradient(180deg, transparent, rgba(40, 28, 15, 0.18)),
      radial-gradient(circle at 9px 18px, transparent 4px, var(--paper-receipt-bot) 4.5px) repeat-x;
    background-size: auto, 18px 18px;
    pointer-events: none;
  }
  .vmx-cohost__msg {
    margin-bottom: 14px;
    padding-left: 20px;
    position: relative;
    letter-spacing: 0.005em;
  }
  .vmx-cohost__msg::before {
    content: "›";
    position: absolute;
    left: 0;
    top: 0;
    color: var(--phosphor-warm);
    font-weight: 700;
    font-family: "Workbench", "Courier New", monospace;
  }
  .vmx-cohost__msg[data-tier="now"] {
    color: var(--paper-receipt-ink);
  }
  .vmx-cohost__msg[data-tier="now"]::after {
    content: "▍";
    display: inline;
    margin-left: 2px;
    color: var(--phosphor-warm);
    animation: vmx-cohost-cursor 1000ms steps(1) infinite;
  }
  .vmx-cohost__msg[data-tier="faded"] {
    color: var(--paper-receipt-ink-old);
  }
  .vmx-cohost__msg[data-tier="old"] {
    color: var(--paper-receipt-ink-older);
    opacity: 0.7;
  }
  .vmx-cohost__ts {
    display: inline-block;
    font-family: "DM Mono", monospace;
    font-size: 9px;
    letter-spacing: 0.18em;
    color: var(--paper-receipt-ts-ink);
    background: var(--paper-receipt-ts-bg);
    padding: 1px 5px;
    border-radius: 2px;
    margin-right: 6px;
    vertical-align: 1px;
    text-transform: uppercase;
  }
  .vmx-cohost__msg em {
    font-family: "Caveat", "DM Mono", monospace;
    font-size: 17px;
    font-style: normal;
    color: var(--paper-receipt-em);
    font-weight: 700;
  }
  @keyframes vmx-cohost-cursor {
    50% { opacity: 0; }
  }
  /* === Foot strip === */
  .vmx-cohost__foot {
    padding: 10px var(--sp-md);
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border-top: 1px solid var(--bezel-1);
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9.5px;
    letter-spacing: 0.18em;
    color: var(--ink-dim);
    text-transform: uppercase;
    line-height: 1;
  }
  .vmx-cohost__foot-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink-engraved);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .vmx-cohost__foot[data-grounded="true"] .vmx-cohost__foot-led {
    background: var(--ok);
    box-shadow: 0 0 6px var(--ok);
  }
  .vmx-cohost__foot[data-grounded="false"] .vmx-cohost__foot-led {
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
  .vmx-cohost__foot-latency {
    margin-left: auto;
    font-family: "DSEG7", "DM Mono", monospace;
    font-size: 13px;
    color: var(--phosphor);
    text-shadow: 0 0 4px var(--phosphor-dim);
    letter-spacing: 0.06em;
  }
`;

registerStyle("vmx-cohost", CSS);

export function renderCohostPanel(props: CohostPanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-cohost";
  root.setAttribute("aria-label", "ai cohost");

  root.append(buildHeader(props.status));
  root.append(buildTranscript(props.transcript));
  root.append(buildFoot(props.grounded, props.latencyMs));

  return root;
}

function buildHeader(status: CohostStatus): HTMLElement {
  const head = document.createElement("header");
  head.className = "vmx-cohost__header";

  // Phase 13-03: mascot bubble dropped — the AVERY chip is the only header
  // content now. The mascot lives in the always-on-top overlay window.
  const meta = document.createElement("div");
  meta.className = "vmx-cohost__meta";
  const name = document.createElement("span");
  name.className = "vmx-cohost__name";
  name.textContent = "AVERY";
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

function buildFoot(grounded: boolean, latencyMs: number | null): HTMLElement {
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

  const right = document.createElement("span");
  right.className = "vmx-cohost__foot-latency";
  right.title = "last reaction latency";
  right.textContent = formatLatency(latencyMs);
  foot.append(right);

  return foot;
}

function formatLatency(ms: number | null): string {
  if (ms == null) return "—";
  const sec = ms / 1000;
  return `${sec.toFixed(2)} s`;
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
    const lat = foot.querySelector<HTMLElement>(".vmx-cohost__foot-latency");
    if (lat) lat.textContent = formatLatency(props.latencyMs);
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
