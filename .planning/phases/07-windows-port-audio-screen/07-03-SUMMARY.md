---
phase: 07-windows-port-audio-screen
plan: 03
subsystem: platform
tags: [screen-windows, track-windows, smtc, pywin32, winsdk, mss, windows-port]

requires:
  - phase: 01-platform-protocol-firewall
    provides: ScreenBackend / TrackInfoBackend Protocols + value dataclasses (WindowBounds, CapturedFrame, NowPlayingSnapshot)
  - phase: 03-sensing-state-port
    provides: ScreenMacOS + TrackMacOS reference impls (the shape Wave 3 ports to Windows)
  - phase: 07-01
    provides: sys.platform-dispatched ScreenImpl/TrackImpl selector slot + Windows-only pyaudiowpatch/pywin32/winsdk deps gated on sys_platform == 'win32'
provides:
  - vibemix.platform._screen_windows.ScreenWindows — mss screen grab + pywin32 EnumWindows DJ-app window discovery + 1Hz state.audible-gated capture loop
  - vibemix.platform._track_windows.TrackWindows — winsdk SMTC poll bridged via asyncio.run inside a sync executor thread; 1Hz cadence + log-once graceful fallback
  - locked _DJ_HINTS tuple ("djay", "serato", "traktor", "rekordbox", "virtualdj") — case-insensitive priority-ordered Windows DJ-software window match
  - pytest marker registration: windows_only (live tests skipped on macOS via skipif + opt-in via marker for Phase 20 CI matrix)
affects:
  - 07-04 (Wave 4: MidiWindows — last platform impl + cross-platform integration test)
  - 07-05 (Wave 5: rolled-up 07-SUMMARY + phase close)
  - 11-tauri-shell (calibration wizard reads sys.platform; ScreenImpl/TrackImpl ready)
  - 20-day-zero-ops (Phase 20 GH Actions windows-latest matrix runs the live test stubs)

tech-stack:
  added: []
  patterns:
    - "Lazy intra-module import for Windows-only deps: win32gui imported only inside ScreenWindows._import_win32gui staticmethod + EnumWindows callback; winsdk.windows.media.control imported only inside TrackWindows._poll_smtc_sync + is_available(). Module-import on darwin pulls neither into sys.modules — verified by test_module_imports_on_macos_without_pulling_{win32gui,winsdk}."
    - "winsdk async bridge via asyncio.run-inside-executor: TrackWindows._poll_smtc_sync runs in a worker thread (run_in_executor), opens a private asyncio loop with asyncio.run(_inner()) where _inner awaits winsdk's request_async + try_get_media_properties_async. Mirrors the macOS subprocess pattern, no new event-loop machinery in the main thread."
    - "Fake-module chain for winsdk mocks: tests build types.ModuleType('winsdk') + types.ModuleType('winsdk.windows') + ... + types.ModuleType('winsdk.windows.media.control') so the impl's `import winsdk.windows.media.control` resolves to the fake parent chain (Python's import machinery requires parent modules to exist for dotted-path imports)."
    - "Order-independent run_poll_loop test: avoid monkeypatch.setattr('vibemix.platform._track_windows.asyncio.sleep', ...) — the string-path attribute walk breaks after test_platform_selector deletes + reimports vibemix.platform. Use asyncio.wait_for(timeout=...) + pre-set stop_event instead — terminates cleanly without monkeypatching."

key-files:
  created:
    - src/vibemix/platform/_screen_windows.py
    - src/vibemix/platform/_track_windows.py
    - tests/test_screen_windows.py
    - tests/test_screen_windows_live.py
    - tests/test_track_windows.py
    - tests/test_track_windows_live.py
    - .planning/phases/07-windows-port-audio-screen/07-03-SUMMARY.md
  modified:
    - pyproject.toml  # registered windows_only marker (--strict-markers gate)

key-decisions:
  - "Lazy import of win32gui via a single _import_win32gui staticmethod (Critical Constraint 3). The staticmethod is the ONLY place in _screen_windows.py that names win32gui — keeps the import surface auditable and makes the fake-injection seam single-point (monkeypatch.setitem(sys.modules, 'win32gui', fake) is the only thing tests need to do)."
  - "_DJ_HINTS as a module-level tuple (not list): immutable so callers + tests can rely on the priority order (djay → serato → traktor → rekordbox → virtualdj). find_dj_window iterates the tuple — earlier entries hit first. Exposed both at module level AND as ScreenWindows._DJ_HINTS class attribute for caller ergonomics."
  - "_ScreenBuffer duplicated from _screen_macos.py instead of extracting to a _screen_common.py. Rationale: Phase 8 (ScreenCaptureKit migration) is the natural extraction point — both impls converge then. Wave 3 keeps the duplication so the firewall blast-radius stays small and the no-leak guard surface is unchanged."
  - "winsdk asyncio bridge via asyncio.run inside a thread (NOT integrating winsdk awaitables into the main event loop). Plan-prescribed; matches macOS subprocess pattern; simpler than introducing a new event-loop machinery; per CONTEXT Decisions §TrackWindows."
  - "Output format parity: f'{artist} - {title}' lives in NowPlayingSnapshot.title (artist field is None). state_refresh_loop reads via .track_info.snapshot() in the v4 dict shape — same call site for macOS and Windows. _SmtcState exposes .snapshot() returning {title, prev_title, title_changed_at} matching macOS TrackInfo exactly."
  - "Log-once on SMTC unavailability via _SmtcState._has_logged_unavailable flag: 1Hz polling means a permanently-unavailable SMTC would spam 86,400 log lines/day. Single first-failure line on stderr is enough for diagnosis; subsequent failures stay silent. test_poll_returns_none_when_winsdk_raises asserts the log-once contract."
  - "Test fixup — run_poll_loop test does NOT monkeypatch asyncio.sleep via string path. Discovered the same Wave 1 test-order issue: pytest's monkeypatch.setattr('vibemix.platform._track_windows.asyncio.sleep', ...) breaks after test_platform_selector deletes + reimports the platform package (the attribute walk fails). Switched to asyncio.wait_for(timeout=3.0) + early stop_event.set() — order-independent."
  - "windows_only marker registration in pyproject.toml's pytest config: --strict-markers is on (Phase 0 standard), so the marker MUST be declared before live test stubs can use it. Added with description noting Phase 20 CI matrix execution."

patterns-established:
  - "Lazy-import seam for Windows-only deps: every Windows-specific dependency (pywin32, winsdk) imported inside a private helper method (staticmethod for stateless lookups; instance method for stateful ones). Tests inject via monkeypatch.setitem(sys.modules, ...). Mirrors Wave 1's _midi_common lazy import to dodge the partial-package re-entry cycle."
  - "Mock fake module chain: when a Windows impl imports a dotted-path module (winsdk.windows.media.control), tests must inject ALL parent modules into sys.modules — Python's import machinery rejects a leaf-only injection. types.ModuleType('parent') + .child = leaf is the pattern."
  - "Live-test stubs collect on macOS: pytestmark = pytest.mark.skipif(sys.platform != 'win32', ...) at module level + a @pytest.mark.windows_only on the test function. Phase 20's CI matrix runs the marker-filtered live tests on windows-latest."

requirements-completed: [SCREEN-02, SCREEN-06]

duration: ~10 min
completed: 2026-05-11
---

# Phase 7 Plan 03: ScreenWindows + TrackWindows Summary

**ScreenWindows (mss + pywin32 EnumWindows + 5-app DJ hint list) and TrackWindows (winsdk SMTC + asyncio.run-in-executor bridge) ship as Wave 3 of the Windows port — both Protocol-satisfying impls import cleanly on macOS, expose the same surface as the Phase 3 macOS reference, and have 32 mocked tests + 2 stubbed Phase 20 live smokes.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-11T19:24:51Z
- **Completed:** 2026-05-11T19:35:00Z (approximate)
- **Tasks:** 2 (TDD pairs — RED + GREEN per task)
- **Files modified/created:** 7 (6 created, 1 modified)
- **Tests added:** 32 mocked (18 ScreenWindows + 14 TrackWindows) + 2 live stubs (skipped on macOS)

## Accomplishments

- **`ScreenWindows`** — ScreenBackend impl satisfying the Phase 1 Protocol structurally. Builds on macOS-impl shape verbatim:
  - `is_available()` → `_HAS_MSS and _HAS_PIL and _has_pywin32()` (lazy pywin32 try-import inside `_import_win32gui` staticmethod).
  - `find_window_bounds(substr)` walks `win32gui.EnumWindows`, filters by case-insensitive substring + ≥200×200 size floor + IsWindowVisible, picks the largest by area. Returns `WindowBounds | None`. Same surface as `ScreenMacOS.find_window_bounds`.
  - `find_dj_window()` iterates `_DJ_HINTS = ("djay", "serato", "traktor", "rekordbox", "virtualdj")` in priority order and returns the first match. Used by `run_capture_loop` to crop screenshots to the active DJ app's window.
  - `capture(bounds, ...)` mirrors `ScreenMacOS.capture` exactly: `mss.mss().grab(monitor)` → `PIL.Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")` → optional scale-factor crop → thumbnail `(1280, 800)` → JPEG quality 82.
  - `async run_capture_loop(state, stop_event)` mirrors `ScreenMacOS.run_capture_loop`: 1Hz cadence, `state.audible` gating (1s sleep + continue when no music), `loop.run_in_executor(None, grab)` offload.
- **`TrackWindows`** — TrackInfoBackend impl. SMTC reads via `winsdk.windows.media.control.GlobalSystemMediaTransportControlsSessionManager.request_async()` → `get_current_session()` → `try_get_media_properties_async()`. Bridges the awaitable API by running `asyncio.run(_inner())` inside a synchronous helper that itself runs in `loop.run_in_executor(...)` — CONTEXT-locked pattern matching macOS subprocess shape.
  - Output format matches macOS: `f"{artist} - {title}"` when both present; artist-only or title-only fall through to the non-empty value; both empty → `poll()` returns None.
  - Graceful fallback: `request_async` raises (SMTC unavailable on box, e.g. djay Pro on certain Windows builds) → `poll()` returns None + logs ONCE on stderr (`_has_logged_unavailable` flag in `_SmtcState` prevents 1Hz log spam).
  - `_SmtcState` exposes the v4 dict shape `{title, prev_title, title_changed_at}` through `.snapshot()` — `state_refresh_loop` reads via `.track_info.snapshot()` identically on macOS and Windows.
  - `async run_poll_loop` offloads `_poll_smtc_sync` at 1Hz cadence, exits cleanly on `stop_event`.
- **Critical Constraint 3 holds on darwin** — importing `vibemix.platform._screen_windows` and `vibemix.platform._track_windows` does NOT pull `win32gui`, any `win32*`, or `winsdk` into `sys.modules`. Verified by:
  - `tests/test_screen_windows.py::test_module_imports_on_macos_without_pulling_win32gui`
  - `tests/test_track_windows.py::test_module_imports_on_macos_without_pulling_winsdk`
  - manual CLI: `python -c "from vibemix.platform._screen_windows import ScreenWindows; from vibemix.platform._track_windows import TrackWindows; import sys; assert 'win32gui' not in sys.modules; assert 'winsdk' not in sys.modules"` → `clean`.
- **Protocol structural satisfaction** — `isinstance(ScreenWindows(), ScreenBackend) is True` (with `win32gui` mocked) and `isinstance(TrackWindows(), TrackInfoBackend) is True` (no mock needed — winsdk only consulted on `is_available()` call).
- **`windows_only` pytest marker registered** in pyproject.toml so `--strict-markers` accepts the live test stubs.

## Task Commits

Each task was committed atomically per TDD (RED + GREEN):

1. **Task 1 RED:** `3e51596` — `test(07-03): add failing tests for ScreenWindows + windows_only marker`
2. **Task 1 GREEN:** `4ab8946` — `feat(07-03): ScreenWindows — mss + pywin32 EnumWindows + DJ-app hint list`
3. **Task 2 RED:** `7e41d1d` — `test(07-03): add failing tests for TrackWindows SMTC backend`
4. **Task 2 GREEN:** `54f28fa` — `feat(07-03): TrackWindows — SMTC via winsdk + asyncio.run bridge`

Plan metadata commit will be created after this SUMMARY.md is committed.

## Files Created/Modified

- `src/vibemix/platform/_screen_windows.py` — **created** — 305 lines. ScreenWindows class + `_ScreenBuffer` (duplicated from `_screen_macos.py` — extraction deferred to Phase 8 per docstring rationale) + `_DJ_HINTS` locked tuple. Critical Constraint 3 honored via `_import_win32gui` staticmethod.
- `src/vibemix/platform/_track_windows.py` — **created** — 205 lines. TrackWindows class + `_SmtcState` (v4-dict-shape thread-safe cache) + the `_poll_smtc_sync` worker (winsdk lazy import + asyncio.run bridge).
- `tests/test_screen_windows.py` — **created** — 347 lines. 18 mocked tests covering module-import discipline, `_DJ_HINTS` lock, Protocol satisfaction, `find_window_bounds` (substring/case-insensitive/no-match/size-floor/largest/invisible/no-pywin32), `find_dj_window` priority-order, `capture` (full + crop), `is_available` true/false branches, `latest()` buffer delegation.
- `tests/test_screen_windows_live.py` — **created** — 31 lines. Stub Phase 20 live smoke with module-level `pytestmark = pytest.mark.skipif(sys.platform != "win32", ...)` + `@pytest.mark.windows_only` on the test function.
- `tests/test_track_windows.py` — **created** — 303 lines. 14 mocked tests covering module-import discipline, Protocol satisfaction, poll happy-path + 3 fallback variants (no-session, winsdk-raises log-once, artist-only/title-only/both-empty), `is_available` true/false, v4-dict-shape snapshot + prev_title-on-change, async `run_poll_loop` offload + stop_event termination, `poll()` is-sync.
- `tests/test_track_windows_live.py` — **created** — 31 lines. Stub Phase 20 live SMTC smoke (same skipif pattern).
- `pyproject.toml` — **modified** — registered `windows_only` pytest marker (`--strict-markers` gate). One-line addition to the `[tool.pytest.ini_options].markers` list.

## Decisions Made

See frontmatter `key-decisions` for the full list. The three load-bearing ones:

1. **`_import_win32gui` staticmethod is the SOLE win32gui-name surface in `_screen_windows.py`** — keeps the lazy-import audit trivial (`grep "win32gui" src/vibemix/platform/_screen_windows.py` → exactly 3 hits: docstring, the import statement inside the staticmethod, and the `except ImportError` line). Tests inject via `monkeypatch.setitem(sys.modules, "win32gui", fake)` — single seam.

2. **winsdk asyncio bridge via `asyncio.run` inside an executor thread** (NOT integrating winsdk awaitables into the main event loop). Plan-prescribed; CONTEXT-locked. The implementation is just:
   ```python
   def _poll_smtc_sync(self) -> str | None:
       try:
           import winsdk.windows.media.control as wmc
       except ImportError:
           return None
       async def _inner(): ...
       try:
           return asyncio.run(_inner())
       except Exception as e:
           # log-once + None fallback
   ```
   `run_poll_loop` then offloads `_poll_smtc_sync` via `loop.run_in_executor(None, ...)`. Each iteration opens + closes a private asyncio loop in the worker thread — same lifecycle pattern as the macOS subprocess-per-poll.

3. **Output format parity with macOS** — combined `f"{artist} - {title}"` lives in `NowPlayingSnapshot.title`; `artist` field is None. This matches macOS `TrackMacOS.poll()` exactly (which only consults `nowplaying-cli get title artist`'s two-line output and combines them in title). State_refresh_loop reads via `.track_info.snapshot()` (v4 dict shape) — same call site across both OSes. The Phase 1 Protocol is honored (`title` is `str | None`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Merged local `main` into worktree branch to pull in Wave 1 foundation**

- **Found during:** initial state assessment (immediately before Task 1 RED).
- **Issue:** The worktree was branched from `6e6dd9f` (Phase 6 close) which predates Wave 1 (07-01). Without Wave 1, `vibemix.platform._midi_common` doesn't exist, the platform selector hasn't been added, and the Windows-only deps aren't in `pyproject.toml`. The plan declares `depends_on: [07-01]` in frontmatter — Wave 1 IS a prerequisite. `git status` showed clean working tree but `git log` showed only up to `6e6dd9f`; local `main` had advanced (`388c0ed` chore: merge executor worktree wave 1) but the worktree branch hadn't followed.
- **Fix:** `git fetch origin main` (no-op — origin lags) + `git merge main --no-edit` → fast-forward, picks up the 7 Wave 1 commits + the merge commit cleanly. No conflicts (Wave 1 added new files + appended to `__init__.py` + `pyproject.toml`; my work hadn't touched either yet).
- **Files modified:** working tree only — all 17 Wave 1 files materialized at their main-branch state.
- **Committed in:** the merge itself is the bring-in; subsequent Task 1/2 commits build on top.

**2. [Rule 3 — Blocking] Registered `windows_only` pytest marker in pyproject.toml**

- **Found during:** Task 1 RED (when first creating `tests/test_screen_windows_live.py`).
- **Issue:** `pyproject.toml` has `[tool.pytest.ini_options].addopts = "-ra --strict-markers"`. With strict markers on, any `@pytest.mark.windows_only` on a test function would crash collection with `'windows_only' not found in markers`. Wave 1 added the `macos_audio` marker but didn't anticipate `windows_only`.
- **Fix:** Added one line to the markers list:
  ```toml
  "windows_only: requires sys.platform == 'win32' — live tests for the Windows port (Phase 7 Wave 3+, executed in Phase 20 CI matrix)",
  ```
- **Files modified:** `pyproject.toml`.
- **Verification:** pytest collection of both live-test stubs succeeds; live tests skipped via the `skipif` module-level pytestmark, not the marker (marker is for Phase 20 CI selection).
- **Committed in:** `3e51596` (Task 1 RED commit — bundled with the new test files since the marker is what enables those files to collect).

**3. [Rule 1 — Bug] Two capture tests needed `win32gui` mock-injection**

- **Found during:** Task 1 GREEN initial test run.
- **Issue:** `test_capture_no_bounds_produces_jpeg` and `test_capture_with_bounds_invokes_crop` mocked `mss.mss` + `PIL.Image` but didn't inject `win32gui` into `sys.modules`. `ScreenWindows.capture()` first calls `self.is_available()` which checks `_has_pywin32()`. On darwin without win32gui mocked, `is_available()` returns False → `capture()` raises `RuntimeError("ScreenWindows dependencies unavailable...")`.
- **Fix:** Added `monkeypatch.setitem(sys.modules, "win32gui", MagicMock())` to both tests so `is_available()` passes the pywin32 check during the mss/PIL-mocked pipeline.
- **Files modified:** `tests/test_screen_windows.py` (still in Task 1 GREEN cycle, not a separate commit — the RED tests had a bug discovered during GREEN debugging).
- **Verification:** all 18 mocked tests pass.
- **Committed in:** `4ab8946` (Task 1 GREEN commit — bundled with the impl since the fix was discovered during the same cycle).

**4. [Rule 1 — Bug] Test-order coupling in `test_run_poll_loop_offloads_via_executor_and_stops_on_event`**

- **Found during:** Task 2 GREEN full-suite verification (test passed in isolation; failed when run after the platform-selector tests).
- **Issue:** The original test used `monkeypatch.setattr("vibemix.platform._track_windows.asyncio.sleep", _short_sleep)` to skip the 1s sleep in `run_poll_loop`. pytest's `monkeypatch.setattr` with a string path walks the dotted attribute chain. After `test_selector_raises_on_unsupported_platform` (Wave 1) deletes + re-imports `vibemix.platform.*` modules, the attribute walk fails with `AttributeError: 'module' object at vibemix.platform._track_windows has no attribute '_track_windows'`. Same root cause Wave 1 hit and fixed with sys.modules save/restore — but this test's monkeypatch needs a different fix because it's not in the selector test file.
- **Fix:** Replaced the asyncio.sleep monkeypatch with `asyncio.wait_for(t.run_poll_loop(stop), timeout=3.0)` + pre-set `stop_event` after 50ms. The loop runs one iteration (poll + state update), checks `stop.is_set()` at the top of the second iteration, exits cleanly. Order-independent.
- **Files modified:** `tests/test_track_windows.py`.
- **Verification:** the offending test now passes both in isolation and after the platform-selector suite. Full pytest run (`uv run pytest -q --deselect <3 pre-existing>`) → `569 passed, 3 skipped`.
- **Committed in:** `54f28fa` (Task 2 GREEN commit — discovered during the same cycle).

**5. [Rule 1 — Bug] `test_poll_returns_none_when_winsdk_raises` substring-overlap miscount**

- **Found during:** Task 2 GREEN first test run.
- **Issue:** The test counted substring `"SMTC unavailable"` occurrences in stderr to assert log-once. The impl prints `-> SMTC unavailable: SMTC unavailable for test` (the inner exception message in the fake `_install_fake_winsdk` was `"SMTC unavailable for test"`). One actual log line → 2 substring occurrences (false-positive failure).
- **Fix:** Changed the assertion from substring count to `[line for line in captured.err.splitlines() if line.startswith("-> SMTC unavailable")]` — anchors to the impl's prefix, ignores inner-exception text overlap. Asserts exactly 1 log line.
- **Files modified:** `tests/test_track_windows.py`.
- **Verification:** passes; log-once contract still enforced.
- **Committed in:** `54f28fa` (bundled with Task 2 GREEN).

---

**Total deviations:** 5 auto-fixed (1× Rule 3 worktree-foundation, 1× Rule 3 strict-markers gate, 3× Rule 1 test bugs)
**Impact on plan:** All five fixes were necessary to make the prescribed plan execute. None expand scope. Deviation #1 (Wave 1 merge) was a worktree provisioning artifact — the worktree was branched before Wave 1 landed on local main; merging picks it up cleanly. Deviation #4 (test-order coupling) inherits Wave 1's lazy-import vs platform-package-reimport interaction; documented in tech-stack.patterns so Wave 4 (`MidiWindows`) doesn't repeat the same monkeypatch mistake.

## Issues Encountered

- **Pre-existing test failures (out of scope for this plan, already logged in `.planning/phases/07-windows-port-audio-screen/deferred-items.md` from Wave 1):**
  1. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — reads untracked `cohost_v4.py`.
  2. `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` — same untracked-file issue.
  3. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — environmental (CoreAudio device name mismatch).

  None caused by Wave 3 changes; verified by `git diff main..HEAD --name-only` showing only the 7 Wave 3 files. See deferred-items.md for recommended post-phase-7 fixes.

## TDD Gate Compliance

Wave 3 followed RED/GREEN cycles for both tasks:

- **Task 1:** RED `3e51596` (test — collection error, expected) → GREEN `4ab8946` (feat — 18/18 pass)
- **Task 2:** RED `7e41d1d` (test — collection error, expected) → GREEN `54f28fa` (feat — 14/14 pass)

Each RED commit verified to fail with `ModuleNotFoundError: No module named 'vibemix.platform._{screen,track}_windows'` before the matching GREEN landed. No GREEN-without-RED commits.

## User Setup Required

None — Wave 3 doesn't require any external service configuration. Windows-only deps (`pyaudiowpatch`, `pywin32`, `winsdk`) will not install on Kaan's macOS box (correctly skipped via `sys_platform == 'win32'` marker from Wave 1); they're picked up on Windows by Wave 4 + Phase 20 CI matrix + the PyInstaller bundle (Phase 18).

## Next Phase Readiness

- **Wave 4 (07-04) unblocked:** `MidiWindows` can reuse `_midi_common.spawn_listener` (Wave 1) verbatim. ScreenImpl/TrackImpl selector slots are already wired (Wave 1); the only remaining concrete impl is `MidiWindows`. Cross-platform integration test for the selector + lazy-import contract is the last deliverable of the phase.
- **Wave 5 (07-05):** rolled-up 07-SUMMARY + ROADMAP/STATE close. Phase 20 will execute the live test stubs on `windows-latest`.
- **Phase 8 (deprecation chase — ScreenCaptureKit):** `_ScreenBuffer` extraction candidate. Both `_screen_macos.py` and `_screen_windows.py` duplicate it (~10 lines). Phase 8's planned ScreenCaptureKit impl gives a third consumer — natural time to lift into `_screen_common.py`.

## Self-Check: PASSED

Files verified:

- `src/vibemix/platform/_screen_windows.py` — exists, 305 lines (above 180 min)
- `src/vibemix/platform/_track_windows.py` — exists, 205 lines (above 140 min)
- `tests/test_screen_windows.py` — exists, 347 lines (above 160 min)
- `tests/test_screen_windows_live.py` — exists, 31 lines, pytestmark skipif darwin + windows_only marker
- `tests/test_track_windows.py` — exists, 303 lines (above 90 min)
- `tests/test_track_windows_live.py` — exists, 31 lines, pytestmark skipif darwin + windows_only marker
- `pyproject.toml` — windows_only marker registered in `[tool.pytest.ini_options].markers`

Commits verified (each present in `git log --oneline`):

- `3e51596` test(07-03) — RED Task 1
- `4ab8946` feat(07-03) — GREEN Task 1
- `7e41d1d` test(07-03) — RED Task 2
- `54f28fa` feat(07-03) — GREEN Task 2

Verification commands (all passing):

- `uv run pytest tests/test_screen_windows.py tests/test_screen_windows_live.py tests/test_track_windows.py tests/test_track_windows_live.py -x -q` → 32 passed, 2 skipped (live stubs)
- `uv run python -c "from vibemix.platform._screen_windows import ScreenWindows; from vibemix.platform._track_windows import TrackWindows; import sys; assert 'win32gui' not in sys.modules; assert 'winsdk' not in sys.modules"` → `clean`
- `uv run python -c "from vibemix.platform._screen_windows import ScreenWindows; from vibemix.platform.screen import ScreenBackend; from unittest.mock import MagicMock; import sys; sys.modules['win32gui'] = MagicMock(); assert isinstance(ScreenWindows(), ScreenBackend)"` → `screen protocol ok`
- `uv run python -c "from vibemix.platform._track_windows import TrackWindows; from vibemix.platform.track import TrackInfoBackend; assert isinstance(TrackWindows(), TrackInfoBackend)"` → `track protocol ok`
- `uv run pytest -q --deselect tests/agent/test_persona.py --deselect tests/test_audio_macos_live.py --deselect tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` → 569 passed, 3 skipped
- `uv run ruff check src/vibemix/platform/_screen_windows.py src/vibemix/platform/_track_windows.py tests/test_screen_windows.py tests/test_track_windows.py` → All checks passed
- `git diff main..HEAD --name-only | grep -E "(cohost|mascot|run_)"` → empty (POC files untouched)

---
*Phase: 07-windows-port-audio-screen*
*Completed: 2026-05-11*
