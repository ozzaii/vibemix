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
    expect(save?.textContent).toContain("L2");
    expect(save?.textContent).toContain("8.5s");
    expect(save?.textContent).toContain("x1");
    expect(meter.root.dataset.saveActive).toBe("true");
    expect(meter.root.dataset.saveLevel).toBe("2");
    expect(meter.root.dataset.saveRemaining).toBe("8.5");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "save window",
    );
    expect(meter.root.getAttribute("aria-label")).toContain("save level 2");

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
    expect(save?.textContent).toContain("x0");
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
    expect(save?.textContent).toContain("L3");
    expect(save?.textContent).toContain("landed");
    expect(save?.textContent).toContain("x2");
    expect(meter.root.querySelector(".learn-live-meter__receipt")?.textContent).toBe(
      "save landed",
    );

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
    meter.dispose();
  });
});
