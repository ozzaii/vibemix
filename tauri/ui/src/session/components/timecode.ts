/* timecode.ts — center column timecode block (UI-SPEC §5).
 *
 * Layout: a panel with "TIMECODE" Workbench 9px header, then the DSEG7
 * hero numeric (88px, --phosphor + --phosphor-halo + 6%-opacity 88:88
 * underlay) and a meta row beneath with BPM / KEY / DECK labels.
 *
 * Lifted verbatim from mocks/vibemix-app-ui.html `.timecode-block`
 * (lines 717-789). Pure-function: idempotent re-renders happen via
 * setTimecode(el, state) which pokes textContent only — no DOM rebuild,
 * no layout thrash. The 250ms rAF cadence is owned by SessionLayout. */

import { registerStyle } from "./_style-registry.js";

export interface TimecodeProps {
  clock: string;
  bpm: number | null;
  key: string | null;
  deck: string | null;
}

const CSS = `
  .vmx-timecode {
    position: relative;
    background: linear-gradient(180deg, var(--panel-deep) 0%, var(--groove) 100%);
    border: 1px solid var(--bezel-2);
    border-radius: 8px;
    padding: 22px 24px 18px;
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.9),
      inset 0 0 0 1px var(--phosphor-soft),
      0 1px 0 rgba(255, 255, 255, 0.04);
    overflow: hidden;
  }
  .vmx-timecode::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(ellipse at 50% 60%, var(--phosphor-soft), transparent 60%);
    opacity: 0.4;
  }
  .vmx-timecode__lbl {
    position: relative;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--ink-dim);
    margin-bottom: var(--sp-sm);
    display: flex;
    align-items: center;
    gap: var(--sp-sm);
    line-height: 1;
  }
  .vmx-timecode__hero {
    position: relative;
    font-family: "DSEG7", "DM Mono", monospace;
    font-size: 88px;
    line-height: 1;
    color: var(--phosphor);
    text-shadow: var(--phosphor-halo), 0 0 4px var(--phosphor);
    letter-spacing: 0.04em;
    user-select: none;
  }
  .vmx-timecode__hero::before {
    /* Ghosted 88:88 underlay — sells the LCD-backlight fiction. */
    content: "88:88:88";
    position: absolute;
    inset: 0;
    color: var(--phosphor-soft);
    opacity: 0.5;
  }
  .vmx-timecode__meta {
    position: relative;
    display: flex;
    gap: var(--sp-md);
    margin-top: var(--sp-md);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 10px;
    color: var(--ink-dim);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    line-height: 1;
  }
  .vmx-timecode__meta-cell {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
  }
  .vmx-timecode__meta-cell b {
    font-family: "DM Mono", monospace;
    font-size: 14px;
    color: var(--ink);
    font-weight: 400;
    letter-spacing: 0.01em;
  }
`;

registerStyle("vmx-timecode", CSS);

export function renderTimecode(props: TimecodeProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-timecode";

  const lbl = document.createElement("div");
  lbl.className = "vmx-timecode__lbl";
  lbl.textContent = "TIMECODE";
  root.append(lbl);

  const hero = document.createElement("div");
  hero.className = "vmx-timecode__hero";
  hero.dataset.role = "clock";
  hero.textContent = props.clock;
  root.append(hero);

  const meta = document.createElement("div");
  meta.className = "vmx-timecode__meta";
  meta.append(buildCell("BPM", formatBpm(props.bpm)));
  meta.append(buildCell("KEY", props.key ?? "—"));
  meta.append(buildCell("DECK", props.deck ?? "—"));
  root.append(meta);

  return root;
}

function buildCell(label: string, value: string): HTMLElement {
  const cell = document.createElement("span");
  cell.className = "vmx-timecode__meta-cell";
  cell.dataset.role = label.toLowerCase();
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("b");
  v.textContent = value;
  cell.append(l, v);
  return cell;
}

function formatBpm(bpm: number | null): string {
  if (bpm == null) return "—";
  return Math.round(bpm).toString();
}

/** Idempotent hot-update. */
export function setTimecode(el: HTMLElement, props: TimecodeProps): void {
  const clock = el.querySelector<HTMLElement>('[data-role="clock"]');
  if (clock && clock.textContent !== props.clock) clock.textContent = props.clock;
  const bpm = el.querySelector<HTMLElement>('[data-role="bpm"] b');
  if (bpm) {
    const v = formatBpm(props.bpm);
    if (bpm.textContent !== v) bpm.textContent = v;
  }
  const key = el.querySelector<HTMLElement>('[data-role="key"] b');
  if (key) {
    const v = props.key ?? "—";
    if (key.textContent !== v) key.textContent = v;
  }
  const deck = el.querySelector<HTMLElement>('[data-role="deck"] b');
  if (deck) {
    const v = props.deck ?? "—";
    if (deck.textContent !== v) deck.textContent = v;
  }
}
