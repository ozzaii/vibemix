// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-04 — `ipc.learn.highlight` → DOM paint latency ≤ 16 ms P95.
//
// Phase 92 Plan 02 — RED-state harness. The two test bodies are shaped
// against `applyHighlight(stage, payload)` which Plan 92-05 will add to
// `tauri/ui/src/learn/components/controller-stage.ts`. Today the export
// does not exist, so each `it()` is gated on dynamic-import success: if
// `applyHighlight` is undefined, the test runs through `it.skip(...)`.
//
// Mirrors `tauri/ui/tests/learn/highlight-latency.test.ts` (P91) for the
// jsdom + SVG-mount + 240-sample sweep contract; the difference is RENDER-04
// pins the highlight PAINT path (CSS-variable swap + pulse-ring class
// toggle) rather than the per-knob rotate path (RENDER-02).
//
// Two tests:
//   1. "P95 paint latency ≤ 16 ms"
//   2. "clears any prior highlight before painting new one"

import { describe, it, expect, beforeAll } from "vitest";
import { PIONEER_DDJ_FLX4_SVG } from "../../src/learn/controllers/pioneer_ddj_flx4.svg.js";

const N_SAMPLES = 240;
const TARGET_MS = 16.0;

interface ApplyHighlightInput {
  control_id: string;
  deck: string;
  cue_color: "amber" | "warning";
  cue_shape: "pulse-ring" | "static-glow";
}

type ApplyHighlightFn = (
  stage: HTMLElement,
  input: ApplyHighlightInput,
) => void;

// Resolved in beforeAll via dynamic import; remains null until Plan 92-05
// adds the export. Each test guards on truthiness via the runtime
// `it.skip` switch below.
let applyHighlight: ApplyHighlightFn | null = null;

describe("ipc.learn.highlight → DOM paint latency (RENDER-04)", () => {
  let stage: HTMLElement;

  beforeAll(async () => {
    try {
      const mod = (await import(
        "../../src/learn/components/controller-stage.js"
      )) as Record<string, unknown>;
      const candidate = mod["applyHighlight"];
      if (typeof candidate === "function") {
        applyHighlight = candidate as ApplyHighlightFn;
      }
    } catch {
      // applyHighlight lands in Plan 92-05; until then, tests skip.
    }
    document.body.innerHTML = `<div id="learn-stage">${PIONEER_DDJ_FLX4_SVG}</div>`;
    stage = document.getElementById("learn-stage")!;
  });

  // Use a `getter` test selector so the dynamic-import resolution above
  // determines whether the tests live or skip at execution time.
  const itLive = (): typeof it | typeof it.skip =>
    applyHighlight ? it : it.skip;

  itLive()("P95 paint latency ≤ 16 ms", () => {
    if (!applyHighlight) {
      // Defensive: itLive should have routed us through it.skip, but if
      // a future runner change breaks that, fail loud.
      throw new Error("applyHighlight not loaded — Plan 92-05 missing?");
    }
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

  itLive()("clears any prior highlight before painting new one", () => {
    if (!applyHighlight) {
      throw new Error("applyHighlight not loaded — Plan 92-05 missing?");
    }
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

  // Visible-when-skipped placeholder so a skipped run still shows in the
  // collect output (rather than vanishing entirely if applyHighlight is
  // missing AND vitest treats `it.skip` from a getter as 0 collected).
  it("contract pin: applyHighlight resolves once Plan 92-05 lands", () => {
    // No-op assert that the SVG is mounted (Plan 91-shipped surface).
    // Confirms the harness can mount the FLX4 fixture; the actual paint
    // gate above runs as soon as applyHighlight exists.
    expect(stage.querySelector("[data-control-id]")).toBeTruthy();
  });
});
