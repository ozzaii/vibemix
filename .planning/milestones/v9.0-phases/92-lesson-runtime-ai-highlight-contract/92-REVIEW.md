---
phase: 92-lesson-runtime-ai-highlight-contract
reviewed: 2026-05-28T05:30:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - src/vibemix/learn/state.py
  - src/vibemix/learn/runtime.py
  - src/vibemix/learn/curriculum.py
  - src/vibemix/learn/prompts.py
  - src/vibemix/learn/progress.py
  - src/vibemix/learn/__init__.py
  - src/vibemix/learn/transcripts/hello_world/01_press_play.json
  - src/vibemix/ui_bus/learn_messages.py
  - src/vibemix/ui_bus/__init__.py
  - src/vibemix/__main__.py
  - src/vibemix/llm/_router_config.py
  - scripts/check_ipc_schema.py
  - tauri/ui/src/learn/lesson/hud.ts
  - tauri/ui/src/learn/lesson/tutor-dock.ts
  - tauri/ui/src/learn/lesson/skip-button.ts
  - tauri/ui/src/learn/components/controller-stage.ts
  - tauri/ui/src/learn/learn-window.ts
  - tauri/ui/src/learn/styles/learn.css
  - tauri/ui/src/settings/components/learn-group.ts
  - tauri/ui/src/settings/SettingsDrawer.ts
  - tauri/ui/src/ipc/messages.schema.json
  - tauri/ui/src/ipc/messages.ts
  - tauri/ui/src/ipc/validator.generated.mjs
findings:
  critical: 4
  warning: 7
  info: 5
  total: 16
fix_summary:
  fixed_at: 2026-05-28T05:52:00Z
  fix_branch: gsd-reviewfix/92-82408
  critical_fixed: 4   # CR-01, CR-02, CR-03, CR-04
  warning_fixed: 6    # WR-01, WR-02, WR-03, WR-04, WR-06, WR-07
  warning_documented: 1  # WR-05 (convention, not bug — comment added)
  info_deferred: 5    # IN-01..IN-05 (per fix scope: critical_warning)
  pytest_learn_runtime: 319  # was 305 baseline; +14 new regression tests
  vitest: 1030  # was 1029 baseline; +1 new test (CR-04 toast)
status: fixed
---

# Phase 92: Code Review Report

**Reviewed:** 2026-05-28T05:30:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Phase 92 lands the lesson runtime FSM, AI highlight contract, 11 new IPC envelopes,
and the lesson UI components (HUD / tutor dock / skip button / settings reset row).
The work is internally well-tested (1029 vitest + 327+ pytest, AST gates green,
0.547ms P95 highlight paint) and the structural invariants hold — sole-writer of
LearnState, no second ws listener, no Pioneer brand marks, no hardcoded model
literals.

However, this adversarial review surfaced 4 BLOCKERs in the inbound IPC dispatch
chain. The LessonRuntime FSM is **structurally complete but operationally
disconnected**: no sidecar handler is registered for ANY of the 4 shell→sidecar
learn envelopes (`start_lesson`, `start_course`, `ack`, `progress_state`). The
frontend can emit them, but the sidecar will silently drop every one. The "Reset
Learn Progress" settings button is visible and clickable, but the reset never
fires. The same gap applies to lesson start, MIDI ack routing, and user-skip
relay. In addition, `mark_completed()` updates in-memory only — completion is
never persisted to disk via `save_progress()`. These gaps are independent of the
P92 test surface because all tests instantiate `LessonRuntime` directly via
`runtime.send(...)`; no test verifies that an inbound ws frame actually reaches
the FSM in the live `__main__` boot path.

The remaining 7 WARNINGs cover task-cleanup gaps (lesson_tick_task leaks on
shutdown), a misplaced toast surface (reset_ack toast lives in the Learn window
but the reset button lives in the Session settings drawer), unused
`course_id` parameter that will produce wrong cross-course progress in P94+, and
defensive-emit failures that proceed past invalid state.

## Critical Issues

### CR-01: LessonRuntime FSM has zero inbound IPC handlers — the FSM is wired but no event ever reaches it

**File:** `src/vibemix/__main__.py:1594-1601`, `src/vibemix/runtime/session_loop.py:251-284`
**Issue:** The LessonRuntime FSM is instantiated in `__main__.py` and its
`tick_loop` is scheduled. However, NO `ipc.learn.*` shell→sidecar envelope has
a registered handler in `SessionLoop.register_handlers()` (or anywhere else in
the live boot path). Specifically:

- `ipc.learn.start_lesson` — would drive `lesson_runtime.send("load", ...)` → `send("begin")`
- `ipc.learn.start_course` — same dispatch
- `ipc.learn.ack` — would drive `lesson_runtime.send("ack_action", midi=...)`
- `ipc.learn.complete_lesson` (shell→sidecar user_skip path) — would drive `lesson_runtime.send("skip")` or finalize
- `ipc.learn.progress_state { action: "reset" }` — would drive `reset_progress()` + emit `reset_ack`

`grep -rn "lesson_runtime.send\|register_handler.*learn"` over `src/` returns
zero call sites outside the test suite. The frontend can fire any of these
envelopes; `IpcRouterBus.dispatch()` (`runtime/ws_bus.py:346-359`) returns False
for unrecognised types and logs nothing. The lesson can never start, never
advance from MIDI, never skip, and the user's reset never fires.

This is the load-bearing operational gap. P92 tests pass because they all
exercise `LessonRuntime` directly with `runtime.send(...)` — never via the IPC
boundary.

**Fix:** Register the 4 inbound handlers in `__main__.py` after the
`SessionLoop.register_handlers()` block. Minimum viable wiring:

```python
# After lesson_runtime is built (line 1601), before ws_task is scheduled:
if ipc_router is not None:
    async def _on_learn_start_lesson(msg: dict) -> None:
        p = msg.get("payload", {})
        lesson_id = p.get("lesson_id")
        # Derive course_id from lesson_id prefix
        course_id = "course_0" if lesson_id and lesson_id.startswith("L0.") else None
        controller_id = midi_mirror.current_profile().id if midi_mirror.current_profile() else ""
        lesson_runtime.send("load", lesson_id=lesson_id, course_id=course_id, controller_id=controller_id)
        lesson_runtime.send("begin")

    async def _on_learn_ack(msg: dict) -> None:
        p = msg.get("payload", {})
        # Re-shape ack payload into the midi dict that action_matches expects.
        midi = {
            "type": "cc" if "value" in p else "button",
            "control": p.get("control_id", "").split(":")[0],
            "deck": p.get("control_id", "").split(":")[-1] if ":" in p.get("control_id", "") else "",
            "direction": p.get("direction", ""),
            "value": p.get("value", 0),
            "prev_value": 0,  # need a delta tracker for CC
        }
        lesson_runtime.send("ack_action", midi=midi)

    async def _on_learn_complete_lesson(msg: dict) -> None:
        if msg.get("payload", {}).get("reason") == "user_skip":
            lesson_runtime.send("skip")

    async def _on_learn_progress_state(msg: dict) -> None:
        from vibemix.learn.progress import reset_progress
        if msg.get("payload", {}).get("action") == "reset":
            reset_progress()
            await ipc_router.emit(
                LearnProgressState.make(action="reset_ack").to_dict()
            )

    ipc_router.register_handler("ipc.learn.start_lesson", _on_learn_start_lesson)
    ipc_router.register_handler("ipc.learn.start_course", _on_learn_start_course)
    ipc_router.register_handler("ipc.learn.ack", _on_learn_ack)
    ipc_router.register_handler("ipc.learn.complete_lesson", _on_learn_complete_lesson)
    ipc_router.register_handler("ipc.learn.progress_state", _on_learn_progress_state)
```

Also add a test under `tests/runtime/` that instantiates `IpcRouterBus`,
dispatches a synthetic `ipc.learn.start_lesson` frame, and asserts the FSM
moved past `idle`. The current P92 test suite never verifies this boundary.

---

### CR-02: `LessonRuntime.on_enter_completed` calls `mark_completed()` but never persists — progress dies with the process

**File:** `src/vibemix/learn/runtime.py:458-462`, `src/vibemix/learn/progress.py:87-111`
**Issue:** `LearnProgress.mark_completed(course_id, lesson_id, strikes_used=0)`
only mutates the in-memory `self.lessons` dict. It does NOT call
`save_progress(self)` or write to disk. The `on_enter_completed` callback in
`runtime.py:459` invokes `mark_completed` but never invokes `save_progress`.

Result: a user completes a lesson, the in-memory `progress_store` records it,
the runtime emits `LearnProgressState(action="snapshot")` with the updated
progress, the webview paints a completed dot. Then the user quits the app.
On next boot, `load_progress()` reads the on-disk `learn-progress.json` (still
empty if it never persisted) → the dot reverts to "pending". The user's
completion is silently lost.

Test gap: `test_mark_completed_updates_lesson` (line 126-134 of
`test_progress_persistence.py`) only asserts the in-memory dict mutation —
not that the change is written through to disk.

**Fix:**
```python
# In runtime.py on_enter_completed, after the mark_completed call:
try:
    self._progress.mark_completed(
        self._learn.current_course_id,
        self._learn.current_lesson_id,
    )
    # Persist to disk — atomic write via os.replace.
    from vibemix.learn.progress import save_progress
    save_progress(self._progress)
except Exception as exc:  # pragma: no cover — defensive
    import sys
    print(f"[learn.runtime] mark_completed/save failed: {exc!r}", file=sys.stderr)
```

Also extend `test_mark_completed_updates_lesson` to assert that after
`runtime.send` finishes the FSM lifecycle, `load_progress()` returns a
LearnProgress with the lesson recorded.

---

### CR-03: `dots_for_course(course_id)` ignores its argument — cross-course progress will leak in P94+

**File:** `src/vibemix/learn/progress.py:119-150`
**Issue:** The method signature accepts `course_id: str | None`, but the body
deliberately deletes the parameter (`del course_id`) and walks ALL
`self.lessons` regardless of which course they belong to. The
`# v9.0 ships course_0 only` comment justifies this for today, but the method
is called by `LessonRuntime.on_enter_loaded` (runtime.py:346) which threads
the active course's `course_id` through. When P94 lands Course 1 (16 lessons)
and Course 2 (14 lessons), this method will return all completed lessons
across all courses as the "progress dots" for whichever course is loaded.
The HUD will show 30+ dots when Course 1 should show 16.

This is technically a P94+ defect, BUT the contract is silently wrong NOW —
the schema's `progress_dots: { maxItems: 32 }` cap was the band-aid against
this exact failure, and any phase that ships a second course breaks the HUD
silently. Don't ship this with `del course_id`.

**Fix:** Filter by course prefix:
```python
def dots_for_course(
    self, course_id: str | None
) -> tuple[dict[str, str], ...]:
    if course_id is None:
        return ()
    # Course id encodes its number: "course_0" → L0.*, "course_1" → L1.*, etc.
    # Use a CURRICULUM-backed lookup instead of string prefix when CURRICULUM
    # gains a course→lesson_id mapping; for v9.0 the prefix is correct.
    course_num = course_id.replace("course_", "")
    expected_prefix = f"L{course_num}."
    dots: list[dict[str, str]] = []
    for lesson_id, entry in self.lessons.items():
        if not lesson_id.startswith(expected_prefix):
            continue
        if entry.get("completed") is True:
            dots.append({"lesson_id": lesson_id, "status": "completed"})
    return tuple(dots)
```

Add a test that mark_completed on `L0.00-press-play` returns 1 dot for
course_0 and 0 dots for course_1.

---

### CR-04: Reset confirmation toast is unreachable — surface mismatch between drawer and Learn window

**File:** `tauri/ui/src/settings/components/learn-group.ts:210-218`, `tauri/ui/src/learn/learn-window.ts:368-372`
**Issue:** The "Reset Learn Progress" button lives in the Settings drawer of
the Session window. The drawer dispatches
`ipc.learn.progress_state { action: "reset" }`. The handler that surfaces
the "learn progress reset." toast (`showLearnToast`) is in
`learn-window.ts:525-532` — only mounted inside the Learn window's DOM.

When the user clicks "reset" in the Session window's settings drawer:
1. The local optimistic-dismiss closes the dialog (good).
2. The IPC frame fires (would be received only if CR-01 is fixed).
3. If reset_ack ever arrives, it broadcasts to all ws clients including the
   Session window — but the Session window's `mountSettingsDrawer` does NOT
   subscribe to `ipc.learn.progress_state`. Only the Learn window does.
4. Result: the user has no feedback in the surface they're standing on.

Even with CR-01 fixed (handler registered + ack emitted), the user clicking
"reset" in the Session drawer never sees confirmation in that window. They'd
have to switch to the Learn window to see "learn progress reset." which is
the opposite of optimistic-repaint UX.

**Fix:** Move the toast surface to the drawer itself, OR subscribe the
session window's `learn-group.ts` to `ipc.learn.progress_state`:

```typescript
// In learn-group.ts, after emitIpcReset() — or better, inside it:
async function emitIpcReset(): Promise<void> {
  try {
    await emitIpc("ipc.learn.progress_state", { action: "reset" });
    // Show local toast — same shape as the Learn window's showLearnToast.
    showSessionToast("learn progress reset.");
  } catch (err) {
    console.warn("[learn-group] reset emitIpc failed:", err);
  }
}
```

Or subscribe to `ipc.learn.progress_state` in the session window's
`session-window.ts` and surface the toast there.

---

## Warnings

### WR-01: `lesson_tick_task` is not in the shutdown cleanup list — leaks on SIGINT

**File:** `src/vibemix/__main__.py:1642`, lines 1719-1729
**Issue:** `lesson_tick_task = asyncio.create_task(lesson_runtime.tick_loop(stop_event))`
is created at line 1642 but is NOT included in the `cleanup_tasks` list at
line 1719-1729. On shutdown, the other tasks are cancelled + awaited, but
`lesson_tick_task` is not.

`tick_loop` does check `stop_event.is_set()` inside its loop (runtime.py:564),
so it WILL exit on its own eventually. But the main coroutine doesn't await
it — so the event loop can shut down while `tick_loop`'s `await asyncio.sleep(1.0)`
is in flight, producing the "Task was destroyed but it is pending" CPython
warning at exit.

**Fix:**
```python
cleanup_tasks: list[asyncio.Task] = [
    coach_task,
    refresh_task,
    screen_task,
    ws_task,
    diag_task,
    track_task,
    deck_poll_task,
    parent_watch_task,
    midi_watcher_task,
    lesson_tick_task,  # ← add
]
```

---

### WR-02: `on_enter_loaded` does not validate `lesson_id` before indexing CURRICULUM — KeyError swallowed but FSM advances anyway

**File:** `src/vibemix/learn/runtime.py:316-362`
**Issue:** The callback guards `if lesson_id is not None: self._learn.current_lesson_id = lesson_id` at line 331. If a caller invokes `send("load")` without supplying `lesson_id`, `self._learn.current_lesson_id` stays None. Line 345 then does `lesson = CURRICULUM[self._learn.current_lesson_id]` → `CURRICULUM[None]` → KeyError, caught by the try/except at line 356 and printed to stderr.

The FSM state transitions to `loaded` regardless (the callback runs AFTER the transition). A subsequent `send("begin")` succeeds, enters `awaiting_action`, which tries the same `CURRICULUM[None]` lookup — silently caught and emit drops.

Net effect: an invalid `load` call leaves the FSM "stuck" in `awaiting_action` with no highlight, no tutor speak, no envelope ever reaches the webview. Hard to debug because there's no visible error in the live log path (only the bracket-tagged stderr line).

**Fix:** Validate before the transition runs by adding an `on_load` action that asserts the params resolve in CURRICULUM:
```python
def on_load(self, lesson_id: str | None = None, **_kwargs) -> None:
    if lesson_id is None or lesson_id not in CURRICULUM:
        # Better: refuse the transition. python-statemachine doesn't let
        # us veto from on_<event>, so raise so the caller sees the error.
        raise ValueError(f"unknown lesson_id {lesson_id!r}")
```

Or surface a typed error envelope (`ipc.error`) instead of silent failure.

---

### WR-03: Sidecar emits invalid `LearnLessonLoaded` payload when `controller_id` is empty — silent schema rejection

**File:** `src/vibemix/learn/runtime.py:343-355`, `tauri/ui/src/ipc/messages.schema.json:3054`
**Issue:** The schema requires `controller_id: {"type": "string", "minLength": 1}` on the lesson_loaded envelope. The runtime's `on_enter_loaded` builds the envelope with `controller_id=self._learn.current_controller_id or ""` (line 352). When no controller is bound yet (first-run flow, controller unplugged), `current_controller_id` is None → `""` is emitted → JSON Schema validation fails → the entire emit chain raises, caught by the try/except at line 356.

The exception is logged to stderr but the HUD never mounts. The webview waits forever for the never-arriving lesson_loaded.

**Fix:** Either (a) defer `lesson_loaded` emit until a controller is bound, or (b) make `controller_id`'s minLength 0 in the schema and treat empty as "no controller yet". Today's behavior — load + crash + degrade to silence — is worse than either.

```python
# In on_enter_loaded:
if not self._learn.current_controller_id:
    # No controller bound; defer the HUD mount until controller_detected fires.
    return
# ... emit envelope ...
```

---

### WR-04: `_finish_when_dwelled` can fire after a re-load — orphan finish silently no-ops but accumulates tasks

**File:** `src/vibemix/learn/runtime.py:444-454`
**Issue:** `on_enter_advancing` schedules `asyncio.create_task(self._finish_when_dwelled())` (line 444). The coroutine awaits ~45s+0.7s and then sends `finish`. If during that wait the user re-loads (post-completion replay), the FSM moves through `completed → loaded → awaiting_action`. The orphaned task wakes up and fires `finish`, which is silently no-op'd by `allow_event_without_transition = True` (no `finish` transition from `awaiting_action`).

The orphaned task is fine as a no-op, BUT:
1. The task reference is dropped immediately after `create_task` (line 444). Per CPython docs, this is exactly the "weak-reference garbage-collection" path that the `_background_tasks` set was created for elsewhere in `__main__.py:1465`.
2. Long-lived sessions with multiple lesson replays will silently leak coroutines.

**Fix:** Track the in-flight finish task and cancel on re-load:
```python
def __init__(self, ...):
    ...
    self._finish_task: asyncio.Task | None = None

def on_enter_advancing(self, **_kwargs):
    ...
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # Cancel any stale in-flight finish task before creating a new one.
        if self._finish_task is not None and not self._finish_task.done():
            self._finish_task.cancel()
        self._finish_task = asyncio.create_task(self._finish_when_dwelled())

def on_enter_loaded(self, ...):
    # Cancel any in-flight finish from a prior lesson.
    if self._finish_task is not None and not self._finish_task.done():
        self._finish_task.cancel()
    self._finish_task = None
    ...
```

---

### WR-05: `LearnExpectedAction.direction` does not include `""` empty sentinel for CC controls — type mismatch with sidecar

**File:** `tauri/ui/src/ipc/messages.ts:832-833`, `src/vibemix/ui_bus/learn_messages.py:399`
**Issue:** The TypeScript-generated type says `direction?: "" | "up" | "down"`. The Python dataclass `LearnExpectedAction.direction: Literal["", "up", "down"]` defaults to `""`. But for CC controls (which have no direction), the runtime emits `expected.get("direction", "")` so the field is `""`. The schema permits `""` (enum `["", "up", "down"]`).

This is not actually a bug, but it's a contract smell: the schema, TS type, and Python dataclass all use the empty-string sentinel for "absent direction", but a CC control's payload always carries the field as `""`. Reviewers can easily mistake this for a missing-data bug.

**Fix:** Either accept this is convention (and document it) or make the field optional in the schema (`required: ["type", "control"]` already, so direction is optional — just remove it from CC payloads entirely instead of stamping `""`).

---

### WR-06: `LessonSkipButton` lockout state is not synced to the runtime's `min_dwell_elapsed` predicate — clock drift on rebind

**File:** `tauri/ui/src/learn/lesson/skip-button.ts:46-138`, `src/vibemix/learn/runtime.py:294-300`
**Issue:** The TypeScript button starts its own `setTimeout(45_000)` lockout from the moment it's mounted (line 123 in skip-button.ts). The Python runtime's `min_dwell_elapsed` predicate reads `time.monotonic() - self._learn.lesson_started_at >= 45.0` — `lesson_started_at` is set inside `on_enter_loaded`.

If `lesson_loaded` envelope is delayed by even 1-2 seconds (network burst, slow ws-client startup), the TS lockout starts BEFORE the Python lesson clock. The user clicks "i got it" at TS clock+46s = Python clock+44.5s. The TS button is unlocked (fires `onSkip()`), the emit reaches the sidecar (post-CR-01 fix), the runtime evaluates `min_dwell_elapsed` → False → silent no-op via `allow_event_without_transition`.

Result: button unlocks visually but the click does nothing for ~0.5-1.5s. User clicks again. Then it works. Confusing UX, hard to attribute.

**Fix:** Anchor the TS lockout on the `lesson_loaded` envelope's `ts` (or, better, on `tutor_speak.ts` of beat 0 which is the actual "lesson started" moment). The runtime could also emit a one-shot `lesson_clock_started` envelope or include `lesson_started_at` in `lesson_loaded`'s payload.

Cheaper fix: add a small grace margin in the runtime (`>= 44.5` instead of `>= 45.0`) so the predicate is forgiving of TS-side clock drift.

---

### WR-07: TutorSpeakDock `applyHighlight` runs against a stale stage when the controller disconnects mid-lesson

**File:** `tauri/ui/src/learn/learn-window.ts:213-222, 323-327`
**Issue:** When `controller_detected { connected: false }` fires, the handler calls `stage.clear()` (line 217) which sets `mountedControllerId = null` and `el.innerHTML = ""`. The lesson HUD remains mounted. If a NEW `ipc.learn.highlight` envelope arrives before the next `controller_detected { connected: true }` (race condition possible because the sidecar emits both via the same ws), `applyHighlight` walks an empty stage and `console.warn`s. No actual harm, but the user sees an unhelpful console message and the highlight is silently lost.

**Fix:** Gate `applyHighlight` on `stage.currentControllerId !== null`:
```typescript
window.addEventListener("ipc.learn.highlight", (ev: Event) => {
  const payload = (ev as CustomEvent<HighlightPayload>).detail;
  if (!payload) return;
  if (stage.currentControllerId === null) return;  // no SVG mounted
  applyHighlight(stageEl, payload);
});
```

---

## Info

### IN-01: `_FORBIDDEN_TUTOR_MOVES_LOCK` constant uses module-level `_` prefix but is not a true private (referenced by tests)

**File:** `src/vibemix/learn/prompts.py:52-80`
**Issue:** The constant has the `_FORBIDDEN_TUTOR_MOVES_LOCK` underscore-prefix convention (private). It's only referenced inside `prompts.py`, but `tests/learn/test_tutor_system_instruction_lock.py` proves its tokens are in the public `build_tutor_system_instruction()` output. The privacy is enforced by the AST gate, not the convention. The leading underscore is fine here, but consider documenting that it's a hard-locked test-pinned literal.

**Fix:** No code change required. Optionally add a docstring `# AST-gated: test_tutor_system_instruction_lock.py asserts 4 tokens`.

---

### IN-02: Settings drawer's LearnGroup mentions "all 36 lessons across 3 courses" in dialog body — copy is forward-looking but accurate (v9.0 ships 1 lesson)

**File:** `tauri/ui/src/settings/components/learn-group.ts:204-206`
**Issue:** The destructive confirm dialog says "all 36 lessons across 3 courses will reset to not started". For v9.0 launch, only Course 0 with 1 lesson exists. A user who has completed the single lesson sees a dialog claiming to reset 36 lessons across 3 courses — slightly misleading.

**Fix:** Reword to reference the actual state: "this clears every completed lesson in vibemix learn." Or wait until P94/P95/P96 land the other courses.

---

### IN-03: `progress.py:save_progress` does not `fsync` before `os.replace` — bytes may not be on disk if power loss occurs between write and rename

**File:** `src/vibemix/learn/progress.py:214-235`
**Issue:** Standard pattern: `tmp.write_text → os.replace(tmp, p)`. POSIX rename is atomic at filesystem level, but bytes may still be in OS page cache when the rename completes. A power loss between the write and the next filesystem sync can leave the renamed file with garbage contents (though atomic rename ensures it's either fully-old or fully-new, never half-half).

This matches the existing `config_store.py` pattern (line 274-277) so the project convention is "rely on the rename atomicity, don't fsync". The `corrupt_file_recovers_clean` test covers the corruption path. Documenting this is enough; no fix required for v9.0.

**Fix:** No change. Optional: add `with open(tmp, "wb") as f: f.write(payload.encode()); os.fsync(f.fileno())` if learn-progress.json corruption becomes a real-world concern.

---

### IN-04: Several places use bare `Exception` catches with `# pragma: no cover — defensive` — silent failure mode

**File:** `src/vibemix/learn/runtime.py:356, 384, 428, 463, 474, 493, 520, 543`
**Issue:** 8 emit-call try/except blocks all use `except Exception as exc: print(f"[learn.runtime] ... failed: {exc!r}", file=sys.stderr)`. Per project convention this is acceptable — never wedge the FSM on an emit failure. But the bracket-tagged stderr is not surfaced anywhere visible (no log file aggregator wires it into the UI). A run with broken IPC will silently fail every emit.

**Fix:** No fix required for v9.0. Optionally route through the existing `tracer` so failures land in events.jsonl + are visible via the debrief surface.

---

### IN-05: `LearnLessonLoaded.make` accepts both `tuple[dict, ...]` and `tuple[LearnProgressDot, ...]` via heuristic isinstance check — fragile to mixed input

**File:** `src/vibemix/ui_bus/learn_messages.py:349-363`
**Issue:** The factory accepts `progress_dots: tuple[LearnProgressDot, ...] | list[dict] | tuple[dict, ...]`. The discriminator is `if progress_dots and isinstance(progress_dots[0], dict):`. A MIXED input — say `(LearnProgressDot(...), {"lesson_id": ..., "status": ...})` — would take the dict branch (because [0] is dataclass, not dict) and try to call `d["lesson_id"]` on the dataclass → TypeError.

In practice no caller mixes types, but the type contract is `Sequence[Union[A,B]]` which allows it. The runtime's `progress_store.dots_for_course()` returns a uniform tuple of dicts, so this doesn't fire today.

**Fix:** No change. Optionally tighten the type to `tuple[LearnProgressDot, ...] | tuple[dict, ...]` (homogeneous) and document the assumption.

---

_Reviewed: 2026-05-28T05:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
