# SPDX-License-Identifier: Apache-2.0
"""Phase 92 CR-01 (P92 REVIEW) regression — inbound ipc.learn.* dispatch.

The :class:`LessonRuntime` FSM was wired in ``__main__.py`` but no
inbound IPC handler was registered for any of the 5 shell→sidecar learn
envelopes. ``IpcRouterBus.dispatch()`` returned False silently and the
FSM stayed parked in ``idle`` — the "press play" demo failed at the
very first envelope.

This module pins the inbound boundary: dispatching a synthetic envelope
through :class:`IpcRouterBus` MUST drive the FSM past ``idle`` (for
``start_lesson`` / ``start_course``) AND emit the expected response
envelopes (for ``progress_state`` action=reset).

REQ-ID: P92 REVIEW CR-01.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.runtime.ws_bus import IpcRouterBus


@pytest.fixture
def progress_path_in_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Redirect ``progress_path()`` to a tmp dir so each test starts with a
    clean canvas. Mirrors the fixture in
    ``test_progress_persistence.py``."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    return target


def _make_runtime() -> tuple[LessonRuntime, LearnProgress, MagicMock]:
    """Build a LessonRuntime + real LearnProgress + Mock ipc_router.

    The ipc_router here is the LessonRuntime's emit sink (the sync
    adapter); the actual inbound dispatch goes through a separate
    IpcRouterBus instance in the test bodies below.
    """
    learn_state = LearnState()
    midi_mirror = MagicMock(name="midi_mirror")
    midi_mirror.current_profile.return_value = None
    controller_state = MagicMock(name="controller_state")
    runtime_emit_sink = MagicMock(name="runtime_emit_sink")
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=learn_state,
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=runtime_emit_sink,
        progress_store=progress,
    )
    return runtime, progress, runtime_emit_sink


def test_start_lesson_dispatch_advances_fsm() -> None:
    """``ipc.learn.start_lesson`` envelope must drive idle → awaiting_action.

    Before CR-01 fix: ``IpcRouterBus.dispatch()`` returned False because
    no handler was registered; the FSM stayed parked in idle.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    assert runtime.current_state.id == "idle", "fresh runtime starts idle"

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L0.00-press-play",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True, (
        "CR-01 regression — ipc.learn.start_lesson must be recognized "
        "by IpcRouterBus.dispatch (handler registered)"
    )
    # After the 2-step load → begin sequence, the FSM is in
    # awaiting_action waiting for MIDI.
    assert runtime.current_state.id == "awaiting_action", (
        f"start_lesson should drive FSM to awaiting_action; "
        f"state={runtime.current_state.id!r}"
    )


def test_start_course_dispatch_advances_fsm() -> None:
    """``ipc.learn.start_course`` resolves the first lesson of the course
    and drives the FSM to awaiting_action.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_course",
                "payload": {
                    "course_id": "course_0",
                    "controller_id": "pioneer_ddj_flx4",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"


def test_start_lesson_unknown_id_silent_noop() -> None:
    """An unknown lesson_id must NOT raise and MUST leave the FSM idle.

    WR-02 mitigation — the FSM previously advanced through transitions
    on a None/unknown lesson_id with no visible error; the handler
    catches the invalid input at the boundary.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L99.99-from-the-future",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    # Dispatch returned True (handler ran) but rejected the invalid
    # lesson — FSM is still idle.
    assert handled is True
    assert runtime.current_state.id == "idle", (
        "unknown lesson_id must NOT advance the FSM; "
        f"state={runtime.current_state.id!r}"
    )


def test_ack_dispatch_drives_action_match() -> None:
    """A matching ``ipc.learn.ack`` MUST drive the FSM past awaiting_action.

    The runtime's action_matches guard checks the midi dict against the
    lesson's expected_action. For L0.00-press-play that's a play_a button
    press-down — the ack should match and advance.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    # Drive to awaiting_action first.
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"

    # Read the actual expected_action from CURRICULUM so this test stays
    # in sync with the lesson fixture without hardcoding the control.
    from vibemix.learn.curriculum import CURRICULUM

    expected = CURRICULUM["L0.00-press-play"].script["expected_action"]

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": (
                        f"{expected['control']}:{expected.get('deck', '')}"
                        if expected.get("deck")
                        else expected["control"]
                    ),
                    "source": "midi",
                    "value": 127,
                    "direction": expected.get("direction", ""),
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    # ack matched → FSM advances; either advancing or completed depending
    # on whether the post-advance auto-finish task fires in the test
    # event loop. Both states are acceptable observations of "advanced".
    assert runtime.current_state.id in {"advancing", "completed"}, (
        "matching ack should advance FSM past awaiting_action; "
        f"state={runtime.current_state.id!r}"
    )


def test_complete_lesson_user_skip_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ipc.learn.complete_lesson { reason: user_skip }`` drives send("skip").

    With the 45 s min-dwell guard satisfied, skip advances the FSM.
    """
    import time

    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    # Load + begin at t=base.
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    # Jump past the 45 s anti-speedrun floor.
    fake_now["t"] = base + 46.0

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.complete_lesson",
                "payload": {
                    "lesson_id": "L0.00-press-play",
                    "reason": "user_skip",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}, (
        "user_skip with min-dwell elapsed should advance FSM; "
        f"state={runtime.current_state.id!r}"
    )


def test_progress_state_reset_emits_ack_and_wipes_progress(
    progress_path_in_tmp: Path,
) -> None:
    """``ipc.learn.progress_state { action: reset }`` MUST:

      * unlink the on-disk file
      * clear the in-memory progress dicts
      * emit a ``reset_ack`` envelope through the ipc_router
    """
    runtime, progress, _ = _make_runtime()

    # Seed some progress to verify the wipe path actually runs.
    from vibemix.learn.progress import save_progress

    progress.mark_completed("course_0", "L0.00-press-play")
    save_progress(progress)
    assert progress_path_in_tmp.exists()
    assert "L0.00-press-play" in progress.lessons

    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    # Capture every emit through the bus's emit binding so we can
    # inspect the reset_ack frame.
    emitted: list[dict] = []

    async def _capture(d: dict) -> None:
        emitted.append(d)

    router.bind_emit(_capture)

    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
        # No ipc_adapter — handler awaits router.emit directly.
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.progress_state",
                "payload": {"action": "reset"},
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    # On-disk file rewritten with empty progress (save_progress fires
    # after reset_progress unlinks + we re-save the empty state).
    assert progress_path_in_tmp.exists(), (
        "reset path should re-save an empty progress file"
    )
    # In-memory dicts wiped.
    assert progress.lessons == {}, (
        f"in-memory lessons not cleared on reset; lessons={progress.lessons!r}"
    )
    assert progress.courses == {}
    # reset_ack emitted.
    ack_types = [e.get("type") for e in emitted]
    assert "ipc.learn.progress_state" in ack_types, (
        f"reset_ack envelope was not emitted; emitted types={ack_types!r}"
    )
    # Verify it's specifically a reset_ack (not snapshot etc).
    ack_actions = [
        e.get("payload", {}).get("action")
        for e in emitted
        if e.get("type") == "ipc.learn.progress_state"
    ]
    assert "reset_ack" in ack_actions, (
        f"action=reset_ack missing from emitted progress_state envelopes; "
        f"actions={ack_actions!r}"
    )


def test_progress_state_snapshot_emits_current_state() -> None:
    """``ipc.learn.progress_state { action: snapshot }`` emits the current
    persisted state as a snapshot envelope."""
    runtime, progress, _ = _make_runtime()
    progress.mark_completed("course_0", "L0.00-press-play")

    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    emitted: list[dict] = []

    async def _capture(d: dict) -> None:
        emitted.append(d)

    router.bind_emit(_capture)

    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.progress_state",
                "payload": {"action": "snapshot"},
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    snapshots = [
        e
        for e in emitted
        if e.get("type") == "ipc.learn.progress_state"
        and e.get("payload", {}).get("action") == "snapshot"
    ]
    assert len(snapshots) == 1, (
        f"expected one snapshot envelope, got {len(snapshots)}: {emitted!r}"
    )
    snap = snapshots[0]["payload"]["progress"]
    assert "L0.00-press-play" in snap.get("lessons", {})


def test_dispatch_unknown_type_returns_false() -> None:
    """Sanity check — unknown types still return False (handler bag is
    type-keyed). CR-01 only registers our 5; everything else stays
    unrecognized."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch({"type": "ipc.notalearntype"})

    assert asyncio.run(go()) is False
