// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-04 — `ipc.learn.highlight` → DOM paint latency ≤ 16 ms P95.
//
// Phase 92 Plan 05 — LIVE harness (flipped from Plan 92-02's RED-state
// dynamic-import-gated stub). `applyHighlight` is now exported from
// `controller-stage.ts`, so the previous `itLive() / it.skip` getter
// pattern (which resolved at collect-time before `beforeAll` ran and
// stayed skipped even when the export existed) is gone — a direct
// static import gives both bodies a clean live run.
//
// Mirrors `tauri/ui/tests/learn/highlight-latency.test.ts` (P91) for the
// jsdom + SVG-mount + 240-sample sweep contract; the difference is RENDER-04
// pins the highlight PAINT path (CSS-variable swap + pulse-ring class
// toggle) rather than the per-knob rotate path (RENDER-02).
//
// Three tests:
//   1. "P95 paint latency ≤ 16 ms"
//   2. "clears any prior highlight before painting new one"
//   3. "contract pin: SVG mounts"

import { describe, it, expect, beforeAll } from "vitest";
import { PIONEER_DDJ_FLX4_SVG } from "../../src/learn/controllers/pioneer_ddj_flx4.svg.js";
import { applyHighlight } from "../../src/learn/components/controller-stage.js";

const N_SAMPLES = 240;
const TARGET_MS = 16.0;

describe("ipc.learn.highlight → DOM paint latency (RENDER-04)", () => {
  let stage: HTMLElement;

  beforeAll(() => {
    document.body.innerHTML = `<div id="learn-stage">${PIONEER_DDJ_FLX4_SVG}</div>`;
    stage = document.getElementById("learn-stage")!;
  });

  it("P95 paint latency ≤ 16 ms", () => {
    const samples: number[] = [];
    const controls: Array<{ control_id: string; deck: string }> = [
      { control_id: "play", deck: "A" },
      { control_id: "play", deck: "B" },
      { control_id: "cue", deck: "A" },
      { control_id: "eq_hi", deck: "A" },
      { control_id: "vol", deck: "A" },
    ];

    for (let i = 0; i < N_SAMPLES; i++) {
      const c = controls[i % controls.length]!;
      const t0 = performance.now();
      applyHighlight(stage, {
        control_id: c.control_id,
        deck: c.deck,
        cue_color: "amber",
        cue_shape: "pulse-ring",
      });
      const t1 = performance.now();
      samples.push(t1 - t0);
    }

    samples.sort((a, b) => a - b);
    const p95 = samples[Math.floor(samples.length * 0.95)] ?? 0;
    // eslint-disable-next-line no-console
    console.log(`learn.highlight paint P95: ${p95.toFixed(3)} ms`);
    expect(p95).toBeLessThanOrEqual(TARGET_MS);
  });

  it("clears any prior highlight before painting new one", () => {
    applyHighlight(stage, {
      control_id: "play",
      deck: "A",
      cue_color: "amber",
      cue_shape: "pulse-ring",
    });
    applyHighlight(stage, {
      control_id: "cue",
      deck: "A",
      cue_color: "amber",
      cue_shape: "pulse-ring",
    });
    const lit = stage.querySelectorAll("[data-cue-color]");
    expect(lit.length).toBe(1);
    // The latest highlight should be on the cue:A group.
    expect(lit[0]?.getAttribute("data-control-id")).toBe("cue:A");
  });

  it("contract pin: SVG mounts", () => {
    // No-op assert that the SVG is mounted (Plan 91-shipped surface).
    // Confirms the harness can mount the FLX4 fixture; the actual paint
    // gates above use the same `stage` reference.
    expect(stage.querySelector("[data-control-id]")).toBeTruthy();
  });
});
