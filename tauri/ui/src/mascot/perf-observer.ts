/* Phase 43 Plan 43-06 / VIS-06 — integrated-GPU perf observer.
 *
 * Watches frame time over a 60-frame rolling window via rAF. When the
 * rolling p99 exceeds 20ms (≈< 50fps), sets `data-blur-perf="on"` on
 * the document element (<html>) to flip the tokens.css backdrop-filter
 * escape hatch.
 *
 * 43-CONTEXT §VIS-06: the data-blur-perf attribute toggle is already
 * wired in tokens.css (cascade rule `html[data-blur-perf="on"] { … }`,
 * see tokens.css ~line 230). This module is the runtime sensor that
 * drives it — main.ts already writes the attribute at boot from the
 * persisted settings preference (applyBlurPerfPreference), and this
 * observer adds the live runtime fallback.
 *
 * TARGET ELEMENT NOTE:
 *   The attribute lives on <html> (document.documentElement), NOT
 *   <body>. tokens.css's cascade rule matches `html[data-blur-perf]`,
 *   and the boot-time wiring in main.ts already uses documentElement.
 *   The plan/CONTEXT prose says "body" in one place; we treat <html>
 *   as authoritative since that's what the CSS actually reads.
 *
 * STICKY-FOR-SESSION RATIONALE (T-43-06-03 mitigation):
 *   Once the ladder drops to "on", it does not flip back to high
 *   without an explicit clear. A single warm GC spike shouldn't toggle
 *   the UI back on; if the GPU is integrated, the user stays on the
 *   low ladder for the whole session. 60-frame rolling window absorbs
 *   single-frame transients before triggering.
 *
 * PURITY DISCIPLINE:
 *   - No three.js — observer is DOM-only, runs whether mascot mounted or not.
 *   - DI for raf/caf/element — keeps tests deterministic without timer mocks.
 *   - The handle is the only mutable state owned externally.
 */

export const _BLUR_LADDER_THRESHOLDS = Object.freeze({
  /** Frames in the rolling p99 window. 60 frames at 60fps ≈ 1 second. */
  window_frames: 60,
  /** p99 frame time (ms) that triggers ladder drop to "on" (~< 50fps). */
  p99_trigger_ms: 20,
});

/**
 * Opaque handle returned by startPerfObserver. The `_stopped` flag is
 * the real cancel signal — `tick()` checks it on every frame and
 * returns early when true. Calling stopPerfObserver flips it AND
 * cancels the queued rAF for cleanliness.
 */
export interface PerfHandle {
  _id: number;
  _stopped: boolean;
}

/**
 * Start the perf observer. Returns a handle the caller must hold and
 * pass to stopPerfObserver on unmount.
 *
 * Dependency injection (raf / caf / target) is for testability — the
 * default values match what production calls.
 *
 * Production wiring lives in main.ts (mascot lifecycle hook).
 */
export function startPerfObserver(
  raf: (cb: FrameRequestCallback) => number = (cb) =>
    requestAnimationFrame(cb),
  caf: (id: number) => void = (id) => cancelAnimationFrame(id),
  target: HTMLElement = document.documentElement,
): PerfHandle {
  const handle: PerfHandle = { _id: 0, _stopped: false };
  const frameTimes: number[] = [];
  let last = performance.now();

  const tick = (): void => {
    if (handle._stopped) return;
    const now = performance.now();
    const dt = now - last;
    last = now;
    frameTimes.push(dt);
    if (frameTimes.length > _BLUR_LADDER_THRESHOLDS.window_frames) {
      frameTimes.shift();
    }
    if (
      frameTimes.length === _BLUR_LADDER_THRESHOLDS.window_frames &&
      target.getAttribute("data-blur-perf") !== "on"
    ) {
      const sorted = [...frameTimes].sort((a, b) => a - b);
      // p99 over a 60-sample window: index 59 (Math.floor(0.99 * 60) = 59).
      const p99 = sorted[Math.floor(0.99 * sorted.length)] ?? 0;
      if (p99 > _BLUR_LADDER_THRESHOLDS.p99_trigger_ms) {
        target.setAttribute("data-blur-perf", "on");
      }
    }
    handle._id = raf(tick);
  };
  handle._id = raf(tick);
  // Reference caf so the parameter isn't dropped by linters (start
  // pairs with stop — caf is passed in there).
  void caf;
  return handle;
}

/**
 * Stop the perf observer. Sets the handle's stopped flag (so any
 * already-queued tick early-returns) and cancels the pending rAF.
 *
 * Idempotent — calling twice is safe.
 */
export function stopPerfObserver(
  handle: PerfHandle,
  caf: (id: number) => void = (id) => cancelAnimationFrame(id),
): void {
  if (handle._stopped) return;
  handle._stopped = true;
  caf(handle._id);
}
