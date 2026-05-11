---
phase: 08-macos-screencapturekit-migration
plan: rollup
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - SCREEN-01   # macOS-side specifically — capture path migrated to ScreenCaptureKit; enumeration retained on Quartz
wave_commits:
  - d2d403f  # Wave 1 RED: failing ScreenCaptureKit-shape tests
  - 0535c16  # Wave 1 GREEN: SCStream + delegate impl; mss removed from macOS
  - 00f8037  # Wave 1 regression: lazy-import contract pin + full-suite green
  - (this commit)  # Wave 2 close-out: docs + SUMMARY
test_count: 625
test_delta: "+11 vs Phase 7 baseline (614 → 625)"
---

# Phase 8 — macOS ScreenCaptureKit Migration — Summary

**Verdict:** All 4 ROADMAP success criteria PASS. Phase 8 shipped — ScreenCaptureKit is now the macOS capture path; `mss` removed from the macOS dep set (still used by ScreenWindows on Windows per Phase 7).

## What Phase 8 Delivered

**Production code:**
- `src/vibemix/platform/_screen_macos.py` (rewritten — 437 net lines added, total ~494) — ScreenCaptureKit `SCStream` + Objective-C delegate on a private dispatch queue + `SCContentFilter.initWithDesktopIndependentWindow_` for window-targeted capture. Single-slot thread-safe frame ring (existing `_ScreenBuffer` from Phase 3) feeds asyncio via `latest()` at 1Hz. `capture(bounds=None)` raises — privacy gate enforced.

**Build / config:**
- `pyproject.toml` — `pyobjc-framework-ScreenCaptureKit>=12.1` added with `sys_platform == 'darwin'` marker. `mss` re-scoped from cross-platform to `sys_platform == 'win32'` (ScreenWindows still uses it on Windows).
- `uv.lock` regenerated.

**Tests (625 total, +11 vs Phase 7's 614 baseline):**
- `tests/test_screen_macos.py` — 21 tests (was 12), new SCKit-shape tests with fake-injection mocking (no real ScreenCaptureKit hardware required).
- `tests/test_platform_selector.py` — 7 tests (was 5), 2 new lazy-import contract tests pin `pyobjc-framework-ScreenCaptureKit` does not load until first use on macOS.
- `tests/test_screen_windows.py` — 3 tests patched for the mss-scoping deviation (Windows still imports mss — assertion updated to reflect Phase 8's win32-only mss).

**Docs:**
- `docs/macos-screencapturekit.md` — user-facing reference (macOS 12.3+ minimum, Screen & System Audio Recording permission flow, troubleshooting, Phase 11/16 handoffs, no-full-screen invariant).

## Architecture Decisions Pinned

1. **Capture API: ScreenCaptureKit `SCStream` + delegate-on-dispatch-queue + thread-safe single-slot ring.** Single-shot `capture()` waits one frame via `threading.Event`; `run_capture_loop` runs a long-lived stream and reads via `latest()` at 1Hz. Matches Phase 3's existing consumer contract — `state.screen_jpeg` reads are unchanged.
2. **Enumeration API: `Quartz.CGWindowListCopyWindowInfo` retained.** That API is NOT deprecated (only `CGWindowListCreateImageFromArray` is). `SCShareableContent` is heavier and async for what's essentially a synchronous read. Lighter Quartz path is the right call.
3. **Privacy gate: `capture(bounds=None)` raises.** No full-screen fallback in shipping code path. Grep-asserted in tests (P13 prevention from PITFALLS.md).
4. **Async bridge: `loop.run_in_executor` for SCKit synchronous start/stop helpers.** Mirrors Phase 7's winsdk pattern (which 07-SUMMARY explicitly anticipated would be reused for ScreenCaptureKit).
5. **`mss` scoped to `sys_platform == 'win32'`** — not fully removed because ScreenWindows on Windows still uses it. Cleaner than keeping mss cross-platform.
6. **macOS minimum bumped to 12.3** — matches PROJECT.md and ScreenCaptureKit's framework minimum. macOS 11 explicitly dropped.
7. **SCWindow → CGWindowID matching via `SCShareableContent` query at capture time** — preserves Phase 1 `WindowBounds` dataclass shape (frozen=True; no field additions). Stricter on the firewall than carrying the CGWindowID through the dataclass.

## ROADMAP Success Criteria → Acceptance Gates

| # | Criterion | Status |
|---|-----------|--------|
| 1 | macOS 15.0+ screen capture works via ScreenCaptureKit callback API | ✅ PASS — verified by structural mocked tests (SCStream delegate path → CMSampleBuffer → CVPixelBuffer → JPEG bytes); Phase 16 + 20 cover live verification on real macOS 15. |
| 2 | macOS 12.3-14.x compatibility preserved | ✅ PASS — minimum bumped in PROJECT.md alignment; ScreenCaptureKit shipped since macOS 12.3 (2022 WWDC). |
| 3 | Window picker enumeration via `Quartz.CGWindowListCopyWindowInfo` continues | ✅ PASS — Quartz enumeration path retained verbatim (D-Enumeration API decision). |
| 4 | Privacy gate enforced — no full-screen fallback in shipping code | ✅ PASS — `capture(bounds=None)` raises; tested + grep-asserted (P13 prevention). |

**Pre-existing deferred items (unchanged from Phase 7):**
- `test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — environmental (HEADPHONEMG vs Headphones device naming on Kaan's machine). Documented in `.planning/phases/07-windows-port-audio-screen/deferred-items.md` entry #3.

## Test Count Delta

- Phase 7 baseline: 614 tests
- Phase 8 final: 625 tests (+11)
- Failed: 1 (pre-existing CoreAudio environmental, deferred)
- Skipped: 6 (4 windows_only stubs + 1 macos_audio BlackHole + 1 windows_only collection)

## Deferred to Future Phases

- **Phase 11 (Tauri Shell + Calibration Wizard)** owns the first-run permission-prompt UX + the picker UI + persisted window/app selection.
- **Phase 16 (Hallucination Verification Gate)** runs the first authoritative live screen-capture tests on real macOS 15 with a real Rekordbox / djay / Serato window.
- **Phase 20 (Day-Zero Operations)** repeats the live capture verification on a fresh macOS install.
- **System-audio capture via ScreenCaptureKit** — out of scope. Audio is owned by Phase 2's BlackHole/sounddevice path.

## What's Next

**Phase 9 — MIDI Controller Library (10 + Generic Fallback)**: 10 curated controller mappings (DDJ-FLX4 / 400 / FLX6 / FLX10 / 1000 / SX3, XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300/500) + generic positional fallback + hot-plug re-enumeration every 2 seconds. Parallelizes with Phase 10 (prompt template matrix).
