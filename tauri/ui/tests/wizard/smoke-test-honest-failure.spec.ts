/**
 * @vitest-environment jsdom
 *
 * The smoke test's whole job is to PROVE the voice plays. It used to render
 * the exact success surface ("READY TO PLAY", armed CTA) when the voice check
 * failed, and shipped a 3-bar "audio meter" hardcoded at 40/70/55% that lit
 * whether audio played or not. Failure now has its own surface and the fake
 * instrument is gone.
 */

import { describe, expect, it, vi } from "vitest";

import { renderSmokeTest } from "../../src/wizard/smoke-test.js";

const cb = { onReplay: vi.fn(), onOpenVibemix: vi.fn() };

describe("smoke-test honest failure", () => {
  it("failure renders its own surface, never the success celebration", () => {
    const el = renderSmokeTest({ greetingPlayed: true, failed: true }, cb);
    document.body.append(el);
    expect(el.textContent).toContain("VOICE CHECK DIDN'T PLAY");
    expect(el.textContent).not.toContain("READY TO PLAY");
    expect(el.textContent).toContain("Retry");
    expect(el.querySelector(".smoke-test")?.getAttribute("data-failed")).toBe("true");
    // Escape hatch stays: Open vibemix remains armed even on failure.
    const cta = Array.from(el.querySelectorAll<HTMLButtonElement>("button")).find((b) =>
      (b.textContent ?? "").includes("Open vibemix"),
    );
    expect(cta?.disabled).toBe(false);
  });

  it("success keeps the celebration and the replay link", () => {
    const el = renderSmokeTest({ greetingPlayed: true, failed: false }, cb);
    expect(el.textContent).toContain("READY TO PLAY");
    expect(el.textContent).toContain("Replay");
    expect(el.querySelector(".smoke-test")?.getAttribute("data-failed")).toBe("false");
  });

  it("the static 3-bar meter is gone — no instrument paints un-probed level", () => {
    const el = renderSmokeTest({ greetingPlayed: false, failed: false }, cb);
    expect(el.querySelector(".smoke-test__meter")).toBeNull();
    expect(el.querySelector(".smoke-test__meter-bar")).toBeNull();
  });
});
