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
  .vmx-drop-chip {
    margin-top: 16px;
    display: inline-flex;
    align-items: center;
    gap: var(--sp-md);
    padding: 10px var(--sp-md);
    background: linear-gradient(180deg, var(--bezel-1) 0%, var(--panel-pressed-bottom) 100%);
    border: 1px solid var(--phosphor-dim);
    border-radius: 6px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      var(--phosphor-glow);
    position: relative;
    animation: vmx-drop-pulse var(--bpm-period-ms, 500ms) ease-in-out infinite;
  }
  .vmx-drop-chip::before {
    content: "";
    position: absolute;
    inset: -1px;
    border-radius: 7px;
    background: linear-gradient(180deg, transparent 30%, var(--phosphor-soft));
    z-index: -1;
    filter: blur(8px);
    pointer-events: none;
  }
  .vmx-drop-chip__arrow {
    font-family: "DSEG7", "DM Mono", monospace;
    color: var(--phosphor);
    font-size: 14px;
    line-height: 1;
  }
  .vmx-drop-chip__count {
    font-family: "DSEG7", "DM Mono", monospace;
    font-size: 22px;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    letter-spacing: 0.06em;
    line-height: 1;
  }
  .vmx-drop-chip__lbl {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.28em;
    color: var(--ink-dim);
    text-transform: uppercase;
    line-height: 1;
  }
  .vmx-drop-chip[data-bars="0"] {
    border-color: var(--rec);
    animation: vmx-drop-rec-flash 220ms ease-out 1;
  }
  .vmx-drop-chip[data-bars="0"] .vmx-drop-chip__count,
  .vmx-drop-chip[data-bars="0"] .vmx-drop-chip__arrow {
    color: var(--rec);
    text-shadow: 0 0 8px var(--rec);
  }
  @keyframes vmx-drop-pulse {
    0%, 100% {
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.06),
        var(--phosphor-glow);
    }
    50% {
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.08),
        var(--phosphor-halo);
    }
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

  const arrow = document.createElement("span");
  arrow.className = "vmx-drop-chip__arrow";
  arrow.textContent = "⟶";
  arrow.setAttribute("aria-hidden", "true");
  root.append(arrow);

  const count = document.createElement("span");
  count.className = "vmx-drop-chip__count";
  count.textContent = formatBars(props.bars);
  root.append(count);

  const lbl = document.createElement("span");
  lbl.className = "vmx-drop-chip__lbl";
  lbl.textContent = "BARS TO DROP";
  root.append(lbl);

  return root;
}

function formatBars(bars: number): string {
  // Bars formatted as "{bars}:00" — eighths placeholder per UI-SPEC §7.
  // Phase 12-04 may extend to true sub-bar tracking; for now the count is bar-aligned.
  const safe = Math.max(0, Math.floor(bars));
  return `${String(safe).padStart(2, "0")}:00`;
}
