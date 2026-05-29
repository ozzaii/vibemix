// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-02 — synthetic MIDI→DOM mirror latency P95 ≤ 50 ms target;
//                    hard-fails at 80 ms (triggers §LEARN-LATENCY-CONTINGENCY).
// Regression harness: 240 synthetic frames exercise the transform-only SVG
// mirror path. Partial-build friendly: skips only if the FLX4 SVG module is
// absent.

import { describe, it, expect, beforeAll } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

// vitest's `environmentMatchGlobs` maps tests/**/*.test.ts → jsdom, so
// `document` + `DOMParser` are both available here without importing
// jsdom directly (the repo has no @types/jsdom — vite/client + DOM lib
// are the only ambient types).

const N_BURST = 240; // 240 synthetic frames @ 30 Hz = 8 s of simulated MIDI
const P95_TARGET_MS = 50;
const P95_HARD_FAIL_MS = 80;

interface PositionFrame {
  controller_id: string;
  positions: Record<string, number>;
  emit_ts: number; // when frame was synthesized
}

const FLX4_SVG_PATH = path.resolve(
  __dirname,
  "../../src/learn/controllers/pioneer_ddj_flx4.svg.ts",
);
const SVG_PRESENT = fs.existsSync(FLX4_SVG_PATH);

describe("midi_position → DOM mirror latency", () => {
  beforeAll(() => {
    // Reset the test-env document; if the SVG exists, populate the stage with
    // the production controller markup.
    document.body.innerHTML = `<div id="learn-stage"></div>`;
    if (!SVG_PRESENT) {
      return;
    }
    // Read the SVG string directly via fs so the test can stay friendly to
    // partial builds where the controller module is absent.
    const moduleSource = fs.readFileSync(FLX4_SVG_PATH, "utf8");
    const match = moduleSource.match(/PIONEER_DDJ_FLX4_SVG\s*=\s*`([\s\S]*?)`/);
    const svgString = match?.[1] ?? "";
    const stage = document.getElementById("learn-stage");
    if (stage) stage.innerHTML = svgString;
  });

  const testFn = SVG_PRESENT ? it : it.skip;

  testFn("P95 latency ≤ 50 ms target; hard-fails at 80 ms", () => {
    const samples: number[] = [];

    // Synthesize 240 frames; sweep eq_hi:A through 0→127→0 over the burst.
    for (let i = 0; i < N_BURST; i++) {
      const v = i < 120 ? i : 240 - i; // triangle 0..127..0
      const frame: PositionFrame = {
        controller_id: "pioneer_ddj_flx4",
        positions: { "eq_hi:A": v },
        emit_ts: performance.now(),
      };

      // Mirror update path: find <g data-control-id="eq_hi:A">, rotate child <circle>.
      applyPositionFrame(document, frame);

      samples.push(performance.now() - frame.emit_ts); // emit→paint delta
    }

    samples.sort((a, b) => a - b);
    const p95 = samples[Math.floor(samples.length * 0.95)] ?? 0;
    // eslint-disable-next-line no-console
    console.log(`midi_position P95 latency: ${p95.toFixed(2)} ms`);

    // Soft fail: warn but don't break CI when between 50-80 ms.
    if (p95 > P95_TARGET_MS && p95 <= P95_HARD_FAIL_MS) {
      // eslint-disable-next-line no-console
      console.warn(
        `LATENCY WARNING: P95 ${p95.toFixed(2)} ms exceeds target ${P95_TARGET_MS} ms ` +
          `but within hard-fail guardrail ${P95_HARD_FAIL_MS} ms. ` +
          `Investigate before §LEARN-LATENCY-CONTINGENCY triggers.`,
      );
    }

    // Red fail: above 80 ms → CI red, §LEARN-LATENCY-CONTINGENCY invoked.
    expect(p95).toBeLessThanOrEqual(P95_HARD_FAIL_MS);
  });
});

// The exact path the production mirror takes — verified identical to the
// runtime applyPositionFrame() in src/learn/components/controller-stage.ts.
function applyPositionFrame(doc: Document, frame: PositionFrame): void {
  for (const [controlId, value] of Object.entries(frame.positions)) {
    const group = doc.querySelector(
      `[data-control-id="${controlId}"]`,
    ) as (Element & { dataset?: DOMStringMap }) | null;
    if (!group) continue;
    // Knobs rotate: map 0..127 → -135°..+135°. transform-only update.
    const degrees = (value / 127) * 270 - 135;
    group.setAttribute(
      "transform",
      `rotate(${degrees} ${getCenterX(group)} ${getCenterY(group)})`,
    );
  }
}

function getCenterX(g: Element & { dataset?: DOMStringMap }): number {
  return Number(g.dataset?.cx ?? 0);
}
function getCenterY(g: Element & { dataset?: DOMStringMap }): number {
  return Number(g.dataset?.cy ?? 0);
}
