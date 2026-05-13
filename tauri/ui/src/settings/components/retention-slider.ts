/* Phase 12 Wave 4 — retention slider (Plan 12-05 §3 RECORDING group).
 *
 * 6-stop retention discs (one per retention tier):
 *   index 0 → 1 day
 *   index 1 → 3 days
 *   index 2 → 7 days
 *   index 3 → 14 days
 *   index 4 → 30 days
 *   index 5 → ∞  (encoded on the wire as 36500 — the sentinel "never expires"
 *                value documented in 12-05-SUMMARY.md. Phase 15's cleanup
 *                policy treats >=36500 as the "keep forever" branch.)
 *
 * Visuals (UI-SPEC §13 RECORDING):
 *   - JetBrains Mono 18px tabular-nums readout above the track shows
 *     current selection (`1 D` / `3 D` / `7 D` / `14 D` / `30 D` / `INF`).
 *   - Horizontal track: 1px var(--glass-edge) recessed hairline; lit portion
 *     is a linear-gradient(90deg, var(--amber-deep), var(--amber) 70%,
 *     var(--amber-pale)) ribbon with var(--amber-22) bloom.
 *   - 6 retention discs along the track: 14×14 circle, var(--void-2) fill,
 *     1px var(--glass-edge) border, hover lifts to var(--amber-40) edge
 *     + var(--amber-22) bloom.
 *   - Active disc: solid var(--amber) fill with var(--amber-pale) edge —
 *     the lit-track portion already sells the position.
 *
 * Emits via `onChange(days)` exactly when the user clicks a disc. The
 * caller wires this to `sendSettings('retention_days', days)`.
 */

import { registerStyle } from "../../session/components/_style-registry.js";

export interface RetentionSliderProps {
  /** Current retention in days. 36500 = ∞ sentinel. */
  value: number;
  onChange: (days: number) => void;
}

export interface RetentionStop {
  index: number;
  days: number;
  label: string;
  readout: string;
}

/** The 6 fixed stops. `days` is the wire value; `label` is the small
 *  stop-label below the track; `readout` is the DSEG7 display when this
 *  stop is the active one. */
export const RETENTION_STOPS: readonly RetentionStop[] = Object.freeze([
  { index: 0, days: 1, label: "1d", readout: "1 D" },
  { index: 1, days: 3, label: "3d", readout: "3 D" },
  { index: 2, days: 7, label: "7d", readout: "7 D" },
  { index: 3, days: 14, label: "14d", readout: "14 D" },
  { index: 4, days: 30, label: "30d", readout: "30 D" },
  { index: 5, days: 36500, label: "∞", readout: "INF" },
]);

/** Map a stored `retention_days` value back into a stop index. Anything
 *  >= 36500 is the ∞ sentinel. Off-grid values snap to the nearest
 *  defined stop. */
export function daysToStopIndex(days: number): number {
  if (!Number.isFinite(days)) return RETENTION_STOPS.length - 1;
  if (days >= 36500) return RETENTION_STOPS.length - 1;
  // Find exact match first.
  const exact = RETENTION_STOPS.findIndex((s) => s.days === days);
  if (exact !== -1) return exact;
  // Snap to nearest stop.
  let best = 0;
  let bestDist = Number.POSITIVE_INFINITY;
  for (let i = 0; i < RETENTION_STOPS.length; i += 1) {
    const stop = RETENTION_STOPS[i]!;
    const dist = Math.abs(stop.days - days);
    if (dist < bestDist) {
      bestDist = dist;
      best = i;
    }
  }
  return best;
}

const CSS = `
  .vmx-retention {
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
  }
  /* Readout — recessed glass display window, JetBrains Mono tabular.
   * Matches the timecode hero clock treatment so the drawer feels of
   * the same instrument. */
  .vmx-retention__readout {
    align-self: flex-start;
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 18px;
    letter-spacing: 0.04em;
    color: var(--silk);
    line-height: 1;
    padding: 8px 12px 10px;
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid rgba(0, 0, 0, 0.55);
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.9),
      inset 0 0 0 1px rgba(0, 0, 0, 0.4),
      inset 0 0 14px rgba(255, 138, 61, 0.04),
      0 0 0 1px rgba(255, 255, 255, 0.02);
    text-shadow: 0 0 6px rgba(255, 138, 61, 0.20);
    user-select: none;
  }
  .vmx-retention__track-wrap {
    position: relative;
    height: 32px;
    display: flex;
    align-items: center;
  }
  /* Track — faint silk hairline so the path is felt at idle. Lit
   * portion is amber-22 glow gradient. */
  .vmx-retention__track {
    position: absolute;
    left: 8px;
    right: 8px;
    top: 50%;
    height: 2px;
    background:
      linear-gradient(90deg,
        rgba(214, 207, 199, 0.07) 0%,
        rgba(214, 207, 199, 0.18) 50%,
        rgba(214, 207, 199, 0.07) 100%);
    transform: translateY(-50%);
    pointer-events: none;
    border-radius: 1px;
  }
  .vmx-retention__track-lit {
    position: absolute;
    left: 8px;
    top: 50%;
    height: 3px;
    background: linear-gradient(90deg, var(--amber-deep), var(--amber) 70%, var(--amber-pale));
    transform: translateY(-50%);
    pointer-events: none;
    width: var(--vmx-retention-lit, 0%);
    transition: width var(--motion-snap) ease-out;
    border-radius: 2px;
    box-shadow: 0 0 4px var(--amber-22);
  }
  .vmx-retention__stops {
    position: relative;
    display: flex;
    justify-content: space-between;
    width: 100%;
    z-index: 1;
  }
  /* Stops — small glass-edge dome knobs. Active knob fills with amber
   * (no halation halo; the lit track does the position signal). */
  .vmx-retention__knob {
    position: relative;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--void-2);
    border: 1px solid var(--glass-edge);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.55),
      0 0 0 1px rgba(0, 0, 0, 0.45);
    cursor: pointer;
    padding: 0;
    transition: background var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                transform var(--motion-snap) ease-out;
  }
  .vmx-retention__knob:hover {
    border-color: var(--amber-40);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 rgba(0, 0, 0, 0.55),
      0 0 6px var(--amber-22);
    transform: scale(1.08);
  }
  .vmx-retention__knob[data-active="true"] {
    background: var(--amber);
    border-color: var(--amber-pale);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.35),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4),
      0 0 4px var(--amber-65),
      0 0 9px var(--amber-22);
  }
  .vmx-retention__labels {
    display: flex;
    justify-content: space-between;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    padding: 0 2px;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-retention__lbl[data-active="true"] {
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
  }
`;

registerStyle("vmx-retention", CSS);

export interface RetentionSliderHandle {
  root: HTMLElement;
  /** Update the slider to a new days value without firing onChange. */
  setValue: (days: number) => void;
}

export function renderRetentionSlider(
  props: RetentionSliderProps,
): RetentionSliderHandle {
  let activeIdx = daysToStopIndex(props.value);

  const root = document.createElement("div");
  root.className = "vmx-retention";
  root.setAttribute("role", "slider");
  root.setAttribute("aria-valuemin", "0");
  root.setAttribute(
    "aria-valuemax",
    String(RETENTION_STOPS.length - 1),
  );

  const readout = document.createElement("div");
  readout.className = "vmx-retention__readout";
  readout.textContent = RETENTION_STOPS[activeIdx]!.readout;
  root.append(readout);

  const trackWrap = document.createElement("div");
  trackWrap.className = "vmx-retention__track-wrap";

  const track = document.createElement("div");
  track.className = "vmx-retention__track";
  trackWrap.append(track);

  const trackLit = document.createElement("div");
  trackLit.className = "vmx-retention__track-lit";
  trackWrap.append(trackLit);

  const stops = document.createElement("div");
  stops.className = "vmx-retention__stops";
  const knobEls: HTMLButtonElement[] = [];
  for (const stop of RETENTION_STOPS) {
    const knob = document.createElement("button");
    knob.type = "button";
    knob.className = "vmx-retention__knob";
    knob.dataset.idx = String(stop.index);
    knob.dataset.active = stop.index === activeIdx ? "true" : "false";
    knob.setAttribute("aria-label", stop.readout);
    knob.addEventListener("click", (e) => {
      e.preventDefault();
      selectIndex(stop.index, /* fire */ true);
    });
    knobEls.push(knob);
    stops.append(knob);
  }
  trackWrap.append(stops);
  root.append(trackWrap);

  const labels = document.createElement("div");
  labels.className = "vmx-retention__labels";
  for (const stop of RETENTION_STOPS) {
    const lbl = document.createElement("span");
    lbl.className = "vmx-retention__lbl";
    lbl.dataset.idx = String(stop.index);
    lbl.dataset.active = stop.index === activeIdx ? "true" : "false";
    lbl.textContent = stop.label;
    labels.append(lbl);
  }
  root.append(labels);

  function syncLit(): void {
    // Lit portion = 0% at idx 0, 100% at last idx.
    const last = RETENTION_STOPS.length - 1;
    const pct = last === 0 ? 0 : (activeIdx / last) * 100;
    trackLit.style.setProperty("--vmx-retention-lit", `${pct}%`);
  }

  function selectIndex(idx: number, fire: boolean): void {
    if (idx < 0 || idx >= RETENTION_STOPS.length) return;
    activeIdx = idx;
    const stop = RETENTION_STOPS[idx]!;
    readout.textContent = stop.readout;
    root.setAttribute("aria-valuenow", String(idx));
    knobEls.forEach((k, i) => {
      k.dataset.active = i === idx ? "true" : "false";
    });
    labels.querySelectorAll<HTMLElement>(".vmx-retention__lbl").forEach((l, i) => {
      l.dataset.active = i === idx ? "true" : "false";
    });
    syncLit();
    if (fire) props.onChange(stop.days);
  }

  // Keyboard nav — left/right arrow keys move between stops when the
  // root has focus. Tab into the root → arrow → fire onChange.
  root.tabIndex = 0;
  root.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowRight" || ev.key === "ArrowUp") {
      ev.preventDefault();
      selectIndex(Math.min(activeIdx + 1, RETENTION_STOPS.length - 1), true);
    } else if (ev.key === "ArrowLeft" || ev.key === "ArrowDown") {
      ev.preventDefault();
      selectIndex(Math.max(activeIdx - 1, 0), true);
    }
  });

  // Initial paint of the lit-track portion.
  syncLit();
  root.setAttribute("aria-valuenow", String(activeIdx));

  return {
    root,
    setValue: (days: number) => {
      selectIndex(daysToStopIndex(days), false);
    },
  };
}
