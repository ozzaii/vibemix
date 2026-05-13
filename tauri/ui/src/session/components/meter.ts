/* meter.ts — vertical 16-segment LED meter (UI-SPEC §4).
 *
 * Each meter is 56px wide × 200px tall: a --glass-3 frame with 16
 * stacked LED segments running a Pioneer-CDJ amber ladder (safe at the
 * bottom in --amber-pale, warm through the body in --amber, clip at the
 * top in --amber-deep) plus a separate peak-hold needle that floats
 * above the current level.
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
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.022);
    padding: 4px;
    display: flex;
    flex-direction: column-reverse;
    gap: 2px;
    overflow: hidden;
  }
  .vmx-meter__seg {
    flex: 1;
    width: 100%;
    border-radius: 1px;
    position: relative;
    /* At rest each segment shows a faint silk hairline + thin centre
     * highlight — the ladder is felt at idle, not invisible. Lit
     * segments override these with the zoned amber treatment. */
    background:
      linear-gradient(90deg,
        rgba(214, 207, 199, 0.025) 0%,
        rgba(214, 207, 199, 0.06) 50%,
        rgba(214, 207, 199, 0.025) 100%);
    box-shadow: inset 0 0 0 0.5px rgba(255, 255, 255, 0.018);
    transition: background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                opacity var(--motion-snap) ease-out;
    opacity: 0.85;
  }
  /* v5 ladder — Pioneer-CDJ style. Amber gradient from deep at the top
   * (clip) to mid in the body to pale near the bottom (safe). A single
   * green hairline marks the safe/warm boundary (segment 5). */
  .vmx-meter__seg[data-lit="true"] {
    opacity: 1;
    box-shadow: none;
  }
  .vmx-meter__seg[data-zone="safe"][data-lit="true"] {
    background: linear-gradient(180deg, var(--amber-pale), rgba(255, 184, 138, 0.7));
    box-shadow:
      inset 0 0 0 0.5px rgba(255, 255, 255, 0.15),
      0 0 3px var(--amber-22);
  }
  .vmx-meter__seg[data-zone="warm"][data-lit="true"] {
    background: linear-gradient(180deg, var(--amber), rgba(255, 138, 61, 0.78));
    box-shadow:
      inset 0 0 0 0.5px rgba(255, 255, 255, 0.12),
      0 0 4px var(--amber-40);
  }
  .vmx-meter__seg[data-zone="clip"][data-lit="true"] {
    background: linear-gradient(180deg, var(--amber-deep), rgba(255, 90, 26, 0.85));
    box-shadow:
      inset 0 0 0 0.5px rgba(255, 255, 255, 0.18),
      var(--glow-soft);
  }
  /* Green hairline marker at segment 5 — the safe/warm boundary */
  .vmx-meter__seg[data-index="5"]::after {
    content: '';
    position: absolute;
    left: -1px;
    right: -1px;
    bottom: -2px;
    height: 1px;
    background: var(--led-ok);
    box-shadow: 0 0 3px var(--led-ok);
    opacity: 0.7;
    pointer-events: none;
  }
  /* Faint scale tick on every third inactive segment — reads as
   * machined detail on the bezel, never competes with lit segments. */
  .vmx-meter__seg[data-index="4"]::before,
  .vmx-meter__seg[data-index="8"]::before,
  .vmx-meter__seg[data-index="12"]::before,
  .vmx-meter__seg[data-index="16"]::before {
    content: '';
    position: absolute;
    left: -3px;
    top: 50%;
    width: 2px;
    height: 1px;
    background: var(--silk-22);
    transform: translateY(-50%);
    pointer-events: none;
  }
  /* Peak needle — a 2px amber-pale floater that hangs above the
   * current RMS. Bottom-up: at peak=1 it sits at the very top of the
   * frame. The shadow + inset highlight give it dimension; the
   * opacity transition is a 1.2s fade so peaks linger as the meter
   * recoils — pure CSS, no JS holds. */
  .vmx-meter__peak {
    position: absolute;
    left: 3px;
    right: 3px;
    height: 2px;
    border-radius: 1px;
    background: linear-gradient(180deg, var(--amber-pale), var(--amber));
    box-shadow:
      0 0 4px var(--amber-65),
      0 0 8px var(--amber-22),
      inset 0 1px 0 rgba(255, 255, 255, 0.35);
    bottom: calc(var(--meter-peak-pct, 0) * (100% - 8px));
    opacity: var(--meter-peak-shown, 0);
    transition: bottom 80ms ease-out,
                opacity 1200ms ease-out;
    pointer-events: none;
  }
  .vmx-meter__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
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
