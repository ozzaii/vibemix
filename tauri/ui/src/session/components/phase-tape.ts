/* phase-tape.ts — paper-textured horizontal phase timeline (UI-SPEC §6).
 *
 * The phase tape is one of the two "analogue interlude" surfaces in the
 * live session UI — explicitly OUT of the dark-only palette to evoke
 * reel-to-reel paper tape. Per UI-SPEC §Color/Paper Family the paper hex
 * values are scoped locally as `--paper-*` CSS custom properties on the
 * root element of this component — NOT promoted to tokens.css.
 *
 * Lifted verbatim from mocks/vibemix-app-ui.html `.phase-tape` (lines
 * 711-869). Chunks render via flex weights:
 *   silent     — flex 0.5
 *   groove     — flex 1.8, phosphor-soft tint
 *   build      — flex 1.2, striped phosphor repeating gradient + slide-arrow
 *   drop-ghost — flex 0.6, dashed border, Caveat italic label
 *
 * NOW marker absolutely positioned at `--phase-now-pct: <0..100>%` via
 * inline style — set by the caller (rAF-driven).
 *
 * Pure-function: chunks are taken as a snapshot and rendered into the
 * `.row`. Hot-update via setPhaseTape(el, {chunks, nowPct}) replaces only
 * the chunks row + nudges the marker style — no full DOM rebuild beyond
 * the chunk list. */

import { registerStyle } from "./_style-registry.js";

export type PhaseChunkKind = "silent" | "groove" | "build" | "drop-ghost";

export interface PhaseChunk {
  kind: PhaseChunkKind;
  weight: number;
  label: string;
}

export interface PhaseTapeProps {
  chunks: PhaseChunk[];
  /** 0..100 position of the NOW marker. */
  nowPct: number;
}

const CSS = `
  .vmx-phase-tape {
    --paper-tape-top: #f3ead7;
    --paper-tape-bot: #ebe0c6;
    --paper-tape-ink: #2a1f15;
    --paper-tape-edge: #2a2118;
    --paper-tape-label: #5a4a30;
    --paper-tape-chunk-silent: #8a7c5e;
    --paper-tape-chunk-groove: #5a4a30;
    --paper-tape-chunk-build: #1a1408;
    --paper-tape-chunk-drop-ghost: #a87010;
    --paper-tape-drop-border: #c8901a;
    margin-top: 18px;
    position: relative;
    height: 96px;
    background: linear-gradient(180deg, var(--paper-tape-top) 0%, var(--paper-tape-bot) 100%);
    border: 1px solid var(--paper-tape-edge);
    border-radius: 4px;
    padding: 8px 12px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.6),
      inset 0 -2px 4px rgba(0, 0, 0, 0.15),
      0 2px 6px rgba(0, 0, 0, 0.5);
    overflow: hidden;
    font-family: "DM Mono", monospace;
    color: var(--paper-tape-ink);
  }
  .vmx-phase-tape::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='p'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='1'/><feColorMatrix values='0 0 0 0 .4  0 0 0 0 .32  0 0 0 0 .2  0 0 0 .2 0'/></filter><rect width='160' height='160' filter='url(%23p)'/></svg>");
    mix-blend-mode: multiply;
    opacity: 0.5;
  }
  .vmx-phase-tape::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 6px;
    background:
      radial-gradient(circle at 8px 3px, var(--bg) 1.5px, transparent 2px) repeat-x;
    background-size: 16px 6px;
    pointer-events: none;
  }
  .vmx-phase-tape__lbl {
    position: absolute;
    top: 6px;
    left: 12px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 7.5px;
    letter-spacing: 0.32em;
    color: var(--paper-tape-label);
    text-transform: uppercase;
    line-height: 1;
  }
  .vmx-phase-tape__row {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 18px;
    height: 42px;
    position: relative;
  }
  .vmx-phase-chunk {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: "DM Mono", monospace;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    border-right: 1px solid rgba(0, 0, 0, 0.25);
    position: relative;
    font-weight: 500;
  }
  .vmx-phase-chunk[data-kind="silent"] {
    color: var(--paper-tape-chunk-silent);
    background: rgba(0, 0, 0, 0.04);
  }
  .vmx-phase-chunk[data-kind="groove"] {
    color: var(--paper-tape-chunk-groove);
    background: var(--phosphor-soft);
  }
  .vmx-phase-chunk[data-kind="build"] {
    color: var(--paper-tape-chunk-build);
    background: repeating-linear-gradient(
      45deg,
      rgba(255, 161, 46, 0.42) 0 6px,
      rgba(255, 161, 46, 0.55) 6px 12px
    );
    font-weight: 700;
  }
  .vmx-phase-chunk[data-kind="build"]::after {
    content: "⟶";
    position: absolute;
    right: 6px;
    font-size: 14px;
    color: var(--paper-tape-chunk-build);
    animation: vmx-phase-arrow 1600ms ease-in-out infinite;
  }
  @keyframes vmx-phase-arrow {
    0%, 100% { transform: translateX(0); opacity: 0.6; }
    50% { transform: translateX(3px); opacity: 1; }
  }
  .vmx-phase-chunk[data-kind="drop-ghost"] {
    border: 1.5px dashed var(--paper-tape-drop-border);
    background: rgba(255, 161, 46, 0.05);
    color: var(--paper-tape-chunk-drop-ghost);
    font-family: "Caveat", "DM Mono", monospace;
    font-style: italic;
    font-size: 13px;
    letter-spacing: 0;
    font-weight: 700;
  }
  .vmx-phase-tape__marker {
    position: absolute;
    top: 0;
    bottom: 0;
    left: var(--phase-now-pct, 50%);
    width: 2px;
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
    z-index: 2;
    pointer-events: none;
  }
  .vmx-phase-tape__marker::before {
    content: "NOW";
    position: absolute;
    top: -2px;
    left: 4px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 8px;
    letter-spacing: 0.2em;
    color: var(--rec);
    font-weight: 700;
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.6);
  }
`;

registerStyle("vmx-phase-tape", CSS);

export function renderPhaseTape(props: PhaseTapeProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-phase-tape";
  root.setAttribute("aria-label", "phase tape");

  const lbl = document.createElement("span");
  lbl.className = "vmx-phase-tape__lbl";
  lbl.textContent = "PHASE TAPE · LAST 90s";
  root.append(lbl);

  const row = document.createElement("div");
  row.className = "vmx-phase-tape__row";
  populateRow(row, props.chunks);
  root.append(row);

  const marker = document.createElement("span");
  marker.className = "vmx-phase-tape__marker";
  marker.setAttribute("aria-hidden", "true");
  setNowPct(marker, props.nowPct);
  row.append(marker);

  return root;
}

function populateRow(row: HTMLElement, chunks: PhaseChunk[]): void {
  for (const chunk of chunks) {
    const div = document.createElement("div");
    div.className = "vmx-phase-chunk";
    div.dataset.kind = chunk.kind;
    div.style.flex = String(Math.max(0.01, chunk.weight));
    div.textContent = chunk.label;
    row.append(div);
  }
}

function setNowPct(marker: HTMLElement, pct: number): void {
  const clamped = Math.max(0, Math.min(100, pct));
  marker.style.setProperty("--phase-now-pct", `${clamped}%`);
}

/** Idempotent hot-update. Re-renders chunks and re-positions the marker.
 *  Chunks list mutations happen rarely (only on phase transition); the
 *  marker pct updates each tick. */
export function setPhaseTape(el: HTMLElement, props: PhaseTapeProps): void {
  const row = el.querySelector<HTMLElement>(".vmx-phase-tape__row");
  if (!row) return;
  const marker = row.querySelector<HTMLElement>(".vmx-phase-tape__marker");
  // Diff chunks by length + kind+weight+label key — if identical, skip rebuild.
  const existing = Array.from(row.querySelectorAll<HTMLElement>(".vmx-phase-chunk"));
  const sameLen = existing.length === props.chunks.length;
  const same = sameLen && existing.every((seg, i) => {
    const c = props.chunks[i];
    return c != null
      && seg.dataset.kind === c.kind
      && seg.style.flex === String(Math.max(0.01, c.weight))
      && seg.textContent === c.label;
  });
  if (!same) {
    existing.forEach((seg) => seg.remove());
    populateRow(row, props.chunks);
    if (marker) row.append(marker);
  }
  if (marker) setNowPct(marker, props.nowPct);
}
