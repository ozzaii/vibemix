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
    margin-top: 18px;
    position: relative;
    height: 108px;
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    padding: 26px 12px 12px;
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      inset 0 0 18px rgba(255, 138, 61, 0.025),
      0 0 0 1px rgba(255, 255, 255, 0.018);
    overflow: hidden;
    font-family: var(--type-mono);
    color: var(--silk-65);
  }
  /* Recessed label strip — sits above the chunks row, not over it */
  .vmx-phase-tape::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 22px;
    background: rgba(0, 0, 0, 0.3);
    border-bottom: 1px solid rgba(0, 0, 0, 0.6);
    pointer-events: none;
  }
  .vmx-phase-tape::after {
    /* Subtle top-edge highlight + bottom amber bleed — the "display window" feel */
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.035) 0%, transparent 28%, transparent 82%, rgba(255, 138, 61, 0.022) 100%);
  }
  .vmx-phase-tape__lbl {
    position: absolute;
    top: 7px;
    left: 12px;
    right: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 8px;
    letter-spacing: 0.28em;
    color: var(--silk-40);
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    z-index: 3;
  }
  .vmx-phase-tape__lbl-right {
    color: var(--silk-22);
    font-variation-settings: "wdth" 85, "wght" 400;
    letter-spacing: 0.22em;
  }
  .vmx-phase-tape__row {
    display: flex;
    align-items: stretch;
    gap: 3px;
    height: 100%;
    position: relative;
    z-index: 1;
  }
  .vmx-phase-chunk {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    border-radius: 1px;
    position: relative;
    overflow: hidden;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-phase-chunk[data-kind="silent"] {
    color: var(--silk-22);
    background: rgba(255, 255, 255, 0.018);
  }
  .vmx-phase-chunk[data-kind="groove"] {
    color: var(--silk-65);
    background:
      linear-gradient(180deg, rgba(255, 138, 61, 0.045), rgba(255, 138, 61, 0.012)),
      rgba(255, 255, 255, 0.025);
    box-shadow: inset 0 0 0 1px rgba(255, 138, 61, 0.10);
  }
  .vmx-phase-chunk[data-kind="build"] {
    color: var(--amber-pale);
    background:
      repeating-linear-gradient(
        45deg,
        rgba(255, 138, 61, 0.18) 0 6px,
        rgba(255, 138, 61, 0.28) 6px 12px
      );
    box-shadow:
      inset 0 0 0 1px var(--amber-40),
      inset 0 0 12px var(--amber-22);
    font-variation-settings: "wdth" 85, "wght" 700;
    text-shadow: 0 0 4px var(--amber-65), 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-phase-chunk[data-kind="build"]::after {
    content: "⟶";
    position: absolute;
    right: 6px;
    font-size: 14px;
    color: var(--amber);
    text-shadow: 0 0 6px var(--amber-65);
    animation: vmx-phase-arrow 1600ms ease-in-out infinite;
  }
  @keyframes vmx-phase-arrow {
    0%, 100% { transform: translateX(0); opacity: 0.6; }
    50% { transform: translateX(3px); opacity: 1; }
  }
  .vmx-phase-chunk[data-kind="drop-ghost"] {
    border: 1px dashed var(--amber-40);
    background: rgba(255, 138, 61, 0.04);
    color: var(--amber-pale);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 100, "wght" 600;
    font-style: italic;
    font-size: 12px;
    letter-spacing: 0.05em;
    text-shadow: 0 0 4px var(--amber-22);
  }
  /* NOW marker — 1px amber needle riding the timeline + a tiny play-head
   * cap at the top so the eye lands without ambiguity. The cap is a
   * small filled triangle (pseudo-element) reading as a CDJ jog cue. */
  .vmx-phase-tape__marker {
    position: absolute;
    top: 0;
    bottom: 0;
    left: var(--phase-now-pct, 50%);
    width: 1px;
    background: var(--amber);
    box-shadow:
      0 0 4px var(--amber-65),
      0 0 10px var(--amber-22);
    z-index: 3;
    pointer-events: none;
  }
  /* Play-head cap — small inverted triangle anchored to the strip top */
  .vmx-phase-tape__marker::before {
    content: "";
    position: absolute;
    top: 22px;
    left: 50%;
    width: 0;
    height: 0;
    transform: translateX(-50%);
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid var(--amber);
    filter: drop-shadow(0 0 3px var(--amber-65)) drop-shadow(0 0 6px var(--amber-22));
  }
  /* NOW chip — sealed glass time tag riding on the marker. Sits above
   * the strip so it never collides with chunk labels below. */
  .vmx-phase-tape__marker::after {
    content: "NOW";
    position: absolute;
    top: 4px;
    left: 50%;
    transform: translateX(-50%);
    padding: 2px 6px 3px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 700;
    font-size: 8px;
    letter-spacing: 0.22em;
    color: var(--amber);
    background: var(--glass-3);
    border: 1px solid var(--amber-22);
    border-radius: 1px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 0 8px var(--amber-22),
      0 0 4px var(--amber-22);
    text-shadow: 0 0 4px var(--amber-65);
    line-height: 1;
    white-space: nowrap;
  }
`;

registerStyle("vmx-phase-tape", CSS);

export function renderPhaseTape(props: PhaseTapeProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-phase-tape";
  root.setAttribute("aria-label", "phase tape");

  const lbl = document.createElement("div");
  lbl.className = "vmx-phase-tape__lbl";
  const lblLeft = document.createElement("span");
  lblLeft.textContent = "PHASE TAPE";
  const lblRight = document.createElement("span");
  lblRight.className = "vmx-phase-tape__lbl-right";
  lblRight.textContent = "LAST 90s";
  lbl.append(lblLeft, lblRight);
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
    div.style.flexGrow = String(Math.max(0.01, chunk.weight));
    div.style.flexShrink = "1";
    div.style.flexBasis = "0";
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
      && seg.style.flexGrow === String(Math.max(0.01, c.weight))
      && seg.textContent === c.label;
  });
  if (!same) {
    existing.forEach((seg) => seg.remove());
    populateRow(row, props.chunks);
    if (marker) row.append(marker);
  }
  if (marker) setNowPct(marker, props.nowPct);
}
