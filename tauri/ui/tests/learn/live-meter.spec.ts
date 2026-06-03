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

    meter.dispose();
    expect(host.childElementCount).toBe(0);
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
    meter.dispose();
  });
});
