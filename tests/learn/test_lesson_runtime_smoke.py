# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — LessonRuntime end-to-end smoke (RED-state stub).

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

This file is a STUB — Plan 92-03 ships ``LessonRuntime``, ``LearnState``,
and the dispatch wiring. Module-level skip names "Plan 92-03" so the
executor knows exactly when the skip flips. The test BODY shape is
written against the contract from 92-CONTEXT.md §LessonRuntime
architecture + 92-VALIDATION.md.

REQ-ID: LESSON-01 (state machine + sole-writer enforcement) + LESSON-04
(advance gate).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from vibemix.learn.runtime import LessonRuntime  # Plan 92-03
    from vibemix.learn.state import LearnState        # Plan 92-03
except ImportError:
    pytest.skip(
        "tests/learn/test_lesson_runtime_smoke.py awaits Plan 92-03 "
        "(LESSON-01 LessonRuntime + LearnState). When runtime.py + "
        "state.py land, this module-level skip flips to live "
        "assertions.",
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
