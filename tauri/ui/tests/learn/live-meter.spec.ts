// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";

import { LiveGradeMeter } from "../../src/learn/live-meter";

describe("LiveGradeMeter", () => {
  it("moves the needle toward center as phase error approaches zero", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const meter = LiveGradeMeter(host);

    meter.update({
      verdict: "drifting",
      phase_error_beats: 0.25,
      score: 0.5,
      citation: null,
    });

    const driftPct = Number(meter.root.dataset.needlePct);
    expect(meter.root.dataset.state).toBe("active");
    expect(meter.root.dataset.verdict).toBe("drifting");
    expect(driftPct).toBeGreaterThan(50);

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:BEATMATCH_GRADED@12.345]",
    });

    expect(meter.root.dataset.verdict).toBe("locked");
    expect(Number(meter.root.dataset.needlePct)).toBe(50);
    expect(meter.root.dataset.citation).toBe("[ev:BEATMATCH_GRADED@12.345]");
    expect(meter.root.dataset.lockEdge).toBe("true");
    expect(meter.root.dataset.lockCount).toBe("1");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "proof caught",
    );

    meter.dispose();
    expect(host.childElementCount).toBe(0);
  });

  it("celebrates only the edge into locked, then rearms after drift", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const meter = LiveGradeMeter(host);

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: null,
    });
    expect(meter.root.dataset.lockEdge).toBe("true");
    expect(meter.root.dataset.lockCount).toBe("1");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "hold pocket",
    );

    meter.update({
      verdict: "locked",
      phase_error_beats: 0.01,
      score: 0.98,
      citation: null,
    });
    expect(meter.root.dataset.lockEdge).toBe("false");
    expect(meter.root.dataset.lockCount).toBe("1");

    meter.update({
      verdict: "drifting",
      phase_error_beats: -0.2,
      score: 0.6,
      citation: null,
    });
    expect(meter.root.dataset.lockEdge).toBe("false");
    expect(meter.root.dataset.locked).toBe("false");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "deck B early",
    );

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:BEATMATCH_GRADED@15.000]",
    });
    expect(meter.root.dataset.lockEdge).toBe("true");
    expect(meter.root.dataset.lockCount).toBe("2");

    meter.dispose();
  });

  it("renders direction, tier, and best-so-far phase on the meter face", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const meter = LiveGradeMeter(host);

    meter.update({
      verdict: "drifting",
      phase_error_beats: 0.25,
      score: 0.5,
      citation: null,
    });

    expect(meter.root.dataset.direction).toBe("behind");
    expect(meter.root.dataset.tier).toBe("drift");
    expect(meter.root.dataset.bestPhase).toBe("0.2500");
    expect(meter.root.style.getPropertyValue("--best-pct")).toBe("75%");
    expect(meter.root.querySelector(".learn-live-meter__direction")?.textContent).toBe(
      "drag",
    );
    expect(meter.root.querySelector(".learn-live-meter__tier")?.textContent).toBe(
      "drift",
    );

    meter.update({
      verdict: "drifting",
      phase_error_beats: 0.31,
      score: 0.42,
      citation: null,
    });
    expect(meter.root.dataset.bestPhase).toBe("0.2500");
    expect(meter.root.style.getPropertyValue("--best-pct")).toBe("75%");

    meter.update({
      verdict: "drifting",
      phase_error_beats: -0.03,
      score: 0.82,
      citation: null,
    });

    expect(meter.root.dataset.direction).toBe("ahead");
    expect(meter.root.dataset.tier).toBe("tight");
    expect(meter.root.dataset.bestPhase).toBe("-0.0300");
    expect(meter.root.style.getPropertyValue("--best-pct")).toBe("47%");
    expect(meter.root.querySelector(".learn-live-meter__direction")?.textContent).toBe(
      "rush",
    );

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: null,
    });

    expect(meter.root.dataset.direction).toBe("center");
    expect(meter.root.dataset.tier).toBe("locked");
    expect(meter.root.dataset.bestPhase).toBe("0.0000");
    expect(meter.root.querySelector(".learn-live-meter__direction")?.textContent).toBe(
      "hold",
    );

    meter.dispose();
  });

  it("renders save-mode pressure, expiry, and landed streak receipts", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const meter = LiveGradeMeter(host);

    meter.update({
      verdict: "drifting",
      phase_error_beats: 0.18,
      score: 0.62,
      citation: null,
      save_attempt_active: true,
      save_floor_seconds_total: 14,
      save_floor_seconds_remaining: 8.5,
      save_difficulty_level: 2,
      save_streak: 1,
    });

    const save = meter.root.querySelector<HTMLElement>(".learn-live-meter__save");
    expect(save?.hidden).toBe(false);
    // Streak/difficulty surface as plain words, never xN / L-number chips
    // (the anti-gamification law); difficulty stays machine-readable in data-*.
    expect(save?.textContent).toContain("save window");
    expect(save?.textContent).toContain("8.5s");
    expect(save?.textContent).toContain("one clean save");
    expect(save?.textContent).not.toMatch(/x\d|L\d/);
    expect(meter.root.dataset.saveActive).toBe("true");
    expect(meter.root.dataset.saveLevel).toBe("2");
    expect(meter.root.dataset.saveRemaining).toBe("8.5");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "save window",
    );
    expect(meter.root.getAttribute("aria-label")).toContain("save window");
    expect(meter.root.getAttribute("aria-label")).toContain("one clean save");

    meter.update({
      verdict: "trainwreck",
      phase_error_beats: -0.4,
      score: 0.1,
      citation: null,
      save_floor_expired: true,
      save_floor_seconds_total: 14,
      save_floor_seconds_remaining: 0,
      save_difficulty_level: 2,
      save_streak: 0,
    });

    expect(meter.root.dataset.saveExpired).toBe("true");
    expect(meter.root.dataset.saveRemaining).toBe("0.0");
    expect(save?.textContent).toContain("00.0s");
    expect(save?.textContent).toContain("no saves yet");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "floor dropped",
    );
    expect(meter.root.getAttribute("aria-label")).toContain("floor dropped");

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:LEARN_BEATMATCH_SAVE_LANDED@21.000]",
      save_landed: true,
      save_difficulty_level: 3,
      save_streak: 2,
    });

    expect(meter.root.dataset.saveLanded).toBe("true");
    expect(meter.root.dataset.saveLevel).toBe("3");
    expect(meter.root.dataset.saveStreak).toBe("2");
    expect(save?.textContent).toContain("landed");
    expect(save?.textContent).toContain("2 clean saves");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "save landed",
    );
    expect(meter.root.dataset.savePulse).toBe("a");
    expect(meter.root.dataset.saveThunk).toBe("silent");

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:BEATMATCH_GRADED@22.000]",
    });
    expect(meter.root.dataset.lockEdge).toBe("false");
    expect(meter.root.dataset.savePulse).toBe("a");

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:LEARN_BEATMATCH_SAVE_LANDED@23.000]",
      save_landed: true,
      save_difficulty_level: 4,
      save_streak: 3,
    });

    expect(meter.root.dataset.savePulse).toBe("b");
    expect(meter.root.dataset.saveStreak).toBe("3");

    meter.dispose();
  });

  it("mutes the save thunk while tutor speech is active", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const meter = LiveGradeMeter(host);

    window.dispatchEvent(
      new CustomEvent("ipc.learn.tutor_speak", {
        detail: {
          text: "pull them into one pulse, then breathe.",
        },
      }),
    );
    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:LEARN_BEATMATCH_SAVE_LANDED@24.000]",
      save_landed: true,
      save_difficulty_level: 2,
      save_streak: 1,
    });

    expect(meter.root.dataset.savePulse).toBe("a");
    expect(meter.root.dataset.saveThunk).toBe("muted");

    meter.dispose();
  });

  it("resets to idle without carrying stale citation state", () => {
    const host = document.createElement("div");
    document.body.append(host);
    const meter = LiveGradeMeter(host);

    meter.update({
      verdict: "locked",
      phase_error_beats: 0,
      score: 1,
      citation: "[ev:BEATMATCH_GRADED@12.345]",
    });
    meter.reset();

    expect(meter.root.dataset.state).toBe("idle");
    expect(meter.root.dataset.verdict).toBeUndefined();
    expect(meter.root.dataset.citation).toBeUndefined();
    expect(meter.root.dataset.needlePct).toBe("50.0");
    expect(meter.root.dataset.lockEdge).toBe("false");
    expect(meter.root.dataset.lockCount).toBe("0");
    expect(meter.root.dataset.locked).toBeUndefined();
    expect(meter.root.dataset.saveActive).toBeUndefined();
    expect(meter.root.dataset.saveRemaining).toBeUndefined();
    expect(meter.root.dataset.savePulse).toBeUndefined();
    expect(meter.root.dataset.saveThunk).toBeUndefined();
    expect(meter.root.dataset.bestPhase).toBeUndefined();
    expect(meter.root.style.getPropertyValue("--best-pct")).toBe("");
    meter.dispose();
  });
});
