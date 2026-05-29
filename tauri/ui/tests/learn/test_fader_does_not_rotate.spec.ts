// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-02 — fader regression guard.
//
// Phase 91 REVIEW.md CR-02 (BLOCKER): every fader group (vol:*, xfader,
// tempo:*) carries `data-cx`/`data-cy` for the original rotation-pivot
// design, so `applyPositionFrame` rotated the WHOLE fader group instead of
// translating the thumb. The pitch slider from value=64 (straight) to
// value=127 (top) made the on-screen fader rotate from 0° to +135°. The
// existing highlight-latency test only exercised eq_hi:A (a knob), so the
// regression was invisible to CI.
//
// This spec pins the CR-02 fix and its follow-up: faders must NOT receive a
// `rotate(...)` transform on the parent group, but the visible thumb should
// translate along the rail. Knobs continue to rotate. Buttons continue to set
// `data-active`.

import { describe, it, expect } from "vitest";
import { applyPositionFrame } from "../../src/learn/components/controller-stage";

function lastRect(group: SVGGElement): SVGRectElement {
  const rects = Array.from(group.querySelectorAll(":scope > rect"));
  const thumb = rects[rects.length - 1];
  expect(thumb).not.toBeUndefined();
  return thumb as SVGRectElement;
}

function makeStage(): HTMLElement {
  // Tiny synthetic SVG covering one of each control-type. We use the FLX4
  // geometry as the reference because it's the canonical golden + the
  // controller Kaan ear-tests on.
  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <svg viewBox="0 0 1200 600" xmlns="http://www.w3.org/2000/svg">
      <!-- Knob (rotate path) -->
      <g data-control-id="eq_hi:A" data-cx="500" data-cy="200">
        <circle cx="500" cy="200" r="22"/>
      </g>
      <!-- Vertical channel fader (translate / data-value path) -->
      <g data-control-id="vol:A" data-cx="580" data-cy="430">
        <rect x="573" y="220" width="14" height="220"/>
        <rect x="565" y="420" width="30" height="18"/>
      </g>
      <!-- Vertical pitch / tempo fader (translate / data-value path) -->
      <g data-control-id="tempo:A" data-cx="395" data-cy="320">
        <rect x="388" y="220" width="14" height="200"/>
        <rect x="382" y="312" width="26" height="16"/>
      </g>
      <!-- Horizontal crossfader (translate / data-value path) -->
      <g data-control-id="xfader" data-cx="640" data-cy="540">
        <rect x="490" y="533" width="300" height="14"/>
        <rect x="632" y="525" width="16" height="30"/>
      </g>
      <!-- Button (data-active path; even with data-cx/cy it MUST NOT rotate) -->
      <g data-control-id="play:A" data-cx="200" data-cy="430">
        <rect x="170" y="410" width="60" height="40"/>
      </g>
      <!-- Jog-touch button (wire spellings jog_touched:A and jog:A must normalise) -->
      <g data-control-id="jog_touch:A" data-cx="265" data-cy="280">
        <circle cx="265" cy="280" r="100"/>
      </g>
    </svg>
  `;
  return wrapper;
}

describe("test_fader_does_not_rotate.spec.ts (CR-02 regression guard)", () => {
  it("vol:A — fader gets data-value, never a rotate transform", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { "vol:A": 100 });
    const g = stage.querySelector(
      '[data-control-id="vol:A"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    // The CR-02 bug: pre-fix, transform was `rotate((100/127)*270-135 580 430)`.
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    // The CR-02 fix: data-value carries the wire value for CSS / follow-up.
    expect(g.getAttribute("data-value")).toBe("100");
    const thumb = lastRect(g);
    expect(thumb.getAttribute("data-fader-thumb")).toBe("true");
    expect(thumb.getAttribute("transform")).toMatch(/^translate\(0 -/);
  });

  it("xfader — crossfader gets data-value, never a rotate transform", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { xfader: 32 });
    const g = stage.querySelector(
      '[data-control-id="xfader"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    expect(g.getAttribute("data-value")).toBe("32");
    const thumb = lastRect(g);
    expect(thumb.getAttribute("data-fader-thumb")).toBe("true");
    expect(thumb.getAttribute("transform")).toMatch(/^translate\(-/);
  });

  it("tempo:A — pitch fader thumb translates, never rotating the group", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { "tempo:A": 127 });
    const g = stage.querySelector(
      '[data-control-id="tempo:A"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    expect(g.getAttribute("data-value")).toBe("127");
    const thumb = lastRect(g);
    expect(thumb.getAttribute("data-fader-thumb")).toBe("true");
    expect(thumb.getAttribute("transform")).toBe("translate(0 -92)");
  });

  it("eq_hi:A — knob STILL rotates (the working path is preserved)", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { "eq_hi:A": 127 });
    const g = stage.querySelector(
      '[data-control-id="eq_hi:A"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    const t = g.getAttribute("transform") ?? "";
    expect(t).toMatch(/rotate\(/);
    // (127/127)*270 - 135 = 135°, pivoted at (500, 200).
    expect(t).toMatch(/135\s+500\s+200/);
    // Knob must NOT receive a stray data-value (that's the fader path).
    expect(g.getAttribute("data-value")).toBeNull();
  });

  it("play:A — button flips data-active; never rotates (pre-fix it rotated ~2° per click)", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { "play:A": 1 });
    const g = stage.querySelector(
      '[data-control-id="play:A"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    expect(g.getAttribute("data-active")).toBe("1");

    applyPositionFrame(stage, { "play:A": 0 });
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    expect(g.getAttribute("data-active")).toBe("0");
  });

  it("jog_touched:A wire-key normalises to jog_touch:A button (no rotation)", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { "jog_touched:A": 1 });
    const g = stage.querySelector(
      '[data-control-id="jog_touch:A"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    expect(g.getAttribute("data-active")).toBe("1");
  });

  it("jog:A relative-move wire-key normalises to jog_touch:A pulse", () => {
    const stage = makeStage();
    applyPositionFrame(stage, { "jog:A": 127 });
    const g = stage.querySelector(
      '[data-control-id="jog_touch:A"]',
    ) as SVGGElement;
    expect(g).not.toBeNull();
    expect(g.getAttribute("transform") ?? "").not.toMatch(/rotate/);
    expect(g.getAttribute("data-active")).toBe("1");

    applyPositionFrame(stage, { "jog:A": 0 });
    expect(g.getAttribute("data-active")).toBe("0");
  });
});
