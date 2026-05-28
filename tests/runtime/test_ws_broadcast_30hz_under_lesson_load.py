# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — 30 Hz ws_broadcast cadence pin under LessonRuntime load.

Pitfall 6 mitigation (92-RESEARCH.md §Pitfall 6). The new 1 Hz
:meth:`LessonRuntime.tick_loop` runs alongside the existing 30 Hz
``ws_broadcast`` producer. If ``on_enter_<state>`` callbacks block on
synchronous file I/O or LLM calls, the ws_broadcast tick budget
(33 ms) is exceeded → mascot frame cadence drifts visibly + highlight
paint exceeds the 16 ms budget (the user-perceived flutter cascades
across the Learn surface).

This test pins the cadence contract by driving:

* ``ws_broadcast`` for ~100 ticks (fast-forwarded via patched
  ``asyncio.sleep``).
* :class:`LessonRuntime` instantiated in parallel; the runtime's
  ``tick_loop(stop_event)`` coroutine runs at 1 Hz under the same
  fast-forwarded clock.

Assertion: mascot emit count stays within ±5% of 100 — the 1 Hz tick
loop must NOT stutter the 30 Hz hot path.

The test is RED-state stub today (Plan 92-03 lands ``LessonRuntime``).
Mirrors ``tests/runtime/test_ws_broadcast_30hz_under_learn_load.py``
(P91) verbatim except for the LessonRuntime instantiation + tick_loop
coroutine.

REQ-ID: RENDER-04 (highlight paint ≤16 ms; depends on 30 Hz cadence
holding under 1 Hz LessonRuntime tick load).

Sampling: per-wave merge (~5 s wall-clock cap).
"""
from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def _has_lesson_runtime() -> bool:
    """Plan 92-03 ships ``vibemix.learn.runtime.LessonRuntime`` with a
    ``tick_loop(stop_event)`` coroutine. False before then."""
    try:
        from vibemix.learn.runtime import LessonRuntime  # noqa: F401
    except ImportError:
        return False
    return True


def _ws_broadcast_accepts_midi_mirror_kwarg(ws_bus_module) -> bool:
    """Plan 91-03 added the ``midi_mirror`` kwarg to ``ws_broadcast``; we
    require it AND a working LessonRuntime to run this test."""
    fn = getattr(ws_bus_module, "ws_broadcast", None)
    if fn is None:
        return False
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return "midi_mirror" in sig.parameters


@pytest.mark.anyio("asyncio")
async def test_30hz_cadence_holds_under_lesson_runtime_tick_loop(mocker) -> None:
    """Drive ``ws_broadcast`` for ~100 ticks while LessonRuntime's 1 Hz
    ``tick_loop`` runs in parallel. Assert mascot-frame emit count stays
    within ±5% of 100 — pinning RESEARCH §Pitfall 6: the 1 Hz tick loop
    must NOT stutter the 30 Hz hot path.

    Skip-gated until Plan 92-03 ships LessonRuntime + its tick_loop
    coroutine.
    """
    if not _has_lesson_runtime():
        pytest.skip(
            "tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py "
            "awaits Plan 92-03 (LessonRuntime + tick_loop coroutine)."
        )

    pytest.importorskip(
        "vibemix.learn.midi_mirror",
        reason="Plan 91-03 lands src/vibemix/learn/midi_mirror.py",
    )
    ws_bus_module = pytest.importorskip(
        "vibemix.runtime.ws_bus",
        reason="Plan 91-03 adds midi_mirror kwarg to ws_broadcast",
    )
    if not _ws_broadcast_accepts_midi_mirror_kwarg(ws_bus_module):
        pytest.skip(
            "Plan 91-03 lands midi_mirror kwarg on ws_broadcast — "
            "without it, this cadence pin cannot exercise the Learn path"
        )

    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState
    from vibemix.runtime.ws_bus import ws_broadcast
    from vibemix.state.music_state import MusicState

    # ---------- Patch the WS server so no real socket is bound ----------
    mock_server = MagicMock()
    mock_server.close = MagicMock()
    mock_server.wait_closed = AsyncMock(return_value=None)
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    # ---------- Fake Levels with a constant snapshot ----------
    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(
        return_value={"music": 0.05, "voice": 0.02, "mic": 0.01}
    )

    state = MusicState()
    state.audible = True
    state.audible_deck = "A"
    state.phase = "groove"
    state.bpm = 124.0
    state.mood = "hype-man"
    state.bpm_confidence = 0.8
    state.downbeat_phase = 0.25
    state.beat_phase = 0.25
    state.active_genre = "house"
    state.detected_genre = "house"
    state.genre_confidence = 0.7
    state.emotion = None
    state.last_reaction_intent = None

    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    constant_position_frame = {
        "type": "ipc.learn.midi_position",
        "ts": "2026-05-28T00:00:00Z",
        "payload": {
            "controller_id": "pioneer_ddj_flx4",
            "positions": {"eq_hi:A": 64, "xfader": 64},
        },
    }
    midi_mirror_stub = SimpleNamespace(
        drain_pending_detected=lambda: [],
        snapshot=lambda: constant_position_frame,
    )

    # ---------- LessonRuntime in awaiting_action state ----
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=midi_mirror_stub,
        controller_state=MagicMock(),
        ipc_router=MagicMock(),
        progress_store=MagicMock(),
    )
    # Drive runtime into awaiting_action so tick_loop has work to do
    # (strike escalation timer running).
    try:
        runtime.send(
            "load",
            lesson_id="L0.00-press-play",
            course_id="course_0",
            controller_id="pioneer_ddj_flx4",
        )
        runtime.send("begin")
    except Exception:
        # If Plan 92-03 picks a different bootstrapping API, the test
        # is still meaningful — the tick_loop coroutine runs even
        # without a live FSM transition.
        pass

    sent_payloads: list[str] = []
    release_handler = asyncio.Event()

    class LongLivedClient:
        async def send(self, payload):
            sent_payloads.append(payload)

        def __aiter__(self):
            async def gen():
                await release_handler.wait()
                if False:  # pragma: no cover — never yields
                    yield

            return gen()

    _REAL_SLEEP = asyncio.sleep
    tick_counter = {"n": 0}

    async def fast_sleep(_s):
        tick_counter["n"] += 1
        if tick_counter["n"] >= 100:
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch(
        "vibemix.runtime.ws_bus.asyncio.sleep",
        side_effect=fast_sleep,
    )

    async def driver():
        # Run BOTH the 30 Hz ws_broadcast AND the 1 Hz LessonRuntime
        # tick_loop in parallel. The tick_loop coroutine is plan-92-03's
        # contract — it MUST yield often enough that 30 Hz cadence is
        # preserved.
        bg = asyncio.create_task(
            ws_broadcast(
                fake_levels,
                state,
                manual_trigger,
                stop_event,
                midi_mirror=midi_mirror_stub,
            )
        )
        tick_loop_task = asyncio.create_task(runtime.tick_loop(stop_event))
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]
        client = LongLivedClient()
        ht = asyncio.create_task(handler(client))
        await bg
        try:
            await asyncio.wait_for(tick_loop_task, timeout=0.5)
        except Exception:
            tick_loop_task.cancel()
        try:
            await asyncio.wait_for(ht, timeout=0.5)
        except Exception:
            ht.cancel()

    await asyncio.wait_for(driver(), timeout=5.0)

    mascot_emits = 0
    for raw in sent_payloads:
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        if not isinstance(msg, dict):
            continue
        if msg.get("type"):
            # Tagged envelope — not a mascot frame.
            continue
        if "music" in msg and "voice" in msg and "mic" in msg:
            mascot_emits += 1

    expected = 100
    tolerance = expected * 0.05  # ±5
    assert abs(mascot_emits - expected) <= tolerance, (
        f"30 Hz cadence drifted under LessonRuntime tick_loop — "
        f"mascot_emits={mascot_emits} vs expected ~{expected} "
        f"(tolerance ±{tolerance:.1f}). LessonRuntime.tick_loop is "
        "blocking the asyncio loop — refactor on_enter_<state> "
        "callbacks to await loop.run_in_executor(None, ...) for any "
        "file I/O (Pitfall 6 mitigation)."
    )
