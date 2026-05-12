/* meter.ts — vertical 16-segment LED meter (UI-SPEC §4).
 *
 * Each meter is 56px wide × 200px tall: a --panel-deep frame with 16
 * stacked LED segments (bottom 5 --ok, middle 8 --phosphor-warm, top 3
 * --phosphor for clip warning) plus a separate peak-hold segment that
 * floats above the current level.
 *
 * Layout-thrash-free update path: the caller writes a single CSS custom
 * property to the meter root — `--meter-rms` (0..1) and `--meter-peak`
 * (0..1). Each segment is positioned bottom-up at index N (1..16) and
 * lit when `--meter-rms * 16 >= N`. We can't do `>` in pure CSS, so the
 * segments are pre-positioned and JS sets a `data-lit-count` attribute
 * on the root (0..16) — a single attribute write per frame, the browser
 * repaints the LEDs.
 *
 * Peak-hold is rendered as a 17th "needle" segment that absolutely-
 * positions itself via the inline `--meter-peak-pct` style — set by the
 * caller; CSS does the translate.
 *
 * The component re-renders ZERO of its DOM after mount. Updates happen
 * exclusively through `setMeterLevels(el, {rms, peak})`. */

import { registerStyle } from "./_style-registry.js";

export type MeterLabel = "music" | "voice" | "mic";

export interface MeterProps {
  label: MeterLabel;
}

const SEGMENT_COUNT = 16;

const CSS = `
  .vmx-meter {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-sm);
    width: 56px;
  }
  .vmx-meter__frame {
    position: relative;
    width: 56px;
    height: 200px;
    background: var(--panel-deep);
    border: 1px solid var(--bezel-1);
    border-radius: 4px;
    box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.7);
    padding: 4px;
    display: flex;
    flex-direction: column-reverse;
    gap: 2px;
    overflow: hidden;
  }
  .vmx-meter__seg {
    flex: 1;
    width: 100%;
    border-radius: 1.5px;
    background: var(--ink-engraved);
    transition: background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                opacity var(--motion-snap) ease-out;
    opacity: 0.45;
  }
  /* Lit colour mapping by segment index (1=bottom, 16=top).
   * Bottom 5: --ok (safe headroom)
   * Middle 8: --phosphor-warm
   * Top 3:    --phosphor (clip warning) */
  .vmx-meter__seg[data-zone="safe"][data-lit="true"] {
    background: var(--ok);
    box-shadow: 0 0 4px var(--ok);
    opacity: 1;
  }
  .vmx-meter__seg[data-zone="warm"][data-lit="true"] {
    background: var(--phosphor-warm);
    box-shadow: 0 0 4px var(--phosphor-warm);
    opacity: 1;
  }
  .vmx-meter__seg[data-zone="clip"][data-lit="true"] {
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
    opacity: 1;
  }
  .vmx-meter__peak {
    position: absolute;
    left: 4px;
    right: 4px;
    height: 3px;
    border-radius: 1.5px;
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
    bottom: calc(var(--meter-peak-pct, 0) * (100% - 8px));
    opacity: var(--meter-peak-shown, 0);
    transition: bottom 80ms ease-out,
                opacity 1200ms ease-out;
    pointer-events: none;
  }
  .vmx-meter__label {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-dim);
    line-height: 1;
  }
`;

registerStyle("vmx-meter", CSS);

function zoneFor(index: number): "safe" | "warm" | "clip" {
  // index 1..16 — 1 is bottom (safe), 16 is top (clip).
  if (index <= 5) return "safe";
  if (index <= 13) return "warm";
  return "clip";
}

export function renderMeter(props: MeterProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-meter";
  root.dataset.label = props.label;
  root.dataset.litCount = "0";
  root.setAttribute("aria-label", `${props.label} level meter`);

  const frame = document.createElement("div");
  frame.className = "vmx-meter__frame";

  // Bottom-up index: segments[0] is the bottom segment (index 1, safe).
  for (let i = 1; i <= SEGMENT_COUNT; i++) {
    const seg = document.createElement("div");
    seg.className = "vmx-meter__seg";
    seg.dataset.index = String(i);
    seg.dataset.zone = zoneFor(i);
    seg.dataset.lit = "false";
    frame.append(seg);
  }

  const peak = document.createElement("div");
  peak.className = "vmx-meter__peak";
  peak.setAttribute("aria-hidden", "true");
  frame.append(peak);

  root.append(frame);

  const label = document.createElement("span");
  label.className = "vmx-meter__label";
  label.textContent = props.label.toUpperCase();
  root.append(label);

  return root;
}

export interface MeterLevels {
  /** 0..1 normalised RMS — clamped on write. */
  rms: number;
  /** 0..1 normalised peak. Optional; suppresses the peak needle when omitted. */
  peak?: number | null;
}

/** Idempotent hot-update — flips the data-lit attribute on each segment.
 *  Returns the number of segments lit (for tests). */
export function setMeterLevels(el: HTMLElement, levels: MeterLevels): number {
  const rms = Math.max(0, Math.min(1, levels.rms));
  const litCount = Math.round(rms * SEGMENT_COUNT);
  if (el.dataset.litCount !== String(litCount)) {
    el.dataset.litCount = String(litCount);
    const segs = el.querySelectorAll<HTMLElement>(".vmx-meter__seg");
    segs.forEach((seg) => {
      const idx = Number(seg.dataset.index ?? "0");
      seg.dataset.lit = idx <= litCount ? "true" : "false";
    });
  }

  const peakEl = el.querySelector<HTMLElement>(".vmx-meter__peak");
  if (peakEl) {
    if (levels.peak == null) {
      peakEl.style.setProperty("--meter-peak-shown", "0");
    } else {
      const peak = Math.max(0, Math.min(1, levels.peak));
      peakEl.style.setProperty("--meter-peak-pct", String(peak));
      peakEl.style.setProperty("--meter-peak-shown", peak > 0.02 ? "1" : "0");
    }
  }

  return litCount;
}
