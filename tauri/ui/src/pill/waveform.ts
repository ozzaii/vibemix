/* Phase 62 Plan 04 — Pill TTS waveform (PILL-03).
 *
 * Reuses the session meter's design language (meter.ts / VIS-03): the same
 * amber warm-zone gradient tokens (--amber / --amber-78 / --amber-40) and the
 * SAME zero-DOM-churn `data-lit-count` + per-segment `data-lit` single-
 * attribute update path. The ONLY delta is geometry — the session meter is a
 * vertical 16-segment strip; the pill waveform is a horizontal 14-bar strip
 * sized for the 280×44 collapsed pill (62-UI-SPEC §Waveform spec).
 *
 * It is driven by the REAL voice.rms signal on the bus (Levels.update_voice AI-
 * speech RMS) — never a fake animation. index.ts feeds `setWaveform(el, rms,
 * peak)` per rAF frame during the speaking state; when voice.rms is silent
 * between phrases the bars settle to a flat low baseline (not zero), which
 * index.ts enforces by flooring the rms it passes.
 *
 * NO hand-rolled canvas / SVG (anti-pattern per 62-PATTERNS + frontend-
 * enforcement): the LED ladder is token-tested and keeps the 20/80 amber
 * discipline. Amber appears here ONLY as the lit-bar fill — one of the four
 * reserved accents.
 *
 * Update-path parity with meter.ts: setMeterLevels writes a single
 * `data-lit-count` attribute and flips each segment's `data-lit`; setWaveform
 * does the byte-identical thing for the horizontal bars.
 */

import { registerStyle } from "../session/components/_style-registry.js";

/** 14 bars — within the 62-UI-SPEC 12–16 range, fits the 280px width. */
const BAR_COUNT = 14;

const CSS = `
  .vmx-pill-wave {
    display: inline-flex;
    flex-direction: row;
    align-items: flex-end;
    gap: 2px;
    height: 16px;
    width: 100%;
    max-width: 140px;
    margin-left: auto;
  }
  .vmx-pill-wave__bar {
    flex: 1 1 0;
    min-width: 2px;
    height: 100%;
    border-radius: 1px;
    /* At rest each bar shows a faint silk hairline — the ladder is felt at
     * idle, not invisible (mirrors meter.ts seg resting treatment). */
    background: linear-gradient(180deg, var(--silk-06), var(--silk-025));
    box-shadow: inset 0 0 0 0.5px var(--seg-hi-018);
    transform-origin: bottom;
    transition: background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                opacity var(--motion-snap) ease-out;
    opacity: 0.85;
  }
  /* Lit bar — the SAME amber warm-zone gradient + glow as the session meter's
   * warm segments (meter.ts lines 113-118). 20/80: amber lives here only. */
  .vmx-pill-wave__bar[data-lit="true"] {
    opacity: 1;
    background: linear-gradient(180deg, var(--amber), var(--amber-78));
    box-shadow:
      inset 0 0 0 0.5px var(--seg-hi-12),
      0 0 4px var(--amber-40);
  }
`;

registerStyle("vmx-pill-wave", CSS);

/** Test-only — exposed so the contract test can grep the registered CSS for
 *  token usage + reject hex / non-black rgba (frontend-enforcement). Mirrors
 *  meter.ts / citation-strip.ts `_CSS_FOR_TEST`. */
export const _CSS_FOR_TEST = CSS;

/** Mount the waveform strip. Re-renders ZERO DOM after mount — updates flow
 *  exclusively through setWaveform(). */
export function renderWaveform(): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-pill-wave";
  root.dataset.litCount = "0";
  root.setAttribute("aria-hidden", "true");
  for (let i = 1; i <= BAR_COUNT; i++) {
    const bar = document.createElement("div");
    bar.className = "vmx-pill-wave__bar";
    bar.dataset.index = String(i);
    bar.dataset.lit = "false";
    root.append(bar);
  }
  return root;
}

/**
 * Idempotent hot-update — the byte-identical update path as meter.ts
 * setMeterLevels: clamp rms to 0..1, compute litCount, and only touch the DOM
 * when litCount changes (writes a single `data-lit-count` attribute, flips
 * each bar's `data-lit`). `peak` is accepted for API parity with the session
 * meter; the compact pill bars don't render a separate peak needle.
 *
 * Returns the number of lit bars (for tests).
 */
export function setWaveform(el: HTMLElement, rms: number, _peak?: number | null): number {
  const clamped = Math.max(0, Math.min(1, rms));
  const litCount = Math.round(clamped * BAR_COUNT);
  if (el.dataset.litCount !== String(litCount)) {
    el.dataset.litCount = String(litCount);
    const bars = el.querySelectorAll<HTMLElement>(".vmx-pill-wave__bar");
    bars.forEach((bar) => {
      const idx = Number(bar.dataset.index ?? "0");
      bar.dataset.lit = idx <= litCount ? "true" : "false";
    });
  }
  return litCount;
}
