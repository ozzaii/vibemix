// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-04 / A11Y — 45 s min-dwell visual + aria contract.
// The 45 s anti-speedrun floor is invisible by design (no countdown timer
// surfaced, countdowns train rushing), but the disabled "i got it" button
// must communicate why it is disabled to motor-impaired + screen-reader users.
// This spec pins the aria contract per UI-SPEC §Copywriting line 364:
//
//   "at least 45 seconds per lesson — that's the floor."  (verbatim tooltip)
//
// Visual lockout = opacity 0.4 + `aria-disabled="true"` +
// `data-min-dwell-locked="true"`. Silent unlock at t=45 s — no animation,
// no toast, no SR announcement.

import { afterEach, describe, expect, it, vi } from "vitest";

import { LessonSkipButton } from "../../src/learn/lesson/skip-button";

describe("test_min_dwell_aria.spec.ts (LESSON-04 a11y)", () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.replaceChildren();
  });

  it("skip button at t<45s has aria-disabled and min-dwell lock state", () => {
    vi.useFakeTimers();
    const onSkip = vi.fn();
    const btn = LessonSkipButton({ onSkip });
    document.body.append(btn);

    expect(btn.getAttribute("aria-disabled")).toBe("true");
    expect(btn.getAttribute("data-min-dwell-locked")).toBe("true");
    btn.click();
    expect(onSkip).not.toHaveBeenCalled();

    btn.dispose();
  });

  it("tooltip copy is present during the dwell lock", () => {
    vi.useFakeTimers();
    const btn = LessonSkipButton({ onSkip: vi.fn() });
    document.body.append(btn);

    expect(btn.title).toBe("at least 45 seconds per lesson — that's the floor.");

    btn.dispose();
  });

  it("silent unlock at t=45s removes lock state without aria-live text", () => {
    vi.useFakeTimers();
    const sr = document.createElement("div");
    sr.id = "learn-sr-announcement";
    sr.setAttribute("aria-live", "polite");
    sr.textContent = "find the play button.";
    document.body.append(sr);
    const onSkip = vi.fn();
    const btn = LessonSkipButton({ onSkip });
    document.body.append(btn);

    vi.advanceTimersByTime(45_000);

    expect(btn.hasAttribute("aria-disabled")).toBe(false);
    expect(btn.hasAttribute("data-min-dwell-locked")).toBe(false);
    expect(btn.hasAttribute("title")).toBe(false);
    expect(sr.textContent).toBe("find the play button.");
    btn.click();
    expect(onSkip).toHaveBeenCalledTimes(1);

    btn.dispose();
  });
});
