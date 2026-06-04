/* meter.ts — vertical 16-segment LED meter (UI-SPEC §4).
 *
 * VIS-03 (Phase 43, Plan 43-04): hardware-LED-strip aesthetic locked.
 * - 16 discrete segments (zone bands safe/warm/clip — 1-5/6-13/14-16)
 * - amber peak-hold lozenge with 1.2s opacity decay (the single most
 *   visceral CDJ Whisper signal — never weaken its 1200ms transition
 *   or replace its amber stack)
 * - silk-12 minor grid lines at indices 4/8/12/16 (downgraded from
 *   silk-22 — the bezel detail must whisper, not compete with lit
 *   segments)
 * - token-only CSS: zero raw color literals. Every color resolves
 *   via var(--token) — see tokens.css "meter spectrum — VIS-03"
 *   block for the semantic alpha names this module consumes.
 *
 * Each meter is 56px wide × 200px tall: a --glass-3 frame with 16
 * stacked LED segments running an amber ladder that brightens upward
 * (a dim amber at the safe bottom, full amber through the warm body)
 * with --meter-clip magenta reserved for the clip zone at the top, plus
 * a separate peak-hold needle that floats above the current level.
 *
 * One-Amber restored (2026-05-26 /impeccable critique): the meter was the
 * single polychrome surface (green→amber→magenta), but it is also the
 * element a DJ glances at most, so a 3-colour ladder competed with amber's
 * "rare deck-light" meaning everywhere else. The ladder is now one amber
 * that intensifies with level; colour only changes when something is
 * wrong (magenta at clip). The peak needle stays amber — the single
 * visceral CDJ Whisper signal.
 *
 * Layout-thrash-free update path: the caller sends RMS + peak (0..1).
 * The LED fill is peak-forward, because DJs read capture confidence from
 * the same transient-heavy signal their hardware meters show. RMS alone made
 * near-red capture look like "barely hearing" while the peak needle was just a
 * thin marker. Segments are pre-positioned and JS sets a `data-lit-count`
 * attribute on the root (0..16) — a single attribute write per frame, the
 * browser repaints the LEDs.
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
const PEAK_DISPLAY_WEIGHT = 0.9;

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
      inset 0 2px 6px var(--void-85),
      inset 0 0 0 1px var(--void-50),
      0 0 0 1px var(--seg-hi-022);
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
        var(--silk-025) 0%,
        var(--silk-06) 50%,
        var(--silk-025) 100%);
    box-shadow: inset 0 0 0 0.5px var(--seg-hi-018);
    transition: background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                opacity var(--motion-snap) ease-out;
    opacity: 0.85;
  }
  /* Amber ladder (2026-05-26) — one hue, brightening with level. Safe is
   * a dim amber at the bottom, warm is full amber through the body; the
   * brightness step at segment 6 IS the band marker. Magenta is reserved
   * for the clip zone only, so colour appears exactly when something's
   * wrong. Restores the One-Amber Rule on the most-glanced surface. */
  .vmx-meter__seg[data-lit="true"] {
    opacity: 1;
    box-shadow: none;
  }
  .vmx-meter__seg[data-zone="safe"][data-lit="true"] {
    background: linear-gradient(180deg, var(--amber-78), var(--amber-40));
    box-shadow:
      inset 0 0 0 0.5px var(--seg-hi-15),
      0 0 3px var(--amber-22);
  }
  .vmx-meter__seg[data-zone="warm"][data-lit="true"] {
    background: linear-gradient(180deg, var(--amber), var(--amber-78));
    box-shadow:
      inset 0 0 0 0.5px var(--seg-hi-12),
      0 0 4px var(--amber-40);
  }
  .vmx-meter__seg[data-zone="clip"][data-lit="true"] {
    background: linear-gradient(180deg, var(--meter-clip), var(--meter-clip-deep-85));
    box-shadow:
      inset 0 0 0 0.5px var(--seg-hi-18),
      var(--meter-clip-glow);
  }
  /* Faint scale tick on every fourth segment — reads as machined
   * detail on the bezel, never competes with lit segments. VIS-03
   * downgrades from --silk-22 → --silk-12 so the minor grid lines
   * whisper. */
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
    background: var(--silk-12);
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
      inset 0 1px 0 var(--peak-hi-35);
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
    text-shadow: 0 1px 0 var(--void-70);
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
  const peak = levels.peak == null ? null : Math.max(0, Math.min(1, levels.peak));
  const displayLevel = Math.max(rms, (peak ?? 0) * PEAK_DISPLAY_WEIGHT);
  const litCount = Math.round(displayLevel * SEGMENT_COUNT);
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
    if (peak == null) {
      peakEl.style.setProperty("--meter-peak-shown", "0");
    } else {
      peakEl.style.setProperty("--meter-peak-pct", String(peak));
      peakEl.style.setProperty("--meter-peak-shown", peak > 0.02 ? "1" : "0");
    }
  }

  return litCount;
}

/**
 * Test-only export. Do not consume in app code.
 * Exposed for the VIS-03 contract tests in meter.test.ts so the suite
 * can grep the registered stylesheet for token usage (no raw
 * color literals, silk-12 grid, 1200ms peak decay) without parsing
 * document.head <style> tags from a jsdom environment.
 */
export const _CSS_FOR_TEST = CSS;
