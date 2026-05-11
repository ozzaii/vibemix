---
phase: 08-macos-screencapturekit-migration
plan: 01
subsystem: platform-screen
tags:
  - screen-macos
  - screencapturekit
  - pyobjc
  - sckit
  - macos-15
  - deprecation-chase
  - lazy-import
  - tdd

# Dependency graph
requires:
  - phase: 01-platform-protocol-firewall
    provides: ScreenBackend Protocol + WindowBounds + CapturedFrame dataclasses
  - phase: 03-sensing-state-port
    provides: Phase 3 ScreenMacOS impl (mss + Quartz) — public surface preserved verbatim
  - phase: 07-windows-port-audio-screen
    provides: lazy-import discipline pattern + asyncio.run-in-executor bridge for native async APIs (template for Wave 1's SCStream bridge)
provides:
  - ScreenCaptureKit SCStream + SCContentFilter + delegate-on-dispatch-queue capture path on macOS 12.3+
  - Privacy gate enforcement — capture(bounds=None) raises, no full-screen fallback in shipping code
  - Lazy-import contract for ScreenCaptureKit / CoreMedia / CoreVideo (no eager pyobjc-framework-ScreenCaptureKit load on import)
  - Test mocking infrastructure for ScreenCaptureKit (fake SCStream + SCContentFilter + SCShareableContent + CMSampleBuffer producer)
  - mss removed from macOS deps (still present on Windows for ScreenWindows)
affects:
  - 08-02 (Wave 2 docs deliverable + macOS-15-deprecation chase tracking)
  - 11-calibration-wizard (window picker UX builds on capture(bounds) contract)
  - 16-hallucination-verification (live SCKit gate — first real capture against djay/Rekordbox)
  - 20-fresh-machine-rehearsal (CI matrix gate for SCKit on macOS 14/15)

# Tech tracking
tech-stack:
  added:
    - pyobjc-framework-ScreenCaptureKit>=12.1 (darwin marker)
    - pyobjc-framework-CoreMedia>=12.1 (transitive, pulled by pyobjc-framework-ScreenCaptureKit)
  patterns:
    - "Lazy-import discipline for native macOS frameworks — ScreenCaptureKit/CoreMedia/CoreVideo imported inside method bodies only (mirror of Phase 7 winsdk pattern in _track_windows.py)"
    - "Dispatch-queue delegate → threading.Event → asyncio.run_in_executor bridge for SCStream sample-buffer delivery (matches Phase 7's winsdk asyncio.run inside executor)"
    - "Mocked-only CI for native capture APIs — fake module injection via monkeypatch.setitem(sys.modules, 'ScreenCaptureKit', fake) (Phase 16 + Phase 20 are the live gates)"
    - "Privacy gate as a hard constraint at the construction site — initWithDesktopIndependentWindow_ only, never the display-wide SCContentFilter constructor (grep gate in tests pins this)"

key-files:
  created:
    - .planning/phases/08-macos-screencapturekit-migration/08-01-SUMMARY.md
  modified:
    - src/vibemix/platform/_screen_macos.py (rewritten — 229 lines → 494 lines)
    - tests/test_screen_macos.py (12 tests → 21 tests; SCKit-shape mocking added)
    - tests/test_platform_selector.py (5 tests → 7 tests; macOS lazy-import contract added)
    - tests/test_screen_windows.py (3 tests updated for Phase 8 pyproject mss-scoping deviation)
    - pyproject.toml (mss → win32-only; pyobjc-framework-ScreenCaptureKit added)
    - uv.lock (regenerated for new pyobjc-framework dependencies)

key-decisions:
  - "Lazy-import ScreenCaptureKit / CoreMedia / CoreVideo — module-level _HAS_SCKIT probe is replaced by a per-call _sckit_available() helper that imports inside the function. This mirrors the Phase 7 _track_windows.is_available() pattern exactly and keeps importing _screen_macos cheap on machines without pyobjc-framework-ScreenCaptureKit installed."
  - "Single-shot SCStream per capture() call — instead of holding a long-lived stream, capture() builds + starts + waits-for-frame + stops + tears-down the SCStream every call. run_capture_loop offloads successive single-shot captures via loop.run_in_executor at 1Hz cadence. Simpler than long-lived stream + state-aware start/stop transitions; matches the Phase 7 single-poll-per-tick pattern in _track_windows."
  - "Privacy gate enforced at TWO points — capture(bounds=None) raises BEFORE any SCKit import, and the SCContentFilter is built only via initWithDesktopIndependentWindow_ (the display-wide constructor is never invoked in source). A grep gate test asserts the display-wide constructor token never appears in the module body."
  - "Mocking strategy: inject fake ScreenCaptureKit / CoreMedia / CoreVideo modules into sys.modules via monkeypatch — mirror of Phase 7's winsdk-fake injection in test_track_windows. This lets the same lazy import sites resolve to the fakes during CI without requiring real macOS framework wheels in the CI environment."
  - "mss scope reduced to win32-only in pyproject.toml — macOS no longer installs mss. Phase 7 _screen_windows.py still uses it (eager top-level import), so the Wave 2 cleanup is to lazy-import mss inside Windows method bodies. Out of scope for Plan 08-01 — captured as candidate work in the GREEN deviation note."
  - "Tests in tests/test_screen_windows.py updated (Rule 1 deviation) — three Phase 7 tests assumed mss would always be installed on macOS dev boxes. Patched to inject a fake mss module + restore _HAS_MSS=True via mocker.patch. The architectural fix (lazy-import mss in _screen_windows.py) is deferred."

patterns-established:
  - "Pattern: Mocked native-framework injection — fake modules built with types.ModuleType + MagicMock + monkeypatch.setitem(sys.modules, ...) handle pyobjc framework mocking the same way Phase 7 handled winsdk."
  - "Pattern: dispatch-queue delegate as plain Python class — pyobjc duck-types delegate registration when method names match Objective-C selectors. _SCKitDelegate is a plain class implementing stream_didOutputSampleBuffer_ofType_, no NSObject base. Phase 16 will validate the duck-type works against the real SCStream API."
  - "Pattern: synchronous start + threading.Event + synchronous stop — capture() blocks the calling thread on delegate.frame_ready.wait(timeout=3.0); the asyncio loop offloads the whole synchronous path via loop.run_in_executor."

requirements-completed:
  - SCREEN-01

# Metrics
duration: 16min
completed: 2026-05-11
---

# Phase 8 Plan 1: ScreenCaptureKit Migration (Wave 1) Summary

**ScreenCaptureKit SCStream + SCContentFilter + delegate-on-dispatch-queue capture path on macOS, replacing the deprecated mss/CGWindowListCreateImageFromArray pipeline; privacy gate enforced at the SCContentFilter construction site; lazy-import contract pinned for forward compat to macOS 15+.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-05-11T20:07:00Z
- **Completed:** 2026-05-11T20:22:41Z
- **Tasks:** 3 (RED + GREEN + regression — TDD plan)
- **Files modified:** 6 (src: 1, tests: 3, build: 2)

## Accomplishments

- **`src/vibemix/platform/_screen_macos.py` rewritten** around the ScreenCaptureKit SCStream callback API. The Phase 1 `ScreenBackend` Protocol shape (`is_available`, `find_window_bounds`, `capture`) and the Phase 3 extension surface (`latest`, `run_capture_loop`) are byte-identical from the caller's perspective. `mss` is gone from the macOS path; Quartz `CGWindowListCopyWindowInfo` is retained verbatim for window enumeration (NOT deprecated per D-Enumeration API).
- **Privacy gate enforced**: `capture(bounds=None)` raises before any SCKit import; `SCContentFilter` is built only via `initWithDesktopIndependentWindow_` (the display-wide constructor is never invoked anywhere in source). Three grep-gate tests pin this as a forward-locked invariant.
- **Lazy-import contract**: `ScreenCaptureKit`, `CoreMedia`, `CoreVideo` are imported only inside method bodies — importing `vibemix.platform._screen_macos` on a box without `pyobjc-framework-ScreenCaptureKit` does not raise. Mirror of the Phase 7 `_track_windows` lazy contract.
- **9 new SCKit-shape tests** added to `tests/test_screen_macos.py` (12 tests → 21), all using mocked SCStream + SCContentFilter + SCShareableContent + a synthetic CMSampleBuffer producer. No live ScreenCaptureKit hardware required in CI; Phase 16 + Phase 20 are the authoritative live gates.
- **2 new lazy-import contract tests** added to `tests/test_platform_selector.py` (5 → 7) — structural mirrors of the Phase 7 win32-side rules for the new macOS path.
- **Cross-platform regression contained**: 3 Phase 7 `test_screen_windows.py` tests broke when mss was scoped to `win32` only (mss no longer installed on macOS dev boxes); patched in-place with `mocker.patch` to restore `_HAS_MSS=True` and inject a fake `mss` module attribute. Same shape as Phase 7's `win32gui` mocking.
- **`pyproject.toml`**: `pyobjc-framework-ScreenCaptureKit>=12.1` added under the darwin marker; `mss>=10.2.0` re-scoped to `sys_platform == 'win32'`.

## Task Commits

1. **Task 1: RED — failing ScreenCaptureKit-shape tests** — `d2d403f` (test)
2. **Task 2: GREEN — ScreenCaptureKit SCStream + delegate; drop mss on macOS** — `0535c16` (feat)
3. **Task 3: pin macOS lazy-import contract + full-suite regression** — `00f8037` (test)

## Files Created/Modified

- `src/vibemix/platform/_screen_macos.py` — rewritten. New: `_sckit_available()` lazy probe, `_SCKitDelegate` class implementing `stream_didOutputSampleBuffer_ofType_`, `_resolve_sc_window_for_bounds` helper bridging Quartz bounds → SCWindow via `SCShareableContent`. Rewritten: `capture()` (single-shot SCStream), `run_capture_loop()` (1Hz async coordinator over `loop.run_in_executor`). Preserved verbatim: `_ScreenBuffer` (thread-safe latest-frame holder), `_find_djay_window_bounds` (Quartz path).
- `tests/test_screen_macos.py` — expanded from 12 to 21 tests. New mocking infrastructure: `_FakeCMSampleBuffer`, `_install_fake_sckit` (injects fake ScreenCaptureKit / CoreMedia / CoreVideo / dispatch modules), `_make_synthetic_sample_buffer` helper. New tests: SCKit pipeline + privacy gate + delegate frame-push + content-filter-window-only + run-capture-loop async bridge + 3 grep-gate invariants + 2 lazy-import contract checks.
- `tests/test_platform_selector.py` — expanded from 5 to 7 tests. New: `test_macos_screen_path_uses_screencapturekit_not_mss`, `test_macos_screen_path_does_not_eager_import_screencapturekit`.
- `tests/test_screen_windows.py` — three tests patched to mock `mss` (Rule 1 deviation; full deferred-architecture note below).
- `pyproject.toml` — `mss>=10.2.0 ; sys_platform == 'win32'` (was unscoped); added `pyobjc-framework-ScreenCaptureKit>=12.1 ; sys_platform == 'darwin'`.
- `uv.lock` — regenerated; new entries for `pyobjc-framework-coremedia` and `pyobjc-framework-screencapturekit`.

## Decisions Made

All decisions match the plan's Decisions §Locked + §Discretion. Notable in-execution choices:

- **Single-shot SCStream per `capture()` call** rather than a long-lived stream + start/stop transitions in `run_capture_loop`. The plan offered both as options; single-shot is simpler and matches the Phase 7 single-poll-per-tick pattern exactly. Phase 16's live test will tell us if SCStream startup latency makes long-lived streams necessary; for now, single-shot keeps the implementation small and the test surface tight.
- **`_SCKitDelegate` as a plain Python class**, not an `NSObject` subclass. Pyobjc duck-types delegate registration when method-name selectors match. If real-world SCKit refuses the duck-type during Phase 16 live testing, the Phase 16 deliverable will wrap the delegate in an NSObject subclass — the public method shape stays identical.
- **`numpy` for the BGRA stride-aware view** in the delegate. numpy is already a project-wide dependency (audio buffers); using it here for the row-stride handling is cheaper than rolling our own pure-Python stride loop and faster on a 1920×1080 frame than naïve indexing.
- **`bytes(base)` cast for the CVPixelBuffer base address**. pyobjc returns a buffer-protocol-compatible accessor for `CVPixelBufferGetBaseAddress`. The cast is defensive — Phase 16 will reveal whether `np.frombuffer(base, dtype=np.uint8)` works directly without the cast (faster path).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mss-scoping cross-platform regression in test_screen_windows.py**
- **Found during:** Task 2 (GREEN — full pytest suite revealed 3 new failures after `mss` was scoped to `win32` in pyproject.toml).
- **Issue:** Phase 7's `tests/test_screen_windows.py` had three tests (`test_capture_no_bounds_produces_jpeg`, `test_capture_with_bounds_invokes_crop`, `test_is_available_true_when_all_mocked`) that exercised the Windows capture pipeline on the macOS dev box, relying on the assumption that `mss` would always be installed system-wide (the Phase 7 `_screen_windows.py` does an eager `import mss` at module top, with the result cached as `_HAS_MSS`). Once Phase 8 dropped `mss` from the macOS install (pyproject scoping), `_HAS_MSS` flipped to `False` on macOS — and the three tests started failing with `ScreenWindows dependencies unavailable`.
- **Fix:** Updated the three tests to inject a fake `mss` module via `mocker.patch("vibemix.platform._screen_windows.mss", fake_mss_module)` AND restore `_HAS_MSS=True` via `mocker.patch("vibemix.platform._screen_windows._HAS_MSS", True)`. Same shape as the existing `win32gui` mocking pattern in those tests. Module docstring updated to document the new contract.
- **Files modified:** `tests/test_screen_windows.py`.
- **Verification:** `uv run pytest tests/test_screen_windows.py` → 18 passed (was 18 pre-Phase-8; restored to baseline).
- **Committed in:** `0535c16` (folded into the GREEN commit since it's caused by the same architectural change).
- **Out-of-scope follow-up:** The deeper architectural fix would be to lazy-import `mss` inside `_screen_windows.py` method bodies (mirror of `_track_windows`'s pattern), which would also pin a Phase 7-style "mss not in sys.modules on macOS" lazy-import contract test. Filed as candidate work for Plan 08-02 Wave 2 cleanup or a future Phase-9 housekeeping pass.

**2. [Rule 2 - Missing Critical] Removed forbidden API tokens from module docstring**
- **Found during:** Task 2 (GREEN — first pytest run after rewrite triggered two grep-gate failures).
- **Issue:** The new `_screen_macos.py` module docstring referenced `initWithDisplay_excludingWindows_` and `CGWindowListCreateImageFromArray` as part of describing what the new code does NOT use. The grep-gate tests strip lines starting with `#` but treat docstring lines as code, so the literal forbidden tokens in the docstring made the gates fail.
- **Fix:** Reworded the docstring to use generic phrases ("legacy Quartz capture API", "display-wide SCContentFilter constructor") instead of the literal forbidden token names. The constraint that those tokens never appear in source body — including docstrings — is the correct invariant to enforce.
- **Files modified:** `src/vibemix/platform/_screen_macos.py`.
- **Verification:** `grep -c 'CGWindowListCreateImageFromArray' src/vibemix/platform/_screen_macos.py` → 0; `grep -c 'initWithDisplay_excludingWindows_' src/vibemix/platform/_screen_macos.py` → 0. Both grep-gate tests now pass.
- **Committed in:** `0535c16` (part of the GREEN commit).

---

**Total deviations:** 2 auto-fixed (1 cross-platform regression / 1 self-induced grep-gate failure)
**Impact on plan:** Both deviations were necessary for correctness and were caused by the Phase 8 architectural change itself (the mss-scoping). No scope creep — the Windows-side `_screen_windows.py` lazy-import discipline is captured as deferred work, not silently rolled in.

## Issues Encountered

- **Worktree base mismatch on agent spawn:** the worktree was created from the Phase 6 commit (`6e6dd9f`) but the Phase 8 plan file was committed to `main` after Phase 7 shipped. Resolved by `git merge --ff-only main` to pick up the Phase 7 codebase + Phase 8 plan/context. Documented for the orchestrator: future Phase 8 work runs should spawn from a Phase-7-aware base commit so this fast-forward isn't necessary.
- **`cohost_v4.py` missing in worktree** — `tests/agent/test_persona.py` and `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` both fail with `FileNotFoundError: cohost_v4.py`. The POC reference files (`cohost_v3.py`, `cohost_v4.py`, `run_v3.sh`, `run_v4.sh`, `fillers/`) are untracked in the main repo (per the user-memory note "v3/v4 POC files are reference too — leave untouched") and so don't propagate to git worktrees. Pre-existing environmental issue, not introduced by Phase 8. Filed in `deferred-items.md` candidates list.
- **Phase 7 deferred items still present:** `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` (CoreAudio device naming `HEADPHONEMG` vs `Headphones`) and `tests/test_midi_common.py` ruff I001 import-sort warning. Both are documented Phase 7 deferred items #3 and #4. Not addressed in Phase 8 — out of scope.

## Self-Check: PASSED

Verified the SUMMARY's claims:

```
git log --oneline | grep -E '08-01' | head -3
00f8037 test(08-01): pin macOS lazy-import contract + full-suite regression
0535c16 feat(08-01): GREEN — ScreenCaptureKit SCStream + delegate; drop mss on macOS
d2d403f test(08-01): RED — failing ScreenCaptureKit-shape tests for _screen_macos
```

```
ls -la src/vibemix/platform/_screen_macos.py    # 494 lines, modified, in worktree
ls -la tests/test_screen_macos.py               # 21 tests, modified
ls -la tests/test_platform_selector.py          # 7 tests, modified
ls -la pyproject.toml                            # mss win32-only, SCKit added
```

```
uv run pytest tests/test_screen_macos.py tests/test_platform_selector.py
→ 28 passed
```

```
uv run pytest -q  # full suite
→ 623 passed, 6 skipped, 3 pre-existing failures (cohost_v4.py / CoreAudio device-naming)
```

All grep gates green:
- `CGWindowListCreateImageFromArray` count in `_screen_macos.py` → 0
- `import mss` / `from mss` count in `_screen_macos.py` → 0
- `CGWindowListCopyWindowInfo` count in `_screen_macos.py` → 5 (enumeration retained)
- `ScreenCaptureKit | SCStream | SCContentFilter` count in `_screen_macos.py` → 37

Protocol satisfaction:
- `from vibemix.platform import ScreenMacOS, ScreenBackend; isinstance(ScreenMacOS(), ScreenBackend)` → True

POC files untouched:
- `git diff HEAD~3..HEAD -- cohost*.py run*.sh fillers/ mascot.html` → empty diff (untracked POC files unmodified).

## Threat Flags

None — Phase 8 narrows the screen-capture trust boundary (privacy gate now enforced at the SCContentFilter construction site, no full-screen fallback in shipping code path) and does not introduce new network endpoints, auth paths, file access patterns, or schema changes. The ScreenCaptureKit permission prompt (Screen & System Audio Recording) is a new OS-level user dialog that fires on first SCShareableContent call — Phase 11 calibration wizard owns that UX, not Phase 8 code.

## Next Phase Readiness

- **Plan 08-02 (Wave 2 — docs deliverable + 08-SUMMARY rollup) ready to execute.** Wave 2's input is this SUMMARY plus the new `_screen_macos.py` source as the canonical reference for the ScreenCaptureKit migration write-up.
- **Phase 16 (hallucination verification)** is the first live gate — needs to run `vibemix.platform._screen_macos.ScreenMacOS().capture(bounds=...)` against a real djay/Rekordbox window on macOS 14 + 15 to confirm the delegate's CMSampleBuffer → JPEG path works end-to-end. The test mocking covers structural correctness; live correctness needs real frames.
- **Phase 20 (fresh-machine rehearsal)** is the second live gate — needs the Screen Recording permission prompt path validated on a freshly-installed macOS box where the user has not previously granted permission to any app.
- **Outstanding cleanup candidate**: `_screen_windows.py` lazy-import refactor — make it import `mss` inside method bodies (mirror of `_track_windows`'s lazy pattern) so a Phase-7-shape "mss not in sys.modules on macOS" gate test can be added. Filed as candidate work for Plan 08-02 cleanup OR a Phase 9 housekeeping pass.

---
*Phase: 08-macos-screencapturekit-migration*
*Completed: 2026-05-11*
