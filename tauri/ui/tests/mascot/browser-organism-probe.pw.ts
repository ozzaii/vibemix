// SPDX-License-Identifier: Apache-2.0
//
// Runtime VISUAL RECEIPT for the particle organism (mask-that-highlights).
//
// Why this exists: jsdom never compiles WebGL, so the vitest suite proves the
// FocusPhase state machine but NOT that the GLSL builds, that the organism
// renders + blooms, or that the teaching-focus dissolve actually moves pixels.
// "test-passing-but-dark = 0" — so this drives `?dev=organism-probe` in real
// Chromium and reads the canvas back across two moments. It asserts:
//   1. LIT — the second frame has bright pixels (the organism rendered; the
//      shader compiled; bloom fired). A dark/blank canvas fails here.
//   2. ALIVE — a meaningful fraction of pixels changed between the two frames
//      (caused motion: breath oscillation + a focus/reform cycle). A frozen
//      canvas fails here.
//
// Grounding contract: the probe drives the organism ONLY through real
// focus/reform events, never a free animation — the motion this measures is
// the same caused motion the production path produces.

import { expect, test } from "@playwright/test";
import { PNG } from "pngjs";

/** Decode a Playwright PNG screenshot to a flat RGBA buffer + dims. */
function decode(buffer: Buffer): { width: number; height: number; data: Buffer } {
  const png = PNG.sync.read(buffer);
  return { width: png.width, height: png.height, data: png.data };
}

/** Per-pixel luma (additive particles read brightest, so luma is the signal). */
function luma(data: Buffer, i: number): number {
  // Buffer indexing is `number | undefined` under noUncheckedIndexedAccess;
  // RGBA bytes are always present for an in-bounds i, so 0 is a safe floor.
  return 0.299 * (data[i] ?? 0) + 0.587 * (data[i + 1] ?? 0) + 0.114 * (data[i + 2] ?? 0);
}

test.describe("organism runtime visual receipt", () => {
  test("the organism renders, blooms, and moves on a real focus cycle", async ({
    page,
  }) => {
    const logs: string[] = [];
    page.on("console", (msg) => {
      const t = msg.text();
      if (t.includes("organism-probe")) logs.push(t);
    });

    await page.goto("/mascot.html?dev=organism-probe");

    const canvas = page.locator("canvas").first();
    await canvas.waitFor({ state: "visible", timeout: 30_000 });
    // Let the renderer boot (assets + GPU upload) and the driver run a cycle.
    await page.waitForTimeout(4_000);

    const a = decode(await canvas.screenshot());
    // Span a focus -> reform transition (driver cycle is ~3.6s, reform at 1.8s).
    await page.waitForTimeout(1_400);
    const b = decode(await canvas.screenshot());

    expect(a.width).toBeGreaterThan(0);
    expect(a.width).toBe(b.width);
    expect(a.height).toBe(b.height);

    const total = a.width * a.height;
    let litB = 0;
    let changed = 0;
    for (let i = 0; i < b.data.length; i += 4) {
      const lb = luma(b.data, i);
      if (lb > 24) litB += 1;
      if (Math.abs(lb - luma(a.data, i)) > 14) changed += 1;
    }

    // 1. LIT — the shader compiled and the organism is on screen, not a dark box.
    expect(litB, "no lit pixels: organism did not render (shader/bloom dark)").toBeGreaterThan(
      Math.floor(total * 0.002),
    );
    // 2. ALIVE — caused motion moved a meaningful share of pixels between frames.
    expect(
      changed / total,
      "canvas is frozen: the organism is not animating on the focus cycle",
    ).toBeGreaterThan(0.005);

    // 3. The motion came through the real teaching-focus path (not a free timer).
    expect(logs.some((l) => l.includes("phase=focus"))).toBe(true);
    expect(logs.some((l) => l.includes("phase=reform"))).toBe(true);
  });
});
