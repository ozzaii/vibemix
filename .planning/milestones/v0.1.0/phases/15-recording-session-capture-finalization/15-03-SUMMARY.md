---
phase: 15
plan: 03
subsystem: recordings
tags: [recordings-index, retention-sweep, ipc-handlers, scandir, path-traversal, wave-2]
requires:
  - phase: 15
    plan: 01
    provides: 7 ipc.recordings.* wire shapes (list / list_result / delete / delete_ack / usage / events / events_result)
  - phase: 15
    plan: 02
    provides: session.json two-write writer + sweep_crashed_sessions + production recordings_root + Tauri assetProtocol
provides:
  - RecordingsIndex (list / compute_usage / delete / read_events) — scandir-based, two-layer path-traversal gate
  - run_retention_sweep — verbatim RESEARCH Pattern 3; ∞-sentinel short-circuit; best-effort rmtree continuation
  - 3 SessionLoop IPC handlers (_on_recordings_list / _on_recordings_delete / _on_recordings_events) + push helper (_emit_recordings_usage)
  - run_boot_sweeps + on_session_close (3-trigger retention sweep entry points)
  - SettingsApplier.recordings_root + _apply_retention extension (settings-change sweep + usage emit)
  - __main__ cascade boot + close retention-sweep call sites for parity with the sidecar path
affects:
  - phase: 15-04 (recording browser UI consumes ipc.recordings.list_result / events_result / usage)
  - phase: 15-05 (SettingsDrawer wiring consumes recordings.usage push for the disk-usage line)
  - phase: 15-06 (verification gates the 3-trigger sweep + path-traversal regression)
tech-stack:
  added: []  # zero new pip / npm deps — stdlib (os, re, shutil, wave, json, datetime, pathlib) + existing vibemix.ui_bus contracts
  patterns:
    - "Two-layer path-traversal gate: SESSION_DIR_RE regex + Path.resolve().is_relative_to(root.resolve()) — defense in depth (schema is gate 1, runtime is gate 2)"
    - "scandir-based size summation per RESEARCH PEP 471 — single syscall on POSIX, cached on Windows"
    - "Discriminated-success return on read_events: (events, None) success | (None, error_code) failure"
    - "Inline import for recordings_index in settings._apply_retention to keep import surface clean"
    - "Best-effort sweep with outer try/except — never raises into SessionLoop / SettingsApplier"
    - "Sentinel 36500 short-circuits BEFORE scandir — verified via monkey-patched scandir-tracking test"
key-files:
  created:
    - src/vibemix/runtime/recordings_index.py
    - tests/recording/test_recordings_index.py
    - tests/recording/test_retention_sweep.py
    - .planning/phases/15-recording-session-capture-finalization/15-03-SUMMARY.md
  modified:
    - src/vibemix/runtime/session_loop.py
    - src/vibemix/runtime/settings.py
    - src/vibemix/__main__.py
    - .planning/phases/15-recording-session-capture-finalization/deferred-items.md
decisions:
  - "Path-traversal gate is two-layer (schema + runtime). The runtime layer rejects 7 attack shapes: dotted paths (../..), absolute paths (/etc/passwd), embedded traversal (20260513-210410/../escape), null-byte injection, dot-only, double-dot-only, plus the symlink-redirect case mitigated by Path.resolve() following symlinks BEFORE is_relative_to compares."
  - "Legacy-dir synthesis (Pitfall 9) is triggered both by absent session.json AND by malformed session.json — bad JSON is treated as 'no session.json' so the row still surfaces in the list."
  - "bytes_total ALWAYS comes from a fresh scandir, never from session.json's cached counts — ongoing-session rows display live disk usage even when session.json's voice_wav_bytes is still the placeholder 0 from __init__."
  - "Sort key is the dir-name-derived unix timestamp (parsed via strptime), NOT mtime — stable across boots / OSes (mtimes drift on rsync migrations)."
  - "read_events returns ([], None) for the regex-match-but-not-on-disk case (well-defined empty success) instead of an error code — matches the 'session has no events recorded' semantics the UI needs for legacy / freshly-started sessions."
  - "_on_recordings_delete emits a fresh ipc.recordings.usage push AFTER the delete_ack so the drawer's disk-usage line updates without a polling round-trip."
  - "run_boot_sweeps is wired into SessionLoop.run() AFTER boot() but BEFORE the snapshot loop starts — by the time the renderer's first connect resolves, the disk-usage state is accurate."
  - "Cascade main() in __main__.py gets its own boot + close retention-sweep call sites (does NOT construct a SessionLoop). load_config is re-read at both trigger points so persisted retention_days changes apply on the next launch even without a SessionLoop in the cascade path."
metrics:
  duration: ~40min
  completed_at: "2026-05-13T15:00:00Z"
  tasks: 3
  commits: 4
  files_created: 4
  files_modified: 4
  python_tests_new: 28
  schema_oneOf_delta: "34 → 34 (no schema changes in Plan 15-03 — this plan implements the producers, not the wire shapes)"
---

# Phase 15 Plan 03: RecordingsIndex + RetentionSweep + IPC Handlers Summary

**One-liner:** Scandir-based RecordingsIndex with two-layer path-traversal gate (regex + is_relative_to), 3-trigger retention sweep (boot / settings-change / session-close) with ∞-sentinel short-circuit, and 3 new SessionLoop IPC handlers (`recordings.list` / `.delete` / `.events`) plus a `recordings.usage` push emitter — 28 new tests green, zero new pip/npm deps, zero schema changes.

## Outcome

The Python sidecar half of the recording browser is wired end-to-end:

- **RecordingsIndex** (180 LOC) lists every session newest-first by dir-name unix timestamp, synthesizing legacy-dir summaries from WAV header + JSONL line count per RESEARCH Pitfall 9 for Phase-2-through-14 dirs that predate session.json. `compute_usage` returns `(sessions_count, bytes_total)` via single-scandir-per-session (PEP 471 — cached on Windows, 1 syscall on POSIX). `delete` enforces the V12 path-traversal gate at TWO layers: regex `^\d{8}-\d{6}$` rejects non-basename shapes, then `Path.resolve().is_relative_to(recordings_root.resolve())` rejects symlink escape. `read_events` shares the same gate and returns a discriminated-success tuple `(events_list, None)` vs `(None, error_code)` so the UI's transcript-overlay can render the well-defined empty case differently from a security rejection.
- **run_retention_sweep** is the verbatim RESEARCH Pattern 3 body with the Phase 12 ∞-sentinel (`retention_days >= 36500`) short-circuiting BEFORE any filesystem work — verified by a monkey-patched scandir-tracking test that asserts the call count remains zero. Per-entry rmtree failures log + continue (Pitfall 4), with post-delete existence verification surfacing Windows file-in-use as a separately-logged warning.
- **SessionLoop** gains a `recordings_root` kwarg, 3 new IPC handlers (`_on_recordings_list` / `_on_recordings_delete` / `_on_recordings_events`), a shared `_emit_recordings_usage` push helper, and two new lifecycle hooks: `run_boot_sweeps()` (fires the boot-time sweep + initial usage emit BEFORE the snapshot loop starts) and `on_session_close()` (fires the session-close sweep). All sync filesystem work runs in `loop.run_in_executor(None, ...)` so the 30Hz snapshot loop stays responsive.
- **SettingsApplier** gains a `recordings_root` kwarg. `_apply_retention` is extended: AFTER `save_config`, it fires `run_retention_sweep` in executor + emits `ipc.recordings.usage` via `ws_bus`. Best-effort wrap (try/except) ensures the settings-set ack always returns to the UI even if the sweep raises.
- **__main__** cascade path (which doesn't construct a SessionLoop) gets two parity sweep calls: one right after `sweep_crashed_sessions` at boot, one right after `recorder.close()` at shutdown. `load_config` is re-read at both points so persisted retention_days changes apply on the next launch.
- **run_session()** (Phase 12 W2 sidecar) passes `recordings_root = app_data_dir() / "recordings"` and wraps `loop.run()` in try/finally to fire `on_session_close()` on graceful shutdown.

Plan 15-04 (recording browser UI) and Plan 15-05 (SettingsDrawer wiring) now consume real producer-side data. Plan 15-06 (verification) can pin the 3-trigger semantics + the two-layer path-traversal regression against this surface.

## Task Execution

### Task 1: RecordingsIndex module + tests (TDD)

**Commits:** `9bbdcf3` (RED) + `f05e620` (GREEN)

RED phase: 14 failing tests in `tests/recording/test_recordings_index.py` covering all 8 plan Test scenarios plus 6 supporting cases (not_found error, missing root, missing-events.jsonl, regex-match-but-no-dir, module-export smoke, SESSION_DIR_RE accept/reject matrix). Initial run failed with `ModuleNotFoundError: vibemix.runtime.recordings_index`, confirming RED.

GREEN phase implemented `src/vibemix/runtime/recordings_index.py` (~534 LOC including docstrings):

1. **SESSION_DIR_RE** module constant — runtime gate mirror of the schema-layer regex.
2. **Internal helpers** — `_scandir_size_sum`, `_dir_name_to_iso`, `_dir_name_to_unix`, `_wav_duration_seconds` (wraps `wave.open` in try/except per Pitfall 5 — crashed WAVs have wrong RIFF headers → duration=0.0), `_count_jsonl_lines`.
3. **`_synthesize_legacy_summary`** — Pitfall 9 fallback: parses dir name to ISO via strptime, opens voice.wav for duration, counts events.jsonl lines, sums file sizes via scandir, returns `crashed=False` (legacy dirs predate the crashed concept).
4. **`_read_session_summary`** — parses session.json into a RecordingSummary; falls back to legacy synth on `FileNotFoundError`, `json.JSONDecodeError`, or "JSON root is not an object" — bad JSON is defensively treated as "no session.json" so the row still surfaces.
5. **`RecordingsIndex.list`** — scandirs recordings_root, filters by `SESSION_DIR_RE` AND `is_dir(follow_symlinks=False)`, builds RecordingSummary per entry, sorts by dir-name unix timestamp descending. Returns empty tuple (not raise) on missing root.
6. **`RecordingsIndex.compute_usage`** — single scandir of recordings_root + single scandir per session-dir, summing `entry.stat().st_size` with per-file try/except continuation.
7. **`RecordingsIndex.delete`** — two-layer gate: regex first, then `target.resolve().is_relative_to(root.resolve())`. Defensive equality check refuses to delete recordings_root itself. `shutil.rmtree(target, ignore_errors=True)` per RESEARCH Pattern 3 + post-delete existence verification surfaces "locked_or_in_use" for Windows file-in-use.
8. **`RecordingsIndex.read_events`** — same gate; discriminated return `(events_list, None)` vs `(None, error_code)`; malformed JSON lines silently skipped at DEBUG log level (legacy / partial files may have mid-line crashes); non-dict JSON values dropped (schema requires per-event elements to be objects); regex-match-but-no-dir returns `([], None)` well-defined-empty.
9. **`run_retention_sweep`** — verbatim Pattern 3 with the ∞ sentinel and per-entry try/except + post-delete existence verification.

**Verification:**

- `pytest tests/recording/test_recordings_index.py -x -v` — **14/14 passed** in 0.09s.
- `grep -c "is_relative_to" src/vibemix/runtime/recordings_index.py` returns **7** (delete + read_events both call it for the root + the target).
- `grep -c "ignore_errors=True" src/vibemix/runtime/recordings_index.py` returns **4** (RESEARCH Pattern 3 — best-effort rmtree).
- `grep -c "def read_events" src/vibemix/runtime/recordings_index.py` returns **1**.
- Module import smoke: `python -c "from vibemix.runtime.recordings_index import RecordingsIndex, run_retention_sweep, SESSION_DIR_RE; print('ok')"` prints `ok`.

### Task 2: 3-trigger retention sweep integration + IPC handlers + tests (TDD)

**Commits:** `f56f9ca` (RED) + `26ee9f6` (GREEN)

RED phase: 14 failing tests in `tests/recording/test_retention_sweep.py` covering all 7 plan Test scenarios plus 7 supporting cases (sentinel-skip-when-root-missing, retention-sweep-deletes-only-old-sessions, _on_recordings_list shape, _on_recordings_delete + usage-emit, handler-registration coverage, settings-change-emits-usage). Initial run failed with `AttributeError: 'run_retention_sweep' not in session_loop module`, confirming RED.

GREEN phase landed across 3 files:

1. **`src/vibemix/runtime/session_loop.py`**:
   - `__init__` gains `recordings_root: Path | None = None` kwarg, passed through to a default-constructed `SettingsApplier` so the settings-change trigger fires from the same root.
   - `register_handlers` extended with 3 new registrations: `ipc.recordings.list` / `.delete` / `.events`. `recordings.usage` is push-only (no inbound shape).
   - 3 new handlers (`_on_recordings_list` / `_on_recordings_delete` / `_on_recordings_events`) — all offload sync I/O via `loop.run_in_executor(None, ...)`, all wrap in try/except emitting `ipc.error` on failure, all defensive on `recordings_root is None` emitting `recordings_root_not_wired`. `_on_recordings_delete` emits a fresh `ipc.recordings.usage` push AFTER the delete_ack.
   - `run_boot_sweeps()` — boot-time sweep + initial usage emit; called from `run()` AFTER `boot()` but BEFORE the snapshot loop starts.
   - `on_session_close()` — session-close sweep + final usage emit.
   - `_emit_recordings_usage()` shared helper used by all 3 triggers.

2. **`src/vibemix/runtime/settings.py`**:
   - `__init__` gains `recordings_root: Path | None = None` kwarg.
   - `_apply_retention` extended: AFTER `save_config`, fires `run_retention_sweep` via executor and emits `ipc.recordings.usage` via `ws_bus`. Inline imports for `recordings_index` + `RecordingsUsage` keep the settings module import surface clean. Outer try/except ensures the settings-set ack always returns to the UI even if the sweep raises.

3. **`src/vibemix/__main__.py`**:
   - +`run_retention_sweep` import alongside `sweep_crashed_sessions`.
   - +`load_config` import (re-reads retention_days at both boot and close, in case the user changed it mid-session).
   - Cascade `main()` gets two parity sweep calls: one right after `sweep_crashed_sessions` (boot trigger for the cascade path), one right after `recorder.close()` in the finally (close trigger).
   - `run_session()` (Phase 12 W2 sidecar) passes `recordings_root=app_data_dir()/"recordings"` to `SessionLoop` and wraps `loop.run()` in try/finally to fire `on_session_close()` on graceful shutdown.

**Verification:**

- `pytest tests/recording/test_retention_sweep.py -x -v` — **14/14 passed** in 0.15s.
- `pytest tests/recording/ tests/runtime/ tests/ui_bus/ -q` — **207/207 passed** in 3.7s (28 new + 179 baseline, zero regressions in Phase 12 W2 SessionLoop / Phase 15-01 ui_bus / Phase 15-02 session_metadata tests).
- `grep -c "ipc.recordings\." src/vibemix/runtime/session_loop.py` returns **18** (≥4 per plan verification — 3 handler-registration strings + 3 emit-typed strings + 12 docstring references).
- `grep -c "_on_recordings_events" src/vibemix/runtime/session_loop.py` returns **2** (definition + registration).
- `grep -c "run_retention_sweep" src/vibemix/runtime/settings.py` returns **2** (import + call).
- `grep -c "on_session_close" src/vibemix/runtime/session_loop.py` returns **5** (definition + 4 docstring references).

### Task 3: Kaan-rig boot-prune UAT — `human_verification_pending`

**Status:** Auto-marked pending per orchestrator FULLY mode (autonomous orchestrator pre-approves `checkpoint:human-verify` so the executor never blocks).

**Plan asks Kaan to:**

1. Pull the branch on his rig.
2. `ls -la ~/Library/Application\ Support/vibemix/recordings/` and `ls -la recordings/` to capture the pre-state.
3. Run `./run_v4.sh` to confirm POC still writes to CWD `recordings/` (writes one new session dir, no error — must be untouched by the new sweep).
4. Run `python -m vibemix` (production path) — observe stderr for `retention sweep (boot): pruned N session(s)` log.
5. Confirm `~/Library/Application Support/vibemix/recordings/<new>/session.json` exists with the 16 Phase 15-02 fields.
6. Confirm `recordings/` (CWD, POC) still has its v4 dirs intact.
7. Verify idempotency: re-run `python -m vibemix`; the boot sweep should now report "no sessions to prune" (or a much lower count).

**Resume signal:** "approved" / "blocked: <reason>" / "defer: <reason>".

**Files modified by this checkpoint:** none — pure observation step.

**Why this is human-verify, not decision:** Plan 15-03 is the FIRST time `python -m vibemix` will auto-delete any dir on Kaan's rig. The verification is "did the right dirs get pruned, did the POC path stay untouched, did the production path get populated correctly". No alternative implementation choice is being decided.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — `9bbdcf3`** — `test(15-03): add failing tests for RecordingsIndex (list/delete/usage/read_events)` — 1 file, 364 insertions.
2. **Task 1 GREEN — `f05e620`** — `feat(15-03): add RecordingsIndex + run_retention_sweep (scandir-based, two-layer path-traversal gate)` — 1 file, 533 insertions.
3. **Task 2 RED — `f56f9ca`** — `test(15-03): add failing tests for 3-trigger retention sweep + IPC handlers` — 1 file, 442 insertions.
4. **Task 2 GREEN — `26ee9f6`** — `feat(15-03): wire 3-trigger retention sweep + 3 recordings.* IPC handlers` — 3 files, 384 insertions.

## Files Created / Modified

### Created

- `src/vibemix/runtime/recordings_index.py` — RecordingsIndex class + run_retention_sweep + SESSION_DIR_RE + 5 internal helpers (~534 LOC including docstrings + threat-model commentary).
- `tests/recording/test_recordings_index.py` — 14 tests (8 plan-mandated + 6 supporting).
- `tests/recording/test_retention_sweep.py` — 14 tests (7 plan-mandated + 7 supporting handler-shape + sentinel + retention-cutoff coverage).

### Modified

- `src/vibemix/runtime/session_loop.py` — recordings_root kwarg, 3 new IPC handler methods, run_boot_sweeps + on_session_close lifecycle hooks, _emit_recordings_usage shared helper, register_handlers extended to register the 3 new handlers, run_session() wires production recordings_root + close-trigger.
- `src/vibemix/runtime/settings.py` — recordings_root kwarg, _apply_retention extended with sweep + usage emit (best-effort wrap).
- `src/vibemix/__main__.py` — +run_retention_sweep + load_config imports; cascade main() gets boot + close retention-sweep call sites for parity with the sidecar path.
- `.planning/phases/15-recording-session-capture-finalization/deferred-items.md` — appended Plan 15-03 scope-boundary observations (3 pre-existing environmental failures unrelated to this plan).

## Decisions Made

All decisions were locked by the plan + RESEARCH; no new decisions taken during execution. Notable lock-ins applied:

- Two-layer path-traversal gate is REQUIRED by the threat model (T-15-03-01 + T-15-03-08). Both regex + is_relative_to fire; either gate alone would let one class of attack through.
- bytes_total reads from fresh scandir, NOT from session.json's cached counts (which are placeholder 0s at __init__ until close()). This ensures the disk-usage line stays accurate for ongoing sessions where session.json hasn't been finalized yet.
- Sort by dir-name strptime-derived unix timestamp, NOT mtime — RESEARCH pattern; mtime drifts on rsync-style migrations.
- `read_events` returns `([], None)` for regex-match-but-no-dir (well-defined empty success) so the UI can render "no events recorded yet" without needing a separate error code path.
- `_on_recordings_delete` emits the post-delete usage push synchronously after the delete_ack (no polling — drawer's disk-usage line updates instantly).
- Cascade `main()` in `__main__.py` gets its own retention-sweep call sites separate from SessionLoop's. The cascade path (full live runtime) doesn't construct a SessionLoop today, so wiring the sweep into the cascade's own boot + close path is the only way to keep parity between sidecar-only and cascade-full runs. `load_config` re-reads retention_days fresh at both trigger points to handle the user-changed-mid-session case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Worktree was forked from Phase 6 commit; missing Phase 7-15 source.**

- **Found during:** Initial state load (STATE.md / 15-CONTEXT.md / 15-03-PLAN.md all reported `file does not exist`).
- **Root cause:** Same artifact Plan 15-01 + 15-02 encountered — the worktree branch (`worktree-agent-ab8b59b27af48d5c3`) was created from commit `6e6dd9f` (end of Phase 6), but the `.planning/phases/15-*` directories + Phase 7-14 source landed on main afterward. The worktree was 412 files behind.
- **Fix:** `git reset --hard main` — fast-forward equivalent to bring all Phase 15 planning artifacts + Phase 7-14 source into the worktree. No commits to replay; the worktree branch had no divergent work.
- **Verification:** `ls .planning/phases/15-recording-session-capture-finalization/` confirmed 15-CONTEXT.md / 15-RESEARCH.md / 15-03-PLAN.md / 15-02-SUMMARY.md / 15-01-SUMMARY.md all present.

**2. [Rule 3 - Test execution path] venv editable install points at main repo's `src/vibemix/`.**

- **Found during:** Task 1 RED test invocation.
- **Root cause:** The project's `.venv/` (at the main repo root, NOT inside the worktree) has `vibemix` installed editable against `/Users/ozai/projects/dj-set-ai/src/vibemix/` — the main repo path. Without an override, pytest imported the main repo's vibemix and would have missed all Plan 15-03 edits.
- **Fix:** Prefix every test invocation with `PYTHONPATH=$(pwd)/src` so the worktree's src/ shadows the editable install. No code change. Same workaround Plans 15-01 + 15-02 used.

**Total deviations:** 2 auto-fixed (both Rule 3 environmental, same pattern as the previous two plans).

**Impact on plan:** Zero — both fixes were environmental and reproducible from the start state. No source-of-truth code drift, no scope creep.

## Authentication Gates

None — Plan 15-03 is purely filesystem + IPC plumbing. No API keys touched.

## Issues Encountered

### Pre-existing environmental (out of scope per execute-plan.md scope-boundary rule)

Three test failures reproduced from the pre-edit state and were left as-is + logged to `deferred-items.md`:

1. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — `FileNotFoundError: 'cohost_v4.py'` (POC file untracked).
2. `tests/test_phase05_verification.py::test_g5_poc_files_untouched` — same root cause.
3. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — live-device test expects an exact-name "Headphones" output device.

All three are pre-existing artifacts (Plan 15-02 SUMMARY also documented #1 + a #3-style smoke variant) — not caused by Plan 15-03 changes. Verified by stash-and-rerun.

## Threat Surface

No new security-relevant surface beyond what the plan's `<threat_model>` already covered. The two-layer path-traversal gate is the dominant defense:

- **T-15-03-01 / T-15-03-08 — Path traversal on session_dir for delete + events.** Mitigated at TWO layers: regex `SESSION_DIR_RE` rejects anything that doesn't match the basename shape, then `Path.resolve().is_relative_to(self.recordings_root.resolve())` rejects symlink escape (Path.resolve follows symlinks before the comparison). Both gates fire; either alone would let one class of attack through. Tests exercise 7 attack shapes for delete + 4 for read_events: `../../etc/passwd`, `../../../tmp/whatever`, `20260513-210410/../../escape`, `/etc/passwd`, null-byte-injected, dot, double-dot. None mutate the filesystem outside recordings_root — verified by sentinel files planted at `tmp_recordings_dir.parent` that are unchanged at test end.
- **T-15-03-05 — Symlink redirect.** Covered by `Path.resolve()` following symlinks before the is_relative_to check.
- **T-15-03-07 — Windows file-in-use on rmtree.** Covered by `shutil.rmtree(target, ignore_errors=True)` + post-delete existence verification; the locked dir surfaces as `(False, "locked_or_in_use")` rather than a silent partial failure.

## Threat Flags

None new. The 3 IPC handlers and the retention sweep only touch paths under `recordings_root` (already a per-OS app-data dir per Plan 15-02). No new TLS endpoints, no new auth paths, no new file-system writes outside the existing recordings root.

## Known Stubs

None. Every new producer path (`list` / `compute_usage` / `delete` / `read_events`) reads real disk state. `RecordingsListResult.sessions` is computed from real session.json + WAV + JSONL files. `recordings.usage.payload.bytes_total` is computed from scandir-summed file sizes. The plan deliberately implements producers only; the consumers (recording browser row UI in Plan 15-04, drawer disk-usage line wiring in Plan 15-05) land in subsequent plans.

## TDD Gate Compliance

Plan declared `tdd="true"` on Tasks 1 + 2. Gate sequence followed for both:

- **Task 1**: `9bbdcf3` test(15-03) RED → `f05e620` feat(15-03) GREEN. RED confirmed via `ModuleNotFoundError: vibemix.runtime.recordings_index`. GREEN passes 14/14.
- **Task 2**: `f56f9ca` test(15-03) RED → `26ee9f6` feat(15-03) GREEN. RED confirmed via `AttributeError: 'run_retention_sweep' not on session_loop module`. GREEN passes 14/14.

No refactor commits were necessary — both implementations landed clean. POC files (`cohost*.py`) and any cohost_v4.py reference were untouched throughout.

## Kaan-rig Boot-Prune UAT

**Status:** `human_verification_pending` (auto-marked per orchestrator FULLY mode).

**What landed:**

`python -m vibemix` (production path) now calls `run_retention_sweep(recordings_root, retention_days)` at boot AFTER `sweep_crashed_sessions` (Plan 15-02) finalizes any unended session.jsons. The sweep walks `~/Library/Application Support/vibemix/recordings/`, deletes any session dir older than `retention_days` (default 7), and logs `-> retention sweep (boot): pruned N session(s)` to stderr.

`./run_v4.sh` (POC path) is unchanged — it constructs `VoiceRecorder()` with the zero-args POC default (`Path.cwd() / "recordings"`) and has no retention sweep call site. POC dirs are NEVER touched by the new sweep.

**Expected end state on Kaan's rig after the first relaunch:**

- All `~/Library/Application Support/vibemix/recordings/<YYYYMMDD-HHMMSS>/` dirs from > 7 days ago: deleted.
- Any pre-existing dir with `ended_at_iso=null` AND mtime > 30s old: marked `crashed=true` by Plan 15-02's sweep (which already runs before the retention sweep in `main()` ordering).
- `~/Library/Application Support/vibemix/recordings/` is auto-created by `VoiceRecorder.__init__` mkdir(parents=True, mode=0o700) if absent.
- `recordings/` (POC, CWD): untouched.
- Stderr line: `-> retention sweep (boot): pruned N session(s)` (with N=0 logged as "no sessions to prune").

**Anonymized pruned-count estimate:** Unknown until Kaan runs the rig — depends on his Phase 2-14 dev session count and how many are >7 days old.

**Resume signal awaited:** approved / blocked: <reason> / defer: <reason>. On "approved", Plan 15-03 closes and Plan 15-04 can begin.

## Self-Check

Verified all claims against disk before writing this section.

### Files exist

```
FOUND: src/vibemix/runtime/recordings_index.py
FOUND: src/vibemix/runtime/session_loop.py (modified)
FOUND: src/vibemix/runtime/settings.py (modified)
FOUND: src/vibemix/__main__.py (modified)
FOUND: tests/recording/test_recordings_index.py
FOUND: tests/recording/test_retention_sweep.py
FOUND: .planning/phases/15-recording-session-capture-finalization/deferred-items.md (modified)
FOUND: .planning/phases/15-recording-session-capture-finalization/15-03-SUMMARY.md (this file)
```

### Commits exist

```
FOUND: 9bbdcf3 test(15-03): add failing tests for RecordingsIndex (list/delete/usage/read_events)
FOUND: f05e620 feat(15-03): add RecordingsIndex + run_retention_sweep (scandir-based, two-layer path-traversal gate)
FOUND: f56f9ca test(15-03): add failing tests for 3-trigger retention sweep + IPC handlers
FOUND: 26ee9f6 feat(15-03): wire 3-trigger retention sweep + 3 recordings.* IPC handlers
```

### Done criteria

```
PASS: 14/14 tests in test_recordings_index.py pass
PASS: 14/14 tests in test_retention_sweep.py pass
PASS: grep -c "is_relative_to" src/vibemix/runtime/recordings_index.py = 7 (≥1 required, ≥2 plan target)
PASS: grep -c "ignore_errors=True" src/vibemix/runtime/recordings_index.py = 4 (≥1)
PASS: grep -c "def read_events" src/vibemix/runtime/recordings_index.py = 1 (≥1)
PASS: Module import smoke — vibemix.runtime.recordings_index resolves ok
PASS: grep -c "ipc.recordings\." src/vibemix/runtime/session_loop.py = 18 (≥4)
PASS: grep -c "_on_recordings_events" src/vibemix/runtime/session_loop.py = 2 (≥1)
PASS: grep -c "run_retention_sweep" src/vibemix/runtime/settings.py = 2 (≥1)
PASS: grep -c "on_session_close" src/vibemix/runtime/session_loop.py = 5 (≥1)
PASS: full Phase 15 suite (recording + runtime + ui_bus) — 207 passes, zero regressions
PASS: tests/recording/ baseline before this plan (8 tests) — still passes (8/8 in current suite)
PASS: Zero new pip / npm deps
PASS: IPC schema baseline unchanged at 34 (this plan did not touch IPC wire shapes)
```

## Self-Check: PASSED

---
*Phase: 15-recording-session-capture-finalization*
*Plan: 03*
*Completed: 2026-05-13*
