/* drop-chip.ts — beat-pulsed drop countdown chip (UI-SPEC §7).
 *
 * Renders ONLY when bars != null. Returns `null` when bars is null so
 * SessionLayout can simply conditionally append. When `bars === 0` the
 * chip ships with the `.rec-flash` class so the unmount-on-drop animation
 * can fire from CSS — SessionLayout removes the node afterwards.
 *
 * The beat pulse cadence is driven via `--bpm-period-ms` set as an
 * inline CSS variable by the caller. NO setInterval / setTimeout / rAF
 * inside the component — pure CSS animation. */

import { registerStyle } from "./_style-registry.js";

export interface DropChipProps {
  /** bars remaining until drop. null = hide. 0 = rec-flash. */
  bars: number | null;
  /** Beat period in ms — drives the pulse animation. Optional. */
  bpmPeriodMs?: number;
}

const CSS = `
  /* FABLE PASS (2026-06-09): the boxed gadget chip is gone. The drop count is
   * now the PHRASE LABEL riding the master groove (the mock's "drop in ~28
   * bars" position) — bare tracked mono on the void, the pips as the one lit
   * machined detail. A spec line on the faceplate, not a widget. */
  .vmx-drop-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-3);
    position: relative;
    white-space: nowrap;
  }
  /* 4-beat pip row — a small bar of dots cycling on the BPM period
   * (one full 4-beat cycle every 4 × --bpm-period-ms). Quiet but
   * unmistakable as a CDJ sync indicator. */
  .vmx-drop-chip__beats {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
    padding-left: 4px;
    border-left: 1px solid var(--amber-22);
  }
  .vmx-drop-chip__pip {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--amber-22);
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.45);
    animation: vmx-drop-pip calc(var(--bpm-period-ms, 500ms) * 4) steps(4, jump-none) infinite;
  }
  .vmx-drop-chip__pip[data-beat="2"] { animation-delay: calc(var(--bpm-period-ms, 500ms) * -3); }
  .vmx-drop-chip__pip[data-beat="3"] { animation-delay: calc(var(--bpm-period-ms, 500ms) * -2); }
  .vmx-drop-chip__pip[data-beat="4"] { animation-delay: calc(var(--bpm-period-ms, 500ms) * -1); }
  @keyframes vmx-drop-pip {
    0%,   24% {
      background: var(--amber);
      box-shadow:
        0 0 3px var(--amber-65),
        0 0 6px var(--amber-22),
        inset 0 1px 0 rgba(255, 255, 255, 0.35);
    }
    25%, 100% {
      background: var(--amber-22);
      box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.45);
    }
  }
  .vmx-drop-chip__count {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    font-size: 12px;
    color: var(--amber);
    text-shadow: 0 0 6px var(--amber-22);
    letter-spacing: 0.08em;
    line-height: 1;
  }
  .vmx-drop-chip__lbl {
    font-family: var(--type-mono);
    font-weight: 500;
    font-size: 9px;
    letter-spacing: 0.25em;
    color: var(--silk-40);
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-drop-chip[data-bars="0"] {
    animation: vmx-drop-rec-flash 220ms ease-out 1;
  }
  .vmx-drop-chip[data-bars="0"] .vmx-drop-chip__count {
    color: var(--rec);
    text-shadow: 0 0 6px rgba(212, 65, 58, 0.45);
  }
  @keyframes vmx-drop-rec-flash {
    0% { transform: scale(1); }
    50% { transform: scale(1.06); }
    100% { transform: scale(1); }
  }
`;

registerStyle("vmx-drop-chip", CSS);

/** Returns `null` when bars is null — caller appends conditionally. */
export function renderDropChip(props: DropChipProps): HTMLElement | null {
  if (props.bars == null) return null;

  const root = document.createElement("div");
  root.className = "vmx-drop-chip";
  if (props.bars === 0) root.classList.add("rec-flash");
  root.dataset.bars = String(props.bars);
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");
  if (props.bpmPeriodMs && props.bpmPeriodMs > 0) {
    root.style.setProperty("--bpm-period-ms", `${props.bpmPeriodMs}ms`);
  }

  // Label leads, count follows — reads as the mock's phrase line
  // ("drop in · 08:00"), not a gadget readout.
  const lbl = document.createElement("span");
  lbl.className = "vmx-drop-chip__lbl";
  lbl.textContent = "DROP IN";
  root.append(lbl);

  const count = document.createElement("span");
  count.className = "vmx-drop-chip__count";
  count.textContent = formatBars(props.bars);
  root.append(count);

  // 4-beat pip row — visualizes the sync period as a Pioneer-style
  // pulse train. Suppressed in REC-flash state (bars === 0) since the
  // chip is already going off in red.
  if (props.bars !== 0) {
    const beats = document.createElement("span");
    beats.className = "vmx-drop-chip__beats";
    beats.setAttribute("aria-hidden", "true");
    for (let i = 1; i <= 4; i++) {
      const pip = document.createElement("span");
      pip.className = "vmx-drop-chip__pip";
      pip.dataset.beat = String(i);
      beats.append(pip);
    }
    root.append(beats);
  }

  return root;
}

function formatBars(bars: number): string {
  // Bars formatted as "{bars}:00" — eighths placeholder per UI-SPEC §7.
  // Phase 12-04 may extend to true sub-bar tracking; for now the count is bar-aligned.
  const safe = Math.max(0, Math.floor(bars));
  return `${String(safe).padStart(2, "0")}:00`;
}
