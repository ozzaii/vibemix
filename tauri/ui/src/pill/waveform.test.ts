/**
 * @vitest-environment jsdom
 *
 * Phase 62 Plan 04 — pill waveform contract (Task 3, PILL-03).
 *
 * Pins the meter.ts reuse: the SAME data-lit update path + the amber warm-zone
 * gradient tokens, restyled to a horizontal bar strip. Mirrors the meter.test
 * / citation-strip.test `_CSS_FOR_TEST` grep pattern (frontend-enforcement
 * no-hex / amber-token discipline) + asserts the rms→lit-count update path and
 * the silent→baseline behaviour (a low non-zero rms still lights a bar).
 *
 * jsdom env: renderWaveform() calls registerStyle() (touches document.head)
 * and constructs HTMLElements.
 */

import { describe, expect, test, beforeEach } from "vitest";

import { renderWaveform, setWaveform, _CSS_FOR_TEST } from "./waveform.js";

describe("pill waveform — PILL-03 contract", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  test("renders 14 horizontal bars, all unlit at mount", () => {
    const el = renderWaveform();
    const bars = el.querySelectorAll(".vmx-pill-wave__bar");
    expect(bars.length).toBe(14);
    el.querySelectorAll<HTMLElement>(".vmx-pill-wave__bar").forEach((b) => {
      expect(b.dataset.lit).toBe("false");
    });
    expect(el.dataset.litCount).toBe("0");
  });

  test("higher rms lights more bars (rms→lit-count, real signal)", () => {
    const el = renderWaveform();
    const low = setWaveform(el, 0.2);
    const high = setWaveform(el, 0.8);
    expect(high).toBeGreaterThan(low);
    // 0.8 * 14 ≈ 11
    expect(high).toBe(Math.round(0.8 * 14));
  });

  test("data-lit-count single-attribute write reflects the lit bars", () => {
    const el = renderWaveform();
    setWaveform(el, 0.5);
    expect(el.dataset.litCount).toBe(String(Math.round(0.5 * 14)));
    const litBars = el.querySelectorAll('.vmx-pill-wave__bar[data-lit="true"]');
    expect(litBars.length).toBe(Math.round(0.5 * 14));
  });

  test("idempotent — second call with identical rms writes nothing new", () => {
    const el = renderWaveform();
    setWaveform(el, 0.5);
    const before = el.dataset.litCount;
    let mutations = 0;
    const obs = new MutationObserver((recs) => {
      mutations += recs.length;
    });
    obs.observe(el, { subtree: true, attributes: true, attributeFilter: ["data-lit"] });
    setWaveform(el, 0.5);
    obs.disconnect();
    expect(el.dataset.litCount).toBe(before);
    expect(mutations).toBe(0);
  });

  test("silent→baseline — a low non-zero rms still lights at least one bar (not zero)", () => {
    const el = renderWaveform();
    // index.ts floors the speaking rms to WAVE_BASELINE_RMS (0.06) between
    // phrases; 0.06 * 14 ≈ 1 → at least one lit bar (a flat low baseline,
    // never a dead-zero strip while speaking).
    const lit = setWaveform(el, 0.06);
    expect(lit).toBeGreaterThanOrEqual(1);
  });

  test("rms is clamped to [0,1]", () => {
    const el = renderWaveform();
    expect(setWaveform(el, -5)).toBe(0);
    expect(setWaveform(el, 99)).toBe(14);
  });

  test("non-finite rms is treated as silence", () => {
    const el = renderWaveform();
    expect(setWaveform(el, Number.NaN)).toBe(0);
    expect(el.dataset.litCount).toBe("0");
    expect(setWaveform(el, Number.POSITIVE_INFINITY)).toBe(0);
  });

  test("frontend-enforcement: zero hex literals in waveform CSS (token-only)", () => {
    expect(_CSS_FOR_TEST).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
  });

  test("frontend-enforcement: lit bar reuses the amber warm-zone gradient tokens", () => {
    const litRule = _CSS_FOR_TEST.match(
      /\.vmx-pill-wave__bar\[data-lit="true"\]\s*\{[^}]*\}/,
    );
    expect(litRule).not.toBeNull();
    // The lit-bar fill is the SAME amber warm gradient as the session meter.
    expect(litRule![0]).toMatch(/var\(--amber\)/);
    expect(litRule![0]).toMatch(/var\(--amber-78\)/);
    expect(litRule![0]).toMatch(/var\(--amber-40\)/);
  });

  test("frontend-enforcement: 20/80 — amber appears ONLY on the lit bar, not the resting bar", () => {
    const restRule = _CSS_FOR_TEST.match(
      /\.vmx-pill-wave__bar\s*\{[^}]*\}/,
    );
    expect(restRule).not.toBeNull();
    // Resting bars are silk, never amber (amber is reserved for the lit fill).
    expect(restRule![0]).not.toMatch(/var\(--amber/);
  });
});
