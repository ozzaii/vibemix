# SPDX-License-Identifier: Apache-2.0
"""LessonRuntime end-to-end smoke regression tests.

End-to-end lifecycle of a single lesson:

1. Instantiate :class:`LessonRuntime` with a stub ipc_router + progress
   store.
2. Send ``load`` → state moves ``idle → loaded``.
3. Send ``begin`` → state moves ``loaded → awaiting_action``.
4. Send ``ack_action`` with a MIDI-matched event → guard
   ``action_matches`` returns True → state moves
   ``awaiting_action → advancing`` → eventually ``completed``.
5. Assert the ipc_router received at least one each of
   :class:`LearnLessonLoaded`, :class:`LearnHighlight`,
   :class:`LearnTutorSpeak`, :class:`LearnAdvance` envelope shapes.

Plus a secondary test that the 45 s min-dwell guard rejects ``skip``
before t=45 and accepts it after.

REQ-ID: LESSON-01 (state machine + sole-writer enforcement) + LESSON-04
(advance gate).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState
except ImportError:
    pytest.skip(
        "LessonRuntime + LearnState unavailable in this partial Learn build.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runtime() -> tuple[LessonRuntime, MagicMock]:
    """Build a LessonRuntime with mocked dependencies.

    The exact ctor signature is Claude's-discretion per 92-CONTEXT
    "Claude's Discretion" section — but the contract is: a runtime that
    can be ``.send(...)``-ed and whose emits land on ``ipc_router.emit``.
    """
    learn_state = LearnState()
    midi_mirror = MagicMock(name="midi_mirror")
    controller_state = MagicMock(name="controller_state")
    ipc_router = MagicMock(name="ipc_router")
    progress_store = MagicMock(name="progress_store")
    runtime = LessonRuntime(
        learn_state=learn_state,
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=ipc_router,
        progress_store=progress_store,
    )
    return runtime, ipc_router


def _emitted_envelope_types(ipc_router: MagicMock) -> list[str]:
    """Pull every type-tagged dict the runtime emitted into ipc_router.

    Tolerates emit(envelope_dict) OR emit(type, payload_dict) call
    signatures — Plan 92-03 picks one; the test reads either.
    """
    types: list[str] = []
    for call in ipc_router.emit.call_args_list:
        args, kwargs = call
        if args and isinstance(args[0], dict) and "type" in args[0]:
            types.append(args[0]["type"])
        elif args and isinstance(args[0], str):
            # emit("ipc.learn.lesson_loaded", {...}) shape
            types.append(args[0])
        elif "type" in kwargs:
            types.append(kwargs["type"])
    return types


def _emitted_envelopes(ipc_router: MagicMock) -> list[dict]:
    """Pull type-tagged dict envelopes from the runtime emit mock."""
    envelopes: list[dict] = []
    for call in ipc_router.emit.call_args_list:
        args, _kwargs = call
        if args and isinstance(args[0], dict) and "type" in args[0]:
            envelopes.append(args[0])
    return envelopes


# ---------------------------------------------------------------------------
# Test 1: full lifecycle
# ---------------------------------------------------------------------------


def test_full_lifecycle() -> None:
    """A fresh LessonRuntime loads + begins + matches MIDI → emits the
    expected envelope sequence + lands in advancing or completed."""
    runtime, ipc_router = _make_runtime()

    # idle → loaded
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )

    # loaded → awaiting_action
    runtime.send("begin")

    # awaiting_action → advancing (or further → completed depending on
    # whether the runtime auto-advances through completed in one step)
    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
        },
    )

    emitted = _emitted_envelope_types(ipc_router)
    # The runtime must have emitted at least one of each of these four
    # envelope shapes over the lifecycle. The exact order depends on
    # state-entry callbacks (Claude's discretion in Plan 92-03), but
    # every one of these is mandatory.
    for required in (
        "ipc.learn.lesson_loaded",
        "ipc.learn.highlight",
        "ipc.learn.tutor_speak",
        "ipc.learn.advance",
    ):
        assert required in emitted, (
            f"LessonRuntime full-lifecycle missing required emit "
            f"{required!r}. Saw: {emitted!r}"
        )


def test_lesson_loaded_emits_full_course_progress_dots() -> None:
    """Live HUD dots must include completed, current, and pending rows.

    The frontend can render ``current`` and ``pending``, but the runtime
    must send the complete course strip or the HUD opens with ``OF 0``.
    """
    from vibemix.learn.progress import LearnProgress

    learn_state = LearnState()
    ipc_router = MagicMock(name="ipc_router")
    progress = LearnProgress()
    progress.mark_completed("course_1_anatomy", "L1.01")
    runtime = LessonRuntime(
        learn_state=learn_state,
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc_router,
        progress_store=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )

    loaded = next(
        env
        for env in _emitted_envelopes(ipc_router)
        if env["type"] == "ipc.learn.lesson_loaded"
    )
    dots = loaded["payload"]["progress_dots"]
    assert len(dots) == 16
    by_id = {dot["lesson_id"]: dot["status"] for dot in dots}
    assert by_id["L1.01"] == "completed"
    assert by_id["L1.03"] == "current"
    assert by_id["L1.04"] == "pending"


def test_lesson_start_emits_in_progress_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Loading a lesson creates and persists an unfinished attempt row."""
    from vibemix.learn.progress import LearnProgress, load_progress

    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    ipc_router = MagicMock(name="ipc_router")
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc_router,
        progress_store=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )

    progress_snapshots = [
        env["payload"]["progress"]
        for env in _emitted_envelopes(ipc_router)
        if env["type"] == "ipc.learn.progress_state"
    ]
    assert progress_snapshots
    assert progress_snapshots[-1]["lessons"]["L1.03"] == {
        "completed": False,
        "completed_at": None,
        "strikes_used": 0,
    }
    assert target.exists()
    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.lessons["L1.03"] == {
        "completed": False,
        "completed_at": None,
        "strikes_used": 0,
    }


def test_hint_strike_updates_live_progress_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Timed hints turn the unfinished row into durable adaptation data."""
    from vibemix.learn.progress import LearnProgress, load_progress

    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    ipc_router = MagicMock(name="ipc_router")
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc_router,
        progress_store=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("strike")

    progress_snapshots = [
        env["payload"]["progress"]
        for env in _emitted_envelopes(ipc_router)
        if env["type"] == "ipc.learn.progress_state"
    ]
    assert progress_snapshots[-1]["lessons"]["L1.03"]["strikes_used"] == 1
    assert target.exists()
    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.lessons["L1.03"]["strikes_used"] == 1


# ---------------------------------------------------------------------------
# Test 2: min-dwell guard rejects skip < 45s, accepts skip ≥ 45s
# ---------------------------------------------------------------------------


def test_idle_to_completed_with_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """The 45 s anti-speedrun min-dwell guard:

    * Before 45 s elapsed → ``send("skip")`` is rejected; state stays
      in ``awaiting_action``.
    * After 45 s → ``send("skip")`` accepted; state moves to
      ``advancing`` (or further to ``completed``).
    """
    import time

    # Pretend t=10 s at "begin"
    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    runtime, _ipc_router = _make_runtime()
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    # Skip BEFORE 45 s elapsed — must be rejected; state stays in
    # awaiting_action.
    fake_now["t"] = base + 10.0
    runtime.send("skip")
    assert runtime.current_state.id == "awaiting_action", (
        "min-dwell guard failed — skip at t+10s should NOT advance the "
        f"runtime, but state is now {runtime.current_state.id!r}"
    )

    # Skip AFTER 45 s — must be accepted.
    fake_now["t"] = base + 46.0
    runtime.send("skip")
    assert runtime.current_state.id in {"advancing", "completed"}, (
        "min-dwell guard failed — skip at t+46s should advance the "
        f"runtime, but state is now {runtime.current_state.id!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: WR-03 (P92 REVIEW) — empty controller_id defers lesson_loaded emit
# ---------------------------------------------------------------------------


def test_empty_controller_id_defers_lesson_loaded_emit() -> None:
    """WR-03 (P92 REVIEW) regression. The lesson_loaded schema requires
    ``controller_id: {minLength: 1}``. When no controller is bound yet
    (first-run flow, controller unplugged mid-load), the runtime
    previously emitted with controller_id="" → schema validation
    rejected the envelope → broad except caught the failure → HUD never
    mounted → webview waited forever.

    Post-fix: the on_enter_loaded callback bails BEFORE the emit when
    controller_id is empty/None. The lesson_loaded envelope is deferred
    until a controller is bound. The webview's empty-state surface
    stays visible (the expected first-run UX).
    """
    runtime, ipc_router = _make_runtime()
    # Load WITHOUT a controller_id — empty-string fallback would have
    # been emitted before the fix.
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="",
    )
    emitted = _emitted_envelope_types(ipc_router)
    assert "ipc.learn.lesson_loaded" not in emitted, (
        "WR-03 fix missing — lesson_loaded was emitted with empty "
        f"controller_id (schema-invalid). emitted={emitted!r}"
    )

    # Now provide a real controller_id — emit fires.
    runtime2, ipc_router2 = _make_runtime()
    runtime2.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    emitted_clean = _emitted_envelope_types(ipc_router2)
    assert "ipc.learn.lesson_loaded" in emitted_clean, (
        "lesson_loaded should emit when a real controller is bound"
    )


# ---------------------------------------------------------------------------
# Test 4: WR-02 (P92 REVIEW) — invalid lesson_id is a silent no-op
# ---------------------------------------------------------------------------


def test_invalid_lesson_id_does_not_wedge_fsm() -> None:
    """WR-02 (P92 REVIEW) regression. ``send("load")`` with a missing or
    unknown ``lesson_id`` MUST NOT crash and MUST NOT leave the FSM in
    an unrecoverable state.

    Pre-fix behavior: the on_enter_loaded callback tried
    ``CURRICULUM[None]`` / ``CURRICULUM[<unknown>]`` → KeyError caught by
    the broad except → no envelope emitted but the FSM already
    transitioned. A follow-up send("begin") similarly failed on the
    CURRICULUM lookup in on_enter_awaiting_action and the FSM landed
    in awaiting_action with NO highlight and NO tutor speak — the
    webview waited forever.

    Post-fix: the on_enter_loaded guard bails before the lookup, leaving
    the FSM in ``loaded`` state with no envelope emitted. A follow-up
    send("begin") similarly short-circuits in on_enter_awaiting_action —
    no emit, but the FSM doesn't wedge in an inconsistent state either.
    """
    runtime, ipc_router = _make_runtime()

    # Send load with no lesson_id at all.
    runtime.send("load")
    # send() returns None (allow_event_without_transition); FSM
    # transitioned to loaded but the callback bailed without emitting.
    assert runtime.current_state.id == "loaded"
    emitted = _emitted_envelope_types(ipc_router)
    # No lesson_loaded envelope on the wire because the guard short-
    # circuited before the emit. This is the documented WR-02 behavior:
    # better to silently NOT mount the HUD than to mount it with a
    # KeyError-filled stderr stream + stuck FSM.
    assert "ipc.learn.lesson_loaded" not in emitted, (
        "WR-02 fix missing — lesson_loaded was emitted with no valid "
        f"lesson_id. emitted={emitted!r}"
    )

    # Try begin → should also short-circuit cleanly.
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"
    emitted_after = _emitted_envelope_types(ipc_router)
    assert "ipc.learn.highlight" not in emitted_after, (
        "WR-02 fix missing — highlight emitted on invalid lesson_id"
    )

    # Now recover by loading a valid lesson — the FSM should accept it.
    # First force back to a state that accepts load (only idle/completed
    # do). We can't move back from awaiting_action, but the practical
    # contract for v9.0 is "boundary handler rejects bad ids before
    # they reach the runtime"; the guards here are belt-and-braces.
    # Verify the runtime can be re-instantiated cleanly.
    runtime2, ipc_router2 = _make_runtime()
    runtime2.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime2.send("begin")
    emitted_clean = _emitted_envelope_types(ipc_router2)
    assert "ipc.learn.lesson_loaded" in emitted_clean
    assert "ipc.learn.highlight" in emitted_clean


# ---------------------------------------------------------------------------
# Test 4: WR-04 (P92 REVIEW) — stale _finish_when_dwelled tasks cancel on
# re-load
# ---------------------------------------------------------------------------


def test_finish_task_cancelled_on_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    """WR-04 (P92 REVIEW) regression. Without cancellation, a replay
    flow stacks one orphan _finish_when_dwelled task per cycle. The
    tasks all silently no-op via allow_event_without_transition (no
    state damage), but the coroutine references accumulate.

    With the fix:

      * on_enter_advancing stores the new task on self._finish_task,
        cancelling any prior in-flight task FIRST.
      * on_enter_loaded (the replay-flow entry point) also cancels
        any leftover in-flight task.

    Test path:

      1. Run an event loop so on_enter_advancing actually schedules a
         finish task (the smoke test path runs synchronously and the
         scheduling falls back to no-op).
      2. Drive to advancing — finish task scheduled.
      3. Re-load — first finish task cancelled, _finish_task reset.
      4. Drive to advancing again — new finish task scheduled, distinct
         from the first.
    """
    import asyncio
    import time

    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    async def run_lifecycle() -> None:
        runtime, _ipc = _make_runtime()
        runtime.send(
            "load",
            lesson_id="L0.00-press-play",
            course_id="course_0",
            controller_id="pioneer_ddj_flx4",
        )
        runtime.send("begin")
        runtime.send(
            "ack_action",
            midi={
                "type": "button",
                "control": "play",
                "deck": "A",
                "direction": "down",
            },
        )
        # The matching ack advances to ``advancing``; on_enter_advancing
        # scheduled a _finish_when_dwelled task because an event loop is
        # running.
        first_task = runtime._finish_task
        assert first_task is not None, (
            "on_enter_advancing must store the scheduled finish task "
            "on self._finish_task (WR-04 fix); got None"
        )
        assert not first_task.done(), (
            "fresh finish task should be pending"
        )

        # Force the FSM out of advancing into completed (the
        # _finish_when_dwelled task would do this after a 45 s sleep —
        # we drive it manually so the test isn't gated on wall-clock).
        # ``load`` only fires from idle/completed; we must reach
        # completed before re-loading. The send("finish") here mirrors
        # what the finish coroutine would have done.
        runtime.send("finish")
        assert runtime.current_state.id == "completed", (
            f"expected completed, got {runtime.current_state.id!r}"
        )

        # Re-load to simulate a post-completion replay BEFORE the
        # original finish task naturally fires. WR-04 fix: this MUST
        # cancel the in-flight task and reset _finish_task to None.
        runtime.send(
            "load",
            lesson_id="L0.00-press-play",
            course_id="course_0",
            controller_id="pioneer_ddj_flx4",
        )
        # The cancellation is synchronous; the task is marked cancelled
        # but the actual coroutine doesn't observe it until the next
        # await point. Yield once so the cancellation propagates.
        await asyncio.sleep(0)

        assert first_task.cancelled() or first_task.done(), (
            "WR-04 fix missing — first finish task was not cancelled "
            "on re-load. The runtime would have leaked the coroutine "
            "until its natural 45 s wakeup."
        )
        assert runtime._finish_task is None, (
            "on_enter_loaded must clear self._finish_task after "
            "cancellation"
        )

        # Drive through the lifecycle again — a fresh finish task is
        # scheduled.
        runtime.send("begin")
        runtime.send(
            "ack_action",
            midi={
                "type": "button",
                "control": "play",
                "deck": "A",
                "direction": "down",
            },
        )
        second_task = runtime._finish_task
        assert second_task is not None and second_task is not first_task, (
            "second cycle should schedule a NEW finish task distinct "
            "from the first"
        )

        # Tear down — cancel the live task so the test event loop closes
        # cleanly without a "Task was destroyed but it is pending"
        # warning.
        if second_task is not None and not second_task.done():
            second_task.cancel()
            try:
                await second_task
            except (asyncio.CancelledError, Exception):
                pass

    asyncio.run(run_lifecycle())


def test_matched_action_completes_after_short_settle() -> None:
    """A correct physical action should not wait out the skip dwell floor."""

    import asyncio

    async def run_lifecycle() -> None:
        runtime, _ipc = _make_runtime()
        runtime.send(
            "load",
            lesson_id="L0.00-press-play",
            course_id="course_0",
            controller_id="pioneer_ddj_flx4",
        )
        runtime.send("begin")
        runtime.send(
            "ack_action",
            midi={
                "type": "button",
                "control": "play",
                "deck": "A",
                "direction": "down",
            },
        )
        assert runtime.current_state.id == "advancing"
        await asyncio.sleep(0.85)
        assert runtime.current_state.id == "completed"

    asyncio.run(run_lifecycle())
