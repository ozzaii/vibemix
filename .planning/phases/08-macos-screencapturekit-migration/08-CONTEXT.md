# Phase 8: macOS ScreenCaptureKit Migration - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — sensible defaults derived from ROADMAP + current impl)

<domain>
## Phase Boundary

Replace the `mss` screen-capture backend in `_screen_macos.py` with `pyobjc-framework-ScreenCaptureKit` for forward-compat to macOS 15+. Keep `Quartz.CGWindowListCopyWindowInfo` for window enumeration — that API is NOT deprecated. The migration target is the **capture path** (mss → ScreenCaptureKit), not the enumeration path.

**Current state:** `_screen_macos.py` uses `mss` for screen capture and `Quartz.CGWindowListCopyWindowInfo` for window enumeration. `mss` internally calls `CGWindowListCreateImageFromArray` which is obsoleted in macOS 15.0.

**Target state:** ScreenCaptureKit's `SCStream` callback API + `SCContentFilter` (windows / displays / apps) for window-targeted capture; CGWindowListCopyWindowInfo retained for window enumeration UX.

**Scope cut:** macOS 11 support — drop. ScreenCaptureKit requires macOS 12.3+. PROJECT.md constraint already says macOS 12.3+ is the minimum.
</domain>

<decisions>
## Implementation Decisions

### Locked

- **Capture API:** ScreenCaptureKit `SCStream` with `SCContentFilter` for window-targeted capture. Async callback delivers `CMSampleBuffer` → CVPixelBuffer → JPEG bytes via Pillow.
- **Enumeration API:** Keep `Quartz.CGWindowListCopyWindowInfo` — not deprecated, simpler than ScreenCaptureKit's `SCShareableContent` for the read-only window-list use case.
- **Minimum macOS:** 12.3+ (matches PROJECT.md constraint; ScreenCaptureKit's minimum).
- **Async bridge:** ScreenCaptureKit delivers via Objective-C delegate callbacks on a dispatch queue. Use `loop.run_in_executor` (matches Phase 7 winsdk pattern + Phase 5/6 macOS subprocess patterns) plus a `threading.Event` or `asyncio.Queue` to deliver frames into the asyncio loop. Alternative: convert the delegate callback's frame to JPEG synchronously inside the delegate, push to a thread-safe ring, asyncio reads from ring at 1Hz. Pick the simplest of these in plan-phase.
- **Privacy gate** (Success Criterion 4): Calibration wizard (Phase 11) mandates user picks a specific DJ-app window. No full-screen fallback in shipping code path — `ScreenCaptureKit.SCStreamConfiguration` is configured for the picked window's SCWindow only.
- **Permission prompt:** ScreenCaptureKit triggers a system permission prompt (Screen & System Audio Recording) the first time `SCShareableContent.currentWithCompletion:` is called. Phase 11 wizard owns the UX; Phase 8 ensures the API call shape triggers the prompt early so the user is prepared.

### Claude's Discretion

- Internal frame-delivery mechanism (asyncio.Queue vs threading.Event + ring) — pick during planning based on simplicity.
- Whether to retain the `mss` import as a fallback or fully remove (the mss import is currently lazy-loaded — removing it cleans up the dependency).
- Whether to bump `pyobjc-framework-Quartz` minimum or add `pyobjc-framework-ScreenCaptureKit` as a separate dep (both ship under pyobjc-framework-* — they may already share the same wheel).
- Test mocking strategy: structural tests on macOS without requiring real ScreenCaptureKit hardware (mock the SCStream delegate callback path).
</decisions>

<code_context>
## Existing Code Insights

- `src/vibemix/platform/_screen_macos.py` (229 lines) — current impl using mss + Quartz.
- The `capture(bounds, ...)` method (Phase 1 Protocol) is the synchronous path; `run_capture_loop` is the async 1Hz loop.
- Both paths go through `_grab_frame` (or equivalent) — refactor target.
- ScreenCaptureKit's callback model fits naturally with the v4 `screen_capture_loop` async pattern — the loop becomes a consumer of a queue/ring fed by the delegate.
- `tests/test_screen_macos.py` exists from Phase 3 — preserve its assertions on the public API (latest() / capture() / run_capture_loop()) so the Protocol contract is unchanged.
- Phase 1's `ScreenBackend` Protocol shape — the migration must preserve this exactly.
</code_context>

<specifics>
## Specific Ideas

1. **Bring up SCStream + SCStreamDelegate via pyobjc** — write a Python delegate class implementing `stream:didOutputSampleBuffer:ofType:` that converts CMSampleBuffer → PNG/JPEG bytes.
2. **CVPixelBuffer → Pillow image** — bridge through `CVPixelBufferGetBaseAddress` + width/height + bytes-per-row, wrap in numpy then PIL.Image. Test with synthetic pixel buffers.
3. **SCContentFilter for picked window** — when window picker returns a CGWindowID, build an SCContentFilter with `initWithDesktopIndependentWindow:` for that window.
4. **Permission prompt early-fire** — wizard surfaces this on first launch via a calibration step in Phase 11.
5. **Single capture path, no full-screen fallback in shipping code** — even unit tests must not exercise a hypothetical full-screen path (P13).
</specifics>

<deferred>
## Deferred Ideas

- Live integration test on macOS Sequoia (real screen capture with a Rekordbox window) — Phase 16 hallucination verification + Phase 20 fresh-machine rehearsal cover this. Phase 8 verifies via structural / mock tests.
- ScreenCaptureKit audio capture (system audio) — Phase 2 already covers audio via BlackHole/sounddevice; SCKit audio is out of scope.
- macOS 11 / 10.x fallback — explicitly dropped per macOS 12.3+ constraint.
</deferred>
