/* Phase 43 Plan 43-06 / VIS-06 — runtime perf observer test.
 *
 * Pins the 60-frame rolling rAF observer that auto-flips
 * data-blur-perf="on" when p99 frame time exceeds 20ms.
 *
 * 43-CONTEXT §VIS-06 says the observer drives the existing tokens.css
 * `[data-blur-perf="on"]` escape hatch. The attribute is read off
 * <html> (the existing wiring in main.ts uses documentElement —
 * tokens.css cascade rule `html[data-blur-perf="on"]` matches).
 *
 * Test approach: inject a mock rAF that gives synchronous control over
 * frame timing via performance.now() spy. No real raf, no flake.
 */
import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";

import {
  startPerfObserver,
  stopPerfObserver,
  _BLUR_LADDER_THRESHOLDS,
  type PerfHandle,
} from "./perf-observer.js";

describe("perf-observer — VIS-06", () => {
  let nowMs: number;
  let queue: FrameRequestCallback[];

  beforeEach(() => {
    nowMs = 0;
    queue = [];
    document.documentElement.removeAttribute("data-blur-perf");
    document.body.removeAttribute("data-blur-perf");
    vi.spyOn(performance, "now").mockImplementation(() => nowMs);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockRaf = (cb: FrameRequestCallback): number => {
    queue.push(cb);
    return queue.length;
  };
  const mockCaf = (_id: number): void => {
    /* noop — the handle._stopped flag is the real cancel signal */
  };

  test("_BLUR_LADDER_THRESHOLDS pins the contract (60 frames, p99 > 20ms)", () => {
    expect(_BLUR_LADDER_THRESHOLDS.window_frames).toBe(60);
    expect(_BLUR_LADDER_THRESHOLDS.p99_trigger_ms).toBe(20);
  });

  test("steady 12ms frames keep data-blur-perf untouched (healthy GPU)", () => {
    const h = startPerfObserver(mockRaf, mockCaf);
    // Drain 65 mock frames at 12ms each — well under 16.7ms target.
    for (let i = 0; i < 65; i++) {
      nowMs += 12;
      const cb = queue.shift();
      if (cb) cb(nowMs);
    }
    expect(document.documentElement.getAttribute("data-blur-perf")).toBeNull();
    expect(document.body.getAttribute("data-blur-perf")).toBeNull();
    stopPerfObserver(h, mockCaf);
  });

  test("p99 frame 25ms flips data-blur-perf='on' on <html>", () => {
    const h = startPerfObserver(mockRaf, mockCaf);
    for (let i = 0; i < 65; i++) {
      nowMs += 25;
      const cb = queue.shift();
      if (cb) cb(nowMs);
    }
    expect(document.documentElement.getAttribute("data-blur-perf")).toBe("on");
    stopPerfObserver(h, mockCaf);
  });

  test("stopPerfObserver prevents further DOM mutation after stop", () => {
    const h = startPerfObserver(mockRaf, mockCaf);
    stopPerfObserver(h, mockCaf);
    // Drain whatever's queued — the handle is stopped, so the body of
    // tick() must early-return and never set the attribute.
    for (let i = 0; i < 65; i++) {
      nowMs += 25;
      const cb = queue.shift();
      if (cb) cb(nowMs);
    }
    expect(document.documentElement.getAttribute("data-blur-perf")).toBeNull();
  });

  test("handle has _id (number) and _stopped (boolean) shape", () => {
    const h: PerfHandle = startPerfObserver(mockRaf, mockCaf);
    expect(typeof h._id).toBe("number");
    expect(typeof h._stopped).toBe("boolean");
    expect(h._stopped).toBe(false);
    stopPerfObserver(h, mockCaf);
    expect(h._stopped).toBe(true);
  });

  test("flip is sticky for the session (T-43-06-03 mitigation) — one warm GC spike at frame 60 still flips, subsequent fast frames do not flip back", () => {
    const h = startPerfObserver(mockRaf, mockCaf);
    // Fill the window with 25ms frames → flip to "on".
    for (let i = 0; i < 65; i++) {
      nowMs += 25;
      const cb = queue.shift();
      if (cb) cb(nowMs);
    }
    expect(document.documentElement.getAttribute("data-blur-perf")).toBe("on");
    // Now feed a bunch of fast 8ms frames — the ladder must NOT flip
    // back to undefined (sticky for session per §VIS-06 rationale).
    for (let i = 0; i < 65; i++) {
      nowMs += 8;
      const cb = queue.shift();
      if (cb) cb(nowMs);
    }
    expect(document.documentElement.getAttribute("data-blur-perf")).toBe("on");
    stopPerfObserver(h, mockCaf);
  });
});
