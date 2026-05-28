---
phase: 92-lesson-runtime-ai-highlight-contract
plan: 04
subsystem: backend
tags: [persistence, atomic-write, cli, lesson-runtime, boot-wiring, single-writer]

# Dependency graph
requires:
  - "Plan 92-01 (python-statemachine ^3.1.2 dep + 11 ipc.learn.* envelopes + learn_tutor router path)"
  - "Plan 92-02 (test scaffolding — test_progress_persistence.py + test_ws_broadcast_30hz_under_lesson_load.py stubs)"
  - "Plan 92-03 (LessonRuntime FSM + LearnState + CURRICULUM dispatch + prompts)"
  - "Plan 91-03 (MidiMirror + ws_broadcast midi_mirror kwarg + __main__ wiring precedent)"
provides:
  - "src/vibemix/learn/progress.py — atomic JSON persistence at ~/.cache/vibemix/learn-progress.json (mirror of config_store.save() os.replace pattern)"
  - "LearnProgress dataclass + load_progress / save_progress / reset_progress / progress_path / dots_for_course + SCHEMA_VERSION export"
  - "vibemix learn reset CLI subcommand (synchronous; short-circuits before asyncio.run(main))"
  - "LessonRuntime wired alongside MidiMirror in __main__.main() — live runtime now boots with the FSM running, 1 Hz tick_loop alongside ws_broadcast's 30 Hz"
  - "_LessonRuntimeIpcAdapter — sync→async bridge that lets the FSM's on_enter_<state> callbacks fire-and-forget emit envelopes via the existing IpcRouterBus"
  - "Boot-time was_recovered toast emit when progress JSON is corrupt"
  - "tests/learn/test_progress_persistence.py flipped from RED to 6/6 GREEN (including the subprocess-tagged test_reset_cli)"
  - "tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py flipped from RED to GREEN (Pitfall 6 mitigation pinned — 30 Hz cadence holds under 1 Hz tick_loop)"
affects: [92-05, 92-06, 92-07]

# Tech tracking
tech-stack:
  added:
    - "No new dependencies — atomic-write pattern reuses config_store.save() precedent; CLI dispatch mirrors the existing library / bench subcommand pattern"
  patterns:
    - "Atomic JSON persistence (LESSON-03): tmp.write_text(json.dumps(...)) → os.replace(tmp, target). POSIX rename + Windows ReplaceFileW are atomic. The tmp file lands NEXT TO the target in the same FS (suffix `.json.tmp`) — required for atomic rename (cross-FS rename falls back to copy+unlink which is NOT atomic)"
    - "Corruption-recovery contract: load_progress catches OSError | json.JSONDecodeError → silent unlink + fresh empty + was_corrupt=True flag for the caller. Schema-version mismatch returns fresh empty WITHOUT was_corrupt=True (a deliberate v2-to-v1 migration seam, not corruption)"
    - "Sync→async ipc adapter for FSM emits: the runtime's on_enter_<state> callbacks call self._ipc.emit(envelope) synchronously, but IpcRouterBus.emit is a coroutine. The _LessonRuntimeIpcAdapter inline class schedules emits as fire-and-forget asyncio tasks via _loop.create_task, with strong-ref retention via _background_tasks (mirrors SessionLoop boot-ingest precedent at __main__.py:1516-1518). T-92-04-08 mitigation: when no running loop is reachable (boot-time synchronous emit), the task creation is skipped silently"
    - "CLI subcommand dispatch via cli_entry pre-argparse short-circuit (mirrors the existing `vibemix library` / `vibemix bench` precedent at __main__.py:3161-3166). The `learn reset` path lazy-imports reset_progress, wipes the file, prints 'learn progress reset.', exits 0. The dispatch block sits BEFORE asyncio.run(main) so a CLI invocation never starts the live runtime (T-92-04-05 mitigation: no concurrent-execution path)"
    - "Test-harness duration discriminator for fast_sleep: when both ws_broadcast (30 Hz) and tick_loop (1 Hz) hit the same asyncio.sleep patch (because vibemix.runtime.ws_bus.asyncio IS the global asyncio module), the test's 100-tick budget must distinguish callers by sleep DURATION (_s < 0.1 = mascot path; longer = tick_loop). Without this, tick_loop steals half the budget and the cadence assertion false-fires"

key-files:
  created:
    - "src/vibemix/learn/progress.py (236 lines — LearnProgress dataclass + load_progress / save_progress / reset_progress / progress_path / dots_for_course / SCHEMA_VERSION)"
    - ".planning/phases/92-lesson-runtime-ai-highlight-contract/92-04-SUMMARY.md (this file)"
  modified:
    - "src/vibemix/learn/__init__.py (re-export 7 new names: LearnProgress / load_progress / save_progress / reset_progress / progress_path / SCHEMA_VERSION + dots_for_course is a method, exposed via LearnProgress)"
    - "src/vibemix/__main__.py — 2 ADDITIVE edits: (1) cli_entry dispatch adds `learn reset` subcommand (22 lines); (2) main() body adds the LessonRuntime wiring block (99 lines) plus 1 line creating the lesson_tick_task. No existing line is modified."
    - "tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py (Rule 1 test-bug fix: fast_sleep duration discriminator — only short sleeps count toward the 100-tick budget; +12 lines comment + 1 conditional)"

key-decisions:
  - "Added LearnProgress.dots_for_course as a Rule 2 missing-functionality. The LessonRuntime's on_enter_loaded callback calls progress_store.dots_for_course(course_id); without this method the call would AttributeError and the defensive try/except would spam stderr on every lesson load. The implementation derives dots from self.lessons (no per-course key today — v9.0 ships one course; future plans can extend the filter)."
  - "_LessonRuntimeIpcAdapter is an inline class INSIDE __main__.main(), not a separate module. The adapter is a 30-line pure-glue object that closes over `_background_tasks` (the strong-ref set already in __main__.main scope); extracting it to vibemix.learn would require either passing _background_tasks as a constructor arg or shipping a separate set, both of which add ceremony without separation-of-concerns gain. Decision: keep it local; if a second consumer needs it later, extract then."
  - "Test fix in tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py is a Rule 1 deviation. The test as shipped by Plan 92-02 (eb95b43e etc.) had a structural flaw — patching the global asyncio.sleep meant both the 30 Hz mascot path AND the 1 Hz tick_loop hit the same wrapper, splitting the 100-tick budget. The fix adds a sleep-duration discriminator (_s < 0.1) so only mascot-rate sleeps count toward the budget. This preserves the original test intent (assert mascot_emits ≈ 100) while accurately measuring cadence under shared-sleep mocking."
  - "Plan's <persistence_blueprint> Step 1 specified the runtime calls `self._progress.dots_for_course(course_id)`, but the plan's <action> Step 1 listed only 5 public functions (load_progress / save_progress / reset_progress / progress_path / LearnProgress). Adding dots_for_course is the most-natural method on the LearnProgress dataclass and matches the runtime's call signature without inventing a wrapper class."
  - "Insertion point for the LessonRuntime block is AFTER the SessionLoop register_handlers block (where ipc_router becomes available — line 1522) and BEFORE the asyncio.create_task(ws_broadcast(...)) call (line 1622). This is later than the plan suggested (`AFTER the MidiMirror block`) — but MidiMirror lives at line 859, before ipc_router exists. Landing the FSM near ipc_router is necessary because LessonRuntime's constructor takes ipc_router. The semantics still hold: LessonRuntime is wired before any asyncio task is created, so its first tick fires alongside ws_broadcast's first tick."

patterns-established:
  - "Atomic write for runtime-mutable JSON: tmp + os.replace; same-FS tmp suffix for cross-FS-safe atomicity"
  - "FSM-side defensive emit with sync→async adapter when async ipc bus is wired to sync state-machine callbacks"
  - "CLI subcommand short-circuit BEFORE asyncio.run(main): mirror of library/bench pattern, T-92-04-05 mitigates concurrent-execution paths"
  - "Fast-sleep test harness must distinguish callers by sleep duration when the same asyncio.sleep wrapper sees multiple loop frequencies"

requirements-completed: [LESSON-03]

# Metrics
duration: 10min
completed: 2026-05-28
---

# Phase 92 Plan 04: Lesson Runtime Wiring + Atomic Progress Persistence Summary

**Atomic JSON persistence (mirror of `config_store.save()` os.replace pattern) + corruption-recovery + reset CLI subcommand + LessonRuntime wired into `__main__.main()` alongside MidiMirror — the seam that takes Plan 92-03's standalone FSM into a real running service. The live app now boots with both `-> midi_mirror wired` (P91) and `-> lesson_runtime wired` (P92) in stderr, and the 1 Hz tick_loop runs alongside ws_broadcast's 30 Hz without stutter.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-28T01:40:17Z
- **Completed:** 2026-05-28T01:50:31Z
- **Tasks:** 3 task commits + 1 metadata commit
- **Files created:** 1 (progress.py) + 1 (this SUMMARY)
- **Files modified:** 3 (__init__.py, __main__.py, test_ws_broadcast_30hz_under_lesson_load.py)
- **Lines:** ~270 net add across all task commits

## Accomplishments

- **Atomic JSON persistence lands.** `~/.cache/vibemix/learn-progress.json` writes are atomic via `os.replace(tmp, target)`. A crash mid-write never leaves a half-truncated file; the next `load_progress` reads the previous-committed snapshot. T-92-04-01 binding.
- **Corruption recovery contract lands.** `load_progress()` on garbage bytes → silent unlink + fresh empty + `was_corrupt=True` flag. The caller (`__main__.main`) emits a one-line `LearnProgressState { was_recovered: True }` toast envelope to the webview. T-92-04-02 binding.
- **Schema-version migration seam.** A future `schema_version: 2` file returns fresh empty (NOT was_recovered — schema mismatch is deliberate, not corruption). v9.0 ships v1; v10 plans land an explicit `_migrate_v2_to_v1` upgrader. T-92-04-03 binding.
- **`vibemix learn reset` CLI subcommand lands.** Idempotent (running on an absent file is a no-op). Short-circuits BEFORE `asyncio.run(main())` so a CLI invocation never starts the live runtime. T-92-04-05 binding.
- **`LessonRuntime` wired into `__main__.main()` alongside `MidiMirror`.** Boot sequence: `load_progress()` → `LessonRuntime(...)` → emit boot toast on `was_recovered` → `asyncio.create_task(lesson_runtime.tick_loop(stop_event))`. Live stderr shows BOTH `-> midi_mirror wired` (P91) AND `-> lesson_runtime wired` (P92).
- **Sync→async ipc adapter (`_LessonRuntimeIpcAdapter`) lands.** The runtime's `on_enter_<state>` callbacks call `self._ipc.emit(envelope_dict)` synchronously, but `IpcRouterBus.emit` is async. The adapter schedules each emit as a fire-and-forget asyncio task via `_loop.create_task`, with strong-ref retention via `_background_tasks`. T-92-04-08 binding (no-loop fallback drops emits silently).
- **Cadence test flipped from RED to GREEN.** `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` was structurally flawed (patched global asyncio.sleep, both loops shared the 100-tick budget). Fixed via sleep-duration discriminator; mascot cadence now holds at ~100 emits ±5% while `tick_loop` runs in parallel.
- **6/6 tests in `test_progress_persistence.py` now PASS** (including the subprocess-tagged `test_reset_cli` under `-m cli`).
- **Plan 92-02's `test_ws_broadcast_30hz_under_lesson_load.py` flipped from skip → PASS** — the Pitfall 6 contract is bound.

## Task Commits

Each task was committed atomically by named paths only (concurrent-session discipline — never `git add -A`):

1. **Task 1: Land atomic `progress.py` with corruption recovery + reset** — `2971d4dc` (feat) — files: `src/vibemix/learn/progress.py` (NEW, 203 lines), `src/vibemix/learn/__init__.py` (+7 re-exports). 5/6 tests in `test_progress_persistence.py` PASS (CLI test still RED awaiting Task 2).
2. **Task 2: Wire `vibemix learn reset` CLI subcommand** — `f3a687f9` (feat) — files: `src/vibemix/__main__.py` (+22 lines, additive). All 6/6 tests in `test_progress_persistence.py` PASS.
3. **Task 3: Wire `LessonRuntime` into `__main__.main()` alongside `MidiMirror`** — `419997cb` (feat) — files: `src/vibemix/__main__.py` (+99 lines wiring + 1 line for `lesson_tick_task`), `src/vibemix/learn/progress.py` (+33 lines for `dots_for_course`), `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` (+12 lines test-harness fix). Cadence test PASS; live-app boot smoke clean.

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS):** see final commit below.

## Files Created / Modified

### Created

- `src/vibemix/learn/progress.py` — atomic JSON persistence module. 5 public functions (`load_progress` / `save_progress` / `reset_progress` / `progress_path` / `dots_for_course` is on the LearnProgress class) + `LearnProgress` dataclass + `SCHEMA_VERSION` constant. Module docstring binds threat-register entries T-92-04-01/02/03 + cross-references the `runtime/config_store.py:266-278` atomic-write precedent.
- `.planning/phases/92-lesson-runtime-ai-highlight-contract/92-04-SUMMARY.md` — this file.

### Modified

- `src/vibemix/learn/__init__.py` — Re-exports 7 new names from `progress.py`: `LearnProgress`, `load_progress`, `save_progress`, `reset_progress`, `progress_path`, `SCHEMA_VERSION`. Extended `__all__` alphabetically. Docstring updated with the new Phase 92 surface.
- `src/vibemix/__main__.py` — **2 ADDITIVE edits, zero existing-line modifications:**
  - `cli_entry` (line 3166-3187): added `learn reset` dispatch BEFORE `_parse_args`. Pattern mirrors the existing `library` / `bench` dispatch at line 3161-3166 (lazy-import → short-circuit → `sys.exit(0)`). Unknown subcommand surfaces `vibemix learn: unknown subcommand` + exit 2.
  - `main()` (line 1524-1620): added the LessonRuntime wiring block between the SessionLoop `except` block and the `--- Asyncio tasks (6) ---` comment. `_LessonRuntimeIpcAdapter` class is inline (closes over `_background_tasks`). `LessonRuntime` instantiation + boot-toast emit happen synchronously; `lesson_tick_task = asyncio.create_task(lesson_runtime.tick_loop(stop_event))` runs alongside `ws_task` in the asyncio tasks block.
- `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` — Rule 1 test-bug fix. `fast_sleep` now distinguishes mascot-rate sleeps (`_s < 0.1`) from `tick_loop`'s 1 Hz sleep (`_s == 1.0`) — only short sleeps count toward the 100-tick budget. Long sleeps still yield cooperatively. Test now asserts mascot_emits ≈ 100 ±5 cleanly.

## Diff Hunks (the load-bearing `__main__.py` additions, for next-session conflict resolution)

The exact additive blocks in `src/vibemix/__main__.py` (so the next session reviewing concurrent-edit collisions sees what landed):

```python
# 1. CLI subcommand dispatch (line 3167-3187 — between `bench` and `_parse_args`):

    # Phase 92 (LESSON-03) — `vibemix learn <sub>` dispatch. v9.0 ships ONE
    # subcommand: `learn reset` (wipes ~/.cache/vibemix/learn-progress.json).
    # Dispatched the same way as `library` / `bench` — short-circuits BEFORE
    # `asyncio.run(main())` so the live runtime never starts when the CLI
    # subcommand is invoked (T-92-04-05 mitigation: no path where reset runs
    # concurrent with a live session). Idempotent — reset_progress is a no-op
    # when the file is already absent.
    if raw_argv and raw_argv[0] == "learn":
        if len(raw_argv) >= 2 and raw_argv[1] == "reset":
            from vibemix.learn.progress import reset_progress

            reset_progress()
            print("learn progress reset.", file=sys.stdout, flush=True)
            sys.exit(0)
        # Unknown `learn` subcommand — surface usage + exit 2 (argparse-style).
        print(
            f"vibemix learn: unknown subcommand {raw_argv[1:]!r}; "
            "available: reset",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)
```

```python
# 2. LessonRuntime wiring block (line 1524-1620 — between SessionLoop except
#    block and `--- Asyncio tasks (6) ---` comment):

    # Phase 92 (LESSON-01/03/04) — wire LessonRuntime alongside MidiMirror.
    # ... (See SUMMARY's "Accomplishments" for the contract.)
    from vibemix.learn.progress import load_progress as _load_progress
    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState
    from vibemix.ui_bus.learn_messages import LearnProgressState

    class _LessonRuntimeIpcAdapter:
        """Sync→async bridge for LessonRuntime emits..."""
        def __init__(self, ipc_router_inst):
            self._router = ipc_router_inst
        def emit(self, msg):
            if self._router is None:
                return
            try:
                _loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            try:
                _t = _loop.create_task(self._router.emit(msg))
                _background_tasks.add(_t)
                _t.add_done_callback(_background_tasks.discard)
            except Exception as _emit_exc:
                print(f"[learn boot] ipc emit failed: {_emit_exc!r}", file=sys.stderr)

    _learn_state = LearnState()
    _learn_progress, _learn_was_recovered = _load_progress()
    _lesson_ipc_adapter = _LessonRuntimeIpcAdapter(ipc_router)
    lesson_runtime = LessonRuntime(
        learn_state=_learn_state,
        midi_mirror=midi_mirror,
        controller_state=midi_macos.controller_state,
        ipc_router=_lesson_ipc_adapter,
        progress_store=_learn_progress,
    )
    print("-> lesson_runtime wired", file=sys.stderr)

    if _learn_was_recovered:
        try:
            _lesson_ipc_adapter.emit(
                LearnProgressState.make(
                    action="snapshot",
                    was_recovered=True,
                    progress=_learn_progress.snapshot(),
                ).to_dict()
            )
        except Exception as _toast_exc:
            print(f"[learn boot] progress recovery toast emit failed: {_toast_exc!r}", file=sys.stderr)
```

```python
# 3. lesson_tick_task creation (line 1638 — right after ws_task creation):

    # Phase 92 (LESSON-01) — drive LessonRuntime's 1 Hz tick_loop
    # alongside ws_broadcast's 30 Hz tick.
    lesson_tick_task = asyncio.create_task(lesson_runtime.tick_loop(stop_event))
```

## Live-App Boot Verification

`PYTHONPATH=src .venv/bin/python -m vibemix` boots clean (subprocess-driven 5s smoke):

```
-> midi_mirror wired
[... 16 lines of audio + LLM + cache + recall + grounding banners ...]
-> session IPC handlers wired onto mascot bus (11 types: settings/profile/recordings)
-> lesson_runtime wired
-> listening to BlackHole 2ch @ 48000Hz -> audio_buf + clean_audio_buf
[live] music=0.000 | voice=0.000 | audible=0 deck=none phase=silent
-> stopping...
-> bye
```

Both breadcrumbs appear. No Python traceback in the first 5 s. Clean SIGTERM shutdown.

## Decisions Made

- **Added `LearnProgress.dots_for_course` as a Rule 2 missing-functionality.** The runtime calls `progress_store.dots_for_course(course_id)` on every lesson load. Without this method the defensive try/except inside `on_enter_loaded` would log `[learn.runtime] lesson_loaded emit failed: AttributeError` every time. The implementation walks `self.lessons` and reports anything marked completed.
- **`_LessonRuntimeIpcAdapter` lives INSIDE `main()` as an inline class.** It closes over `_background_tasks` (the strong-ref set already in `main()` scope, used by the SessionLoop boot-ingest task). Extracting it to a separate module would require either passing `_background_tasks` as a constructor arg or shipping a separate set. Local inline is the least-friction choice; can be extracted later if a second consumer arises.
- **Test fix `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` is a Rule 1 deviation.** The test as shipped by Plan 92-02 patched `vibemix.runtime.ws_bus.asyncio.sleep` globally (asyncio.sleep is module-shared) — both ws_broadcast's 30 Hz sleep AND tick_loop's 1 Hz sleep hit the same wrapper. The original 100-tick counter split between both loops, so mascot_emits dropped to ~47 even when the runtime was correctly cooperative. Fix: count only short sleeps (`_s < 0.1`) toward the 100-tick budget; long tick_loop sleeps still yield. Test now asserts mascot cadence accurately under shared-sleep mocking.
- **Insertion point for LessonRuntime block is later than the plan's "after MidiMirror" suggestion.** MidiMirror is at line 859 (before `ipc_router` exists); LessonRuntime needs `ipc_router` as a constructor arg, so the FSM block lands at line 1524 (right after the SessionLoop register_handlers block). The semantic invariant still holds — LessonRuntime is wired before any asyncio task is created.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] Added `LearnProgress.dots_for_course` method**
- **Found during:** Task 3 (LessonRuntime constructor accepts `progress_store=progress`; the FSM's `on_enter_loaded` calls `progress_store.dots_for_course(course_id)`).
- **Issue:** The plan's `<persistence_blueprint>` specified 5 public functions on `progress.py` — `load_progress / save_progress / reset_progress / progress_path / LearnProgress` — but the runtime's protocol contract (runtime.py:346) calls `dots_for_course` on the progress_store. Without this method, every lesson load would log `[learn.runtime] lesson_loaded emit failed: AttributeError(...)`.
- **Fix:** Added `LearnProgress.dots_for_course(course_id) -> tuple[dict, ...]` that walks `self.lessons` and returns `({"lesson_id": ..., "status": "completed"}, ...)` tuples. The `course_id` arg is currently ignored (v9.0 ships one course); future plans (P94+) can extend the filter for multi-course progress lookup.
- **Files modified:** `src/vibemix/learn/progress.py`
- **Verification:** `tests/learn/test_progress_persistence.py` 6/6 PASS; live-app boot shows no `[learn.runtime] lesson_loaded emit failed` lines in stderr.
- **Committed in:** `419997cb` (Task 3 commit)

**2. [Rule 1 — Bug in test scaffold] Fast-sleep duration discriminator in `test_ws_broadcast_30hz_under_lesson_load.py`**
- **Found during:** Task 3 verify gate (running the test).
- **Issue:** The test as shipped by Plan 92-02 patched `vibemix.runtime.ws_bus.asyncio.sleep` with a counter-incrementing wrapper, expecting ws_broadcast to fire 100 mascot emits before `stop_event.set` was tripped. But `vibemix.runtime.ws_bus.asyncio` IS the asyncio module (verified: `wb.asyncio is asyncio` returns True); patching the `sleep` attribute affects ALL callers including `vibemix.learn.runtime.tick_loop` which awaits `asyncio.sleep(1.0)`. Result: both loops shared the 100-tick budget, tick_loop stole ~53, mascot got ~47 → assertion failed with the very error message the test was designed to surface ("LessonRuntime.tick_loop is blocking the asyncio loop").
- **Fix:** Added a sleep-duration discriminator in `fast_sleep`: only sleeps shorter than 0.1 s (the 30 Hz mascot path at 1/30 ≈ 0.033 s) count toward the 100-tick budget. The 1 Hz `tick_loop` sleep (1.0 s) still yields cooperatively via `_REAL_SLEEP(0)` but doesn't consume budget. Test now PASSES with mascot_emits = 100 ±5.
- **Files modified:** `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py`
- **Verification:** `pytest -v tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` PASSES.
- **Committed in:** `419997cb` (Task 3 commit)

**3. [Positive deviation] No `git add -A` ever used; concurrent-session discipline upheld**
- **Concurrent context:** Multiple sessions touching shared files (CLAUDE.md, src/vibemix/agent/_streaming_pipe.py, src/vibemix/prompts/matrix.py, src/vibemix/prompts/negative_dict.py, src/vibemix/intel/claim_validator.py, tauri/ui/src/debrief/, tauri/ui/src/library/, tauri/ui/src/session/, tauri/ui/src/settings/, plus various tests). Every `git add` in this plan staged ONLY named paths from `files_modified`; verified with `git status --short <paths>` and `git diff --cached --name-only` before each commit.
- **Files in concurrent-session edit state but NOT touched by this plan:** All preserved exactly as-found.

---

**Total deviations:** 3 (2 Rule fixes, 1 positive). All fixes close functional/test gaps the plan's skeleton did not anticipate. No deviation changed plan scope or invariants. All 3 task commits stayed named-path strict.

## Threat Register Bindings

All threat-register entries from the plan's `<threat_model>` are bound:

- **T-92-04-01 (DoS: half-truncated mid-write):** Mitigated by `os.replace(tmp, target)` — POSIX atomic rename; Windows ReplaceFileW atomic. `tmp.write_text` is the entire write; the rename is the atomicity guarantee. Pinned by `test_atomic_write` (verifies no `.json.tmp` leftover after `save_progress`).
- **T-92-04-02 (DoS: corrupt file wedges runtime):** Mitigated by `load_progress` catching `OSError | json.JSONDecodeError` → silent `unlink` + fresh empty + `was_corrupt=True` flag. Pinned by `test_corrupt_file_recovers_clean`.
- **T-92-04-03 (Tampering: schema version drift):** Mitigated by `LearnProgress.from_dict` returning fresh `cls()` when `schema_version != SCHEMA_VERSION`. Future migrations land in an explicit `_migrate_v2_to_v1` upgrader (not in v9.0). Pinned by `test_schema_version_mismatch_returns_fresh_empty`.
- **T-92-04-04 (DoS: tick_loop stutters 30 Hz):** Mitigated by tick_loop being 1 Hz with sync emit-only callbacks (no file I/O, no LLM calls, no blocking work). Pinned by `test_ws_broadcast_30hz_under_lesson_load`.
- **T-92-04-05 (Tampering: CLI fires during live session):** Mitigated by the CLI dispatch block short-circuiting with `sys.exit(0)` BEFORE `asyncio.run(main())`. The `learn reset` subcommand can never run concurrent with a live session by construction.
- **T-92-04-06 (Information Disclosure: progress file leaks PII):** Accepted. The file stores only lesson-completion timestamps (ISO-8601) — not personally identifying. Local-machine-only under `~/.cache/vibemix/`.
- **T-92-04-07 (Tampering: concurrent-session edits to `__main__.py`):** Mitigated by re-reading `__main__.py` immediately before each edit, staging only named paths, and verifying content matched the initial read before commit. No collisions detected during this plan.
- **T-92-04-08 (DoS: boot-time `was_recovered` emit blocks):** Mitigated by the `_LessonRuntimeIpcAdapter`'s try/except on `asyncio.get_running_loop()` — when no loop is running, the emit is silently dropped; the webview re-queries via `progress_state` once it connects.
- **T-92-04-SC (Tampering: package supply chain):** Accepted. This plan adds ZERO new packages.

## Issues Encountered

- **None blocking.** The `current_state` deprecation warning (99 instances during the cadence test) is a pre-existing python-statemachine 3.1.2 deprecation logged by Plan 92-03's runtime; unchanged by this plan. Future cleanup in P94+ when the upgrade is forced.

## Self-Check: PASSED

- `src/vibemix/learn/progress.py` exists at expected path: ✓
- `from vibemix.learn import LearnProgress, load_progress, save_progress, reset_progress, progress_path` works: ✓
- `from vibemix.learn.progress import SCHEMA_VERSION` returns 1: ✓
- `save_progress(LearnProgress())` writes via tmp+replace; no `.json.tmp` residue: ✓
- `load_progress()` returns `(LearnProgress(), False)` on missing file: ✓
- `load_progress()` returns `(fresh_empty, True)` on garbage bytes + unlinks the file: ✓
- `load_progress()` returns `(fresh_empty, False)` on schema_version mismatch (NOT was_corrupt — schema migration seam): ✓
- `reset_progress()` is idempotent (no error on absent file): ✓
- `uv run python -m vibemix learn reset` exits 0 with `learn progress reset.` stdout, idempotent across multiple invocations: ✓
- `src/vibemix/__main__.py::main()` instantiates `LessonRuntime` after the SessionLoop register_handlers block: ✓
- Boot stderr prints BOTH `-> midi_mirror wired` (P91) AND `-> lesson_runtime wired` (P92): ✓
- `asyncio.create_task(lesson_runtime.tick_loop(stop_event))` runs alongside `ws_broadcast`: ✓
- Live app `uv run python -m vibemix` boots without Python traceback in the first 5 s; clean SIGTERM shutdown: ✓
- `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` PASSED (flipped from RED to GREEN): ✓
- `tests/learn/test_progress_persistence.py` 6/6 PASS (including `test_reset_cli` under `-m cli`): ✓
- AST gates stay green: `test_runtime_invariants`, `test_scripts_are_fixtures`, `test_no_new_ws_port`, `test_no_pioneer_brand_marks` all PASS: ✓
- Pre-existing P91 tests stay green: `test_ws_broadcast_30hz_under_learn_load`, `test_midi_mirror_unit`, `test_main_smoke` — all PASS: ✓
- Broader regression scope: 277/277 PASS in `tests/learn/` + `tests/ipc/test_learn_envelope_parity*` + `tests/llm/test_model_router*` + `tests/runtime/test_ws_broadcast_30hz_under_*` + `tests/test_main_smoke.py` + `tests/ui_bus/`: ✓
- Three task commits exist + verified:
  - `2971d4dc` feat(92-04): land atomic progress.py with corruption recovery + reset ✓
  - `f3a687f9` feat(92-04): wire 'vibemix learn reset' CLI subcommand ✓
  - `419997cb` feat(92-04): wire LessonRuntime into __main__.main() alongside MidiMirror ✓
- No git deletions in any task commit: ✓ (each commit only adds new files / new lines; no shared-file lines removed + no file removals)
- No `git add -A` used; concurrent-session discipline upheld: ✓ (every commit staged specific named paths; CLAUDE.md, src/vibemix/agent/_streaming_pipe.py, src/vibemix/prompts/matrix.py, etc. concurrent-session edits NEVER staged into this plan's commits — verified via `git diff --cached --name-only` before each commit)

## Threat Flags

No new security-relevant surface flagged. The atomic-write path adds no new file-system surface (location pre-exists for `library-clap.db` / `library.pkl` neighbours); the CLI subcommand is a `sys.exit` short-circuit (no new attack surface); the LessonRuntime wiring re-uses the existing `IpcRouterBus` on the single ws:8765 socket (Invariant #4 preserved).

## Concurrent-Session Reconciliation

No concurrent-session collisions occurred during execution. Each task commit was named-path strict and `git status --short` verified before staging. The shared file `src/vibemix/__main__.py` had no intervening edits between this plan's reads and writes (`git log --oneline -2 src/vibemix/__main__.py` showed the last commit was P91-03's `e572a8a7` from before this plan started).

## Next Phase Readiness

- **Plan 92-05 (Learn webview wiring of the 11 envelopes)** unblocked — the live runtime now emits `lesson_loaded`, `highlight`, `tutor_speak`, `advance`, `complete_lesson`, `progress_state` envelopes via the `ipc_router` instance. P92-05 wires the webview-side handlers to consume them.
- **Plan 92-06 (LearnGroup settings drawer row)** unblocked — `vibemix learn reset` works end-to-end as the CLI surface; the drawer button can emit `ipc.learn.progress_state { action: "reset" }` and SessionLoop's handler can call `reset_progress()` directly.
- **Plan 92-07 (integration test + end-to-end demo)** unblocked — the FSM is wired, tick_loop runs, the live app boots clean. The hello-world 1-step lesson (`L0.00-press-play`) can be triggered via `ipc.learn.start_lesson`.
- **Concurrent sessions** continue safely — the 4 files this plan touched (progress.py NEW, __init__.py, __main__.py, test_ws_broadcast_30hz_under_lesson_load.py) are now stable; the 5+ concurrent-session sessions on `live-tuning-or-brain` saw NO file collisions during execution.
- **No KAAN-ACTION items added** by this plan.

---
*Phase: 92-lesson-runtime-ai-highlight-contract*
*Plan: 04*
*Completed: 2026-05-28*
