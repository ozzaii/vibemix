/* Phase 31 Plan 02 — BaseLayer vitest spec.
 *
 * Coverage:
 *   - Default boot clip = idle_breathe.
 *   - cancel() is a no-op (P47: base never canceled).
 *   - play() swaps the active clip.
 *   - Invalid clip throws (anti-slop discipline).
 *   - asMascotState() returns a valid MascotState idle variant.
 */

import { describe, expect, it } from "vitest";

import { BASE_PRIORITY, BaseLayer, DEFAULT_BASE_CLIP } from "./base.js";
import { STATE_CLASS } from "../types.js";

describe("BaseLayer — construction", () => {
  it("defaults to idle_breathe", () => {
    const base = new BaseLayer();
    expect(base.currentClip()).toBe(DEFAULT_BASE_CLIP);
    expect(DEFAULT_BASE_CLIP).toBe("idle_breathe");
  });

  it("BASE_PRIORITY is locked at 50", () => {
    expect(BASE_PRIORITY).toBe(50);
  });

  it("accepts an alternate initial clip", () => {
    const base = new BaseLayer("idle_bop_to_beat_mellow");
    expect(base.currentClip()).toBe("idle_bop_to_beat_mellow");
  });

  it("throws on invalid initial clip (anti-slop)", () => {
    expect(
      () =>
        new BaseLayer(
          // @ts-expect-error — invalid clip on purpose.
          "not_an_idle_clip",
        ),
    ).toThrow(/invalid initial clip/i);
  });
});

describe("BaseLayer.cancel — never canceled (Pitfall P47)", () => {
  it("cancel() does not change the current clip", () => {
    const base = new BaseLayer("idle_bop_to_beat_energetic");
    base.cancel();
    expect(base.currentClip()).toBe("idle_bop_to_beat_energetic");
  });
});

describe("BaseLayer.play — swap", () => {
  it("swaps the active clip", () => {
    const base = new BaseLayer();
    base.play("idle_bop_to_beat_mellow");
    expect(base.currentClip()).toBe("idle_bop_to_beat_mellow");
  });

  it("throws on invalid clip (anti-slop)", () => {
    const base = new BaseLayer();
    expect(() =>
      base.play(
        // @ts-expect-error — invalid clip on purpose.
        "dance_a",
      ),
    ).toThrow(/invalid clip/i);
  });
});

describe("BaseLayer — MascotState integration", () => {
  it("asMascotState() returns a state whose STATE_CLASS is 'idle'", () => {
    const base = new BaseLayer();
    const state = base.asMascotState();
    expect(STATE_CLASS[state]).toBe("idle");
  });
});
