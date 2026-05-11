---
phase: 07-windows-port-audio-screen
plan: 01
subsystem: infra
tags: [platform-selector, midi-common, windows-deps, refactor, pyproject]

requires:
  - phase: 01-platform-protocol-firewall
    provides: AudioBackend / ScreenBackend / MidiBackend / TrackInfoBackend Protocols
  - phase: 03-sensing-state-port
    provides: MidiMacOS + ControllerState + _CC_MAP / _NOTE_MAP (the DDJ-FLX4 IP that survives intact)
provides:
  - sys.platform-dispatched AudioImpl / ScreenImpl / MidiImpl / TrackImpl selector at vibemix.platform
  - cross-platform midi_listener_thread + spawn_listener (vibemix.platform._midi_common)
  - Windows-only pyaudiowpatch / pywin32 / winsdk deps gated on sys_platform == 'win32'
affects:
  - 07-02 (Wave 2: AudioWindows imports AudioImpl wiring + pyaudiowpatch)
  - 07-03 (Wave 3: ScreenWindows + TrackWindows import via selector + pywin32 / winsdk)
  - 07-04 (Wave 4: MidiWindows imports _midi_common.spawn_listener)
  - 07-05 (Wave 5: rolled-up 07-SUMMARY + close)
  - 09-controller-library (extracts more MIDI machinery into _midi_common; this wave is the first cut)
  - 11-tauri-shell (calibration wizard reads sys.platform to pick OS-specific permissions flow)

tech-stack:
  added:
    - pyaudiowpatch>=0.2.12 (Windows WASAPI loopback — Wave 2 consumer)
    - pywin32>=308 (Windows EnumWindows / SMTC FFI — Wave 3 consumer)
    - winsdk>=1.0.0b10 (Microsoft official winrt successor — Wave 3 SMTC reader)
  patterns:
    - "Lazy intra-package import: when a sibling module under vibemix.platform needs another sibling, import inside the method (NOT top-of-file) to sidestep the __init__.py re-entry cycle"
    - "Test-injection seam via module parameter: midi_listener_thread accepts mido_module as a positional argument so unit tests pass a SimpleNamespace fake — production callers pass the real mido. No global monkeypatching needed."
    - "Sys-modules save/restore in selector tests: tests that delete vibemix.platform.* and re-import must restore the original module identities in a finally block, otherwise pytest's monkeypatch.setattr(string_path) crashes downstream tests with AttributeError"

key-files:
  created:
    - src/vibemix/platform/_midi_common.py
    - tests/test_midi_common.py
    - tests/test_platform_selector.py
  modified:
    - src/vibemix/platform/__init__.py
    - src/vibemix/platform/_midi_macos.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Lazy import of _midi_common inside MidiMacOS.start_listener_thread (not at module top) — the package __init__.py imports _midi_macos, so a top-level import of _midi_common would re-enter the partially-loaded package and risk a circular-import deadlock. Lazy import sidesteps the cycle entirely."
  - "winsdk version pin >=1.0.0b10 (not >=1.0): the published version on PyPI is still beta (latest 1.0.0b10 as of 2026-05). Pinning to the stable >=1.0 made uv refuse to resolve the deps. Production tracks the latest beta until Microsoft graduates to 1.0.0."
  - "Selector branch eager-imports the _*_windows modules on win32 (not lazy). Eager surfaces missing-impl bugs at startup instead of at first-use — important because the runtime orchestrator instantiates AudioImpl right after package import, so any missing concrete impl would crash with an ImportError that's easier to debug at startup than mid-session."
  - "AudioMacOS / ScreenMacOS / MidiMacOS / TrackMacOS re-exports STAY exposed via __all__ alongside the new *Impl aliases — Phase 3 tests import the macOS-named classes directly, and removing them would force a cascade of test rewrites for zero gain."
  - "_midi_common.py is intentionally minimal in Wave 1 — only the listener loop moved over. _CC_MAP / _NOTE_MAP / ControllerState / _knob_label / _xfader_label STAY in _midi_macos.py because the DDJ-FLX4 IP is the same on macOS and Windows but the file boundary keeps the platform-specific blast radius small. Phase 9 (controller library) is the natural time to extract those further."
  - "_midi_macos.py::start_listener_thread returns an inert daemon Thread (target=lambda: None) when _HAS_MIDO is False so callers can .join() without special-casing the no-mido path — preserves the existing API contract."
  - "Phase 7 docs (07-CONTEXT.md + 07-01-PLAN.md … 07-05-PLAN.md) already exist on main; this worktree was branched off Phase 6 close. The plan docs were checked out from main into the worktree as read-only references and intentionally NOT committed in this branch — the orchestrator owns those writes."

patterns-established:
  - "Platform selector at __init__.py: sys.platform branches into eager imports of concrete impls aliased as AudioImpl / ScreenImpl / MidiImpl / TrackImpl. Linux + other platforms raise immediately."
  - "Cross-platform extraction policy: extract code into _*_common.py ONLY when a second platform is about to consume it (Phase 7 = first Windows landing → Phase 7 = right time to extract MIDI listener; controller maps stay platform-local until Phase 9 expands controller support)."
  - "Selector tests must restore sys.modules: any test that drops + re-imports vibemix.platform.* must save/restore the originals in a finally block."

requirements-completed: [ARCH-02]

duration: ~30 min
completed: 2026-05-11
---

# Phase 7 Plan 01: Platform Selector + MIDI Common Extraction Summary

**sys.platform-dispatched AudioImpl/ScreenImpl/MidiImpl/TrackImpl selector + cross-platform _midi_common.py extraction + Windows-only deps gated on sys_platform == 'win32' — Wave 1 foundation for the Windows port.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-11T18:50:00Z (approximate)
- **Completed:** 2026-05-11T19:20:04Z
- **Tasks:** 2 (TDD pairs: RED commit + GREEN commit per task, plus one ruff format fixup)
- **Files modified:** 7 (3 created, 4 modified)
- **Tests added:** 10 (5 _midi_common + 6 selector — but 1 of the "selector 6" is the no-marker-violation pyproject test; collected as 10 total new tests)

## Accomplishments

- **`vibemix.platform.__init__.py` selector dispatch** — `AudioImpl` / `ScreenImpl` / `MidiImpl` / `TrackImpl` now alias to the macOS Phase 2/3 classes on darwin; on win32 they will alias to the Wave 2-4 `_*_windows` modules; any other platform raises `RuntimeError`. Runtime orchestrator + future calibration wizard can instantiate by these names without an inline `sys.platform` check.
- **`src/vibemix/platform/_midi_common.py` created** — exposes `midi_listener_thread(controller_state, stop_event, port_hint, mido_module)` + `spawn_listener` convenience wrapper. Body lifted verbatim from `_midi_macos.py::MidiMacOS.start_listener_thread._run` (which was a verbatim port of `cohost_v4.py:730-756`). Production callers pass real `mido`; tests pass a `SimpleNamespace` fake. Wave 4's `_midi_windows.py` will reuse it byte-for-byte.
- **`_midi_macos.py::MidiMacOS.start_listener_thread` refactored** — body shrunk from a 26-line inline closure to a 7-line delegation call. Behavior pinned byte-identical via the new golden regression test (`test_midi_macos_golden_unchanged_behavior_after_refactor`): feeding the same scripted DDJ-FLX4 message sequence through (a) direct `handle_msg` and (b) the new listener thread yields equal `deck_snapshot()` and `moves_since()` outputs.
- **`pyproject.toml` Windows-only deps** — `pyaudiowpatch>=0.2.12`, `pywin32>=308`, `winsdk>=1.0.0b10` all gated on `sys_platform == 'win32'`. `uv sync` on macOS skips them; PyInstaller on Windows picks them up automatically. `uv.lock` regenerated cleanly — only Windows wheels added, no cross-platform changes.

## Task Commits

Each task was committed atomically per TDD (RED + GREEN), plus one formatting fixup:

1. **Task 1 RED: failing tests for `_midi_common` listener** — `2a872f0` (test)
2. **Task 1 GREEN: extract MIDI listener loop into `_midi_common.py`** — `49e0186` (feat)
3. **Task 2 RED: failing tests for platform selector + Windows deps** — `51c74ed` (test)
4. **Task 2 GREEN: platform selector + Windows-only deps** — `26a3573` (feat)
5. **Style fixup: ruff format `test_midi_common.py`** — `31314d7` (style)

Plan metadata commit will be created after this SUMMARY.md is committed.

## Files Created/Modified

- `src/vibemix/platform/_midi_common.py` — **created** — cross-platform MIDI listener loop (`midi_listener_thread` + `spawn_listener`). The `mido_module` parameter is the test-injection seam.
- `src/vibemix/platform/__init__.py` — **modified** — added `sys.platform`-dispatched `AudioImpl` / `ScreenImpl` / `MidiImpl` / `TrackImpl` aliases + appended to `__all__`. Linux/etc. raise `RuntimeError`.
- `src/vibemix/platform/_midi_macos.py` — **modified** — `start_listener_thread` now delegates to `_midi_common.spawn_listener`. No-mido path returns an inert daemon thread so the API contract (`.join()`-able) survives. Module docstring updated to reflect the refactor.
- `pyproject.toml` — **modified** — added 3 Windows-only deps with `sys_platform == 'win32'` markers.
- `uv.lock` — **modified** — auto-regenerated by `uv sync`; only Windows wheels added.
- `tests/test_midi_common.py` — **created** — 5 tests: 4 listener-loop tests (port match + dispatch, no-match retry, exception swallow, case-insensitive match) + 1 golden regression test confirming `_midi_common.midi_listener_thread` produces byte-identical `ControllerState` mutations vs direct `handle_msg`.
- `tests/test_platform_selector.py` — **created** — 6 tests: macOS impl resolution, no-leak guard against pyaudiowpatch/winsdk/win32/`_*_windows` in `sys.modules`, Linux RuntimeError, and 2 pyproject marker checks. Includes save/restore cleanup of `sys.modules` so the linux-monkeypatch test doesn't pollute downstream tests' module identities.

## Decisions Made

See frontmatter `key-decisions` for the seven calls made during execution. The two non-obvious ones:

1. **Lazy import of `_midi_common` inside `start_listener_thread`** — a top-level `from vibemix.platform import _midi_common` would have re-entered the partially-loaded `__init__.py` (which imports `_midi_macos`) and risked a circular-import deadlock on cold start. The lazy import is the cheap fix; performance impact is one extra `import` call per agent startup which is negligible.

2. **`winsdk>=1.0.0b10` instead of `>=1.0`** — the plan asked for `winsdk>=1.0`, but PyPI's latest is still beta `1.0.0b10`. `uv` refused to resolve `>=1.0` because the published version is `1.0.0b10` which is `<` the constraint per PEP 440 pre-release ordering. Pinned to the beta directly with a comment explaining the upgrade path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adjusted `winsdk` version constraint from `>=1.0` to `>=1.0.0b10`**

- **Found during:** Task 2 GREEN (running `uv run pytest` after editing `pyproject.toml`)
- **Issue:** `uv` refused to resolve dependencies with the plan-prescribed `winsdk>=1.0` constraint because PyPI's latest published version is `1.0.0b10` (a pre-release per PEP 440). Resolver error: `Because only winsdk{sys_platform == 'win32'}<=1.0.0b10 is available and your project depends on winsdk{sys_platform == 'win32'}>=1.0, we can conclude that your project's requirements are unsatisfiable.`
- **Fix:** Pinned to `winsdk>=1.0.0b10` with a comment in `pyproject.toml` documenting the upgrade path when Microsoft graduates the package to a stable 1.0.0 release.
- **Files modified:** `pyproject.toml`
- **Verification:** `uv sync` resolves cleanly (109 packages); selector tests pass; `winsdk` not present in `sys.modules` on darwin (Linux-platform test confirms selector raises before any winsdk import would be attempted).
- **Committed in:** `26a3573` (Task 2 GREEN commit)

**2. [Rule 3 - Blocking] Added `sys.modules` save/restore cleanup in selector tests**

- **Found during:** Task 2 GREEN (initial test run showed `test_midi_macos_golden_unchanged_behavior_after_refactor` crashing when run alongside selector tests, with `AttributeError: 'module' object at vibemix.platform._midi_macos has no attribute '_midi_macos'`)
- **Issue:** `test_selector_raises_on_unsupported_platform` deletes all `vibemix.platform.*` modules from `sys.modules` then attempts `importlib.import_module("vibemix.platform")` which raises (as expected). That partial-import side effect leaves the `_midi_macos` module reference in a stale state — pytest's `monkeypatch.setattr("vibemix.platform._midi_macos.time.time", ...)` then can't resolve the path and crashes a later golden test.
- **Fix:** Wrapped the two `sys.modules`-mutating selector tests in `try/finally` that (a) snapshots the pre-test set of `vibemix.platform.*` entries, (b) lets the test run, (c) drops any partial-import remnants in the finally block, (d) restores the original modules. Subsequent tests see byte-identical module identities.
- **Files modified:** `tests/test_platform_selector.py` (Task 2 RED test file, fixed before Task 2 GREEN commit)
- **Verification:** `uv run pytest tests/test_platform_selector.py tests/test_platform.py tests/test_midi_macos.py tests/test_midi_common.py -q` → 42 pass.
- **Committed in:** `26a3573` (Task 2 GREEN commit — the test-cleanup fix was bundled with the selector implementation since it was discovered during GREEN debugging)

**3. [Plan-prescribed but non-trivial] Lazy import of `_midi_common` inside `MidiMacOS.start_listener_thread`**

- **Found during:** Task 1 GREEN (initial attempt to add `from vibemix.platform import _midi_common` at the top of `_midi_macos.py`)
- **Issue:** A top-level `from vibemix.platform import _midi_common` triggers `vibemix.platform.__init__.py` execution, which itself imports `_midi_macos` at the top of the file. Result: a partial-import cycle where `_midi_macos.py` runs to its top-level `import _midi_common` → `__init__.py` starts → `__init__.py` calls `from vibemix.platform._midi_macos import MidiMacOS` → `_midi_macos.py` is mid-execution and `MidiMacOS` is not yet defined → `ImportError`.
- **Fix:** Moved the `_midi_common` import inside `MidiMacOS.start_listener_thread`. This is documented at the top of `_midi_macos.py` with a comment explaining the cycle.
- **Files modified:** `src/vibemix/platform/_midi_macos.py`
- **Verification:** `uv run pytest tests/test_midi_macos.py tests/test_midi_common.py` → 32 pass.
- **Committed in:** `49e0186` (Task 1 GREEN commit)

---

**Total deviations:** 3 auto-fixed (3× Rule 3 - Blocking)
**Impact on plan:** All three fixes were necessary to make the prescribed plan execute. None expand scope; all are tactical adjustments. The lazy-import pattern is now documented in the file and the frontmatter `tech-stack.patterns` so Wave 4 (`_midi_windows.py`) doesn't re-encounter it.

## Issues Encountered

- **Pre-existing test failures (out of scope for this plan, logged in `deferred-items.md`):**
  1. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — reads untracked `cohost_v4.py` which isn't in the worktree.
  2. `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` — same untracked-file issue.
  3. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — environmental ("Headphones" device substring doesn't match Kaan's CoreAudio device list "HEADPHONEMG").

  None of these are caused by Wave 1 changes; they existed on the worktree base commit `6e6dd9f`. See `.planning/phases/07-windows-port-audio-screen/deferred-items.md` for the recommended post-phase-7 fixes.

## TDD Gate Compliance

Wave 1 followed RED/GREEN cycles for both tasks:

- **Task 1:** RED `2a872f0` (test) → GREEN `49e0186` (feat) — `_midi_common.py` listener tests.
- **Task 2:** RED `51c74ed` (test) → GREEN `26a3573` (feat) — selector + pyproject tests.

Each RED commit verified to actually fail (ImportError) before the matching GREEN landed. No GREEN-without-RED commits.

## User Setup Required

None — no external service configuration. Windows-only deps will not install on Kaan's macOS box (correctly skipped via `sys_platform == 'win32'` marker); they're picked up on Windows by Wave 2-4's CI (Phase 20) and the PyInstaller bundle (Phase 18).

## Next Phase Readiness

- **Wave 2 (07-02) unblocked:** `AudioWindows` can import via the selector slot; `pyaudiowpatch` is available in `uv.lock` on win32.
- **Wave 3 (07-03) unblocked:** `ScreenWindows` + `TrackWindows` selector slots are in place; `pywin32` + `winsdk` resolved on win32.
- **Wave 4 (07-04) unblocked:** `MidiWindows` will call `_midi_common.spawn_listener(controller_state, stop_event, "DDJ-FLX4", mido)` verbatim — same call signature MidiMacOS uses today.
- **Phase 11 (calibration wizard):** can use `sys.platform` to branch on OS-specific permissions flow; the selector raising on Linux gives a clean early-error path if anyone tries to run on an unsupported OS.

## Self-Check: PASSED

Files verified:

- `src/vibemix/platform/_midi_common.py` — exists, 92 lines (above 60 min)
- `src/vibemix/platform/__init__.py` — contains `if _sys.platform == "darwin"` selector + appended `*Impl` names to `__all__`
- `src/vibemix/platform/_midi_macos.py` — `start_listener_thread` delegates to `_midi_common.spawn_listener`
- `pyproject.toml` — contains `sys_platform == 'win32'` markers on pyaudiowpatch / pywin32 / winsdk
- `tests/test_platform_selector.py` — exists, 6 selector + pyproject tests, ≥40 lines (actual ~150)
- `tests/test_midi_common.py` — exists, 5 tests (4 listener + 1 golden), ≥50 lines (actual ~270)

Commits verified (each present in `git log --oneline`):

- `2a872f0` test(07-01) — RED Task 1
- `49e0186` feat(07-01) — GREEN Task 1
- `51c74ed` test(07-01) — RED Task 2
- `26a3573` feat(07-01) — GREEN Task 2
- `31314d7` style(07-01) — ruff format fixup

Verification commands (all passing):

- `uv run pytest tests/test_platform.py tests/test_platform_selector.py tests/test_midi_common.py tests/test_midi_macos.py -q` → 42 passed
- `uv run pytest --ignore=tests/agent/test_persona.py --ignore=tests/test_audio_macos_live.py --deselect tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke -q` → 537 passed, 1 skipped (live smoke opt-in)
- `uv sync` on darwin → resolves 109 packages, no error
- `uv run python -c "import vibemix.platform; import sys; assert 'pyaudiowpatch' not in sys.modules; assert 'winsdk' not in sys.modules; assert not any(m.startswith('win32') for m in sys.modules)"` → no leak
- `uv run ruff check src/vibemix/platform/` → All checks passed
- `uv run ruff format --check src/vibemix/platform/ tests/` → all formatted
- POC files (`cohost.py`, `cohost_lk.py`, `cohost_v2.py`, `mascot.html`, `run*.sh`) diff vs `main` is empty

---
*Phase: 07-windows-port-audio-screen*
*Completed: 2026-05-11*
