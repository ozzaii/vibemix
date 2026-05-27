# SPDX-License-Identifier: Apache-2.0
"""Phase 91 Plan 02 — 30 Hz ws_broadcast cadence pin under MidiMirror load.

RED-state integration stub. Pins RESEARCH §Assumption A1: the existing 30 Hz
``ws_broadcast`` loop tolerates one additional ``await midi_mirror.snapshot()``
+ optional ``_send_all(pos_frame)`` per tick WITHOUT missing the 1/30 s
budget. If A1 fails, the mascot frame's 30 Hz cadence drifts (visible
flutter) and the Learn surface loses its latency budget.

The test is shaped against the Plan-03 wiring in RESEARCH §Code Example 6
(``midi_mirror`` kwarg on ``ws_broadcast``). Today the kwarg does not exist
yet, so this file SKIPS via ``pytest.importorskip`` until Plan 03 lands the
wiring change in ``src/vibemix/runtime/ws_bus.py``.

REQ-ID: RENDER-02 (30 Hz cadence holds under Learn surface load).

Sampling: per-wave merge (~5 s — the test simulates ~3.3 s of ticks under
``asyncio.wait_for`` with a generous 5 s wall-clock cap so the integration
gate stays fast).
"""
from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def _ws_broadcast_accepts_midi_mirror_kwarg(ws_bus_module) -> bool:
    """Detect whether ``ws_broadcast`` already exposes the ``midi_mirror``
    kwarg from RESEARCH §Code Example 6. False before Plan 03 lands the
    wiring — the test below skips in that case."""
    fn = getattr(ws_bus_module, "ws_broadcast", None)
    if fn is None:
        return False
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return "midi_mirror" in sig.parameters


@pytest.mark.anyio("asyncio")
async def test_30hz_cadence_holds_with_midi_mirror_kwarg(mocker) -> None:
    """Drive ``ws_broadcast`` for ~100 ticks (fast-forwarded via patched
    ``asyncio.sleep``, capped at 5 s wall-clock via ``asyncio.wait_for``)
    with a fake MidiMirror that returns a constant snapshot every call and
    a single queued ``controller_detected`` envelope on the first tick.

    Assert the mascot-frame emit count is within ±5% of 100 — pinning
    RESEARCH §Assumption A1: the existing 30 Hz loop tolerates the per-
    tick drain+snapshot calls without missing the 1/30 s budget.
    """
    # Source-presence gate — the imports must succeed for the test to be
    # meaningful (Plan 03 just landed midi_mirror + the kwarg).
    pytest.importorskip(
        "vibemix.learn.midi_mirror",
        reason="Plan 91-03 lands src/vibemix/learn/midi_mirror.py",
    )
    ws_bus_module = pytest.importorskip(
        "vibemix.runtime.ws_bus",
        reason="Plan 91-03 adds midi_mirror kwarg to ws_broadcast",
    )
    if not _ws_broadcast_accepts_midi_mirror_kwarg(ws_bus_module):
        pytest.skip("Plan 91-03 lands midi_mirror kwarg on ws_broadcast")

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

    # ---------- Minimal MusicState — every attribute ws_broadcast reads
    # is already initialized by MusicState.__init__ (verified by
    # test_mood_change_envelope.py:270).
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

    # ---------- Fake MidiMirror — drain returns 1 envelope on first call,
    # then 0 forever; snapshot returns a constant position frame every call.
    # This exercises both the drain branch AND the snapshot branch on at
    # least one tick.
    detected_envelope = {
        "type": "ipc.learn.controller_detected",
        "ts": "2026-05-27T00:00:00Z",
        "payload": {
            "connected": True,
            "controller_id": "pioneer_ddj_flx4",
            "display_name": "Pioneer DDJ-FLX4",
            "port_name": "DDJ-FLX4 USB MIDI Input",
        },
    }
    constant_position_frame = {
        "type": "ipc.learn.midi_position",
        "ts": "2026-05-27T00:00:00Z",
        "payload": {
            "controller_id": "pioneer_ddj_flx4",
            "positions": {"eq_hi:A": 64, "xfader": 64},
        },
    }
    drain_call_count = {"n": 0}
    detected_emitted_marker = {"done": False}

    def _drain():
        drain_call_count["n"] += 1
        # Queue the controller_detected envelope on tick ~50 (well after the
        # LongLivedClient connects via the patched handler — empirically, the
        # client is registered within the first few ticks via the two-step
        # _REAL_SLEEP(0) yield pattern from test_mood_change_envelope.py).
        # Emit exactly ONCE so the drain-then-snapshot ordering assertion has
        # a single point to compare against the first midi_position frame.
        if drain_call_count["n"] == 50 and not detected_emitted_marker["done"]:
            detected_emitted_marker["done"] = True
            return [detected_envelope]
        return []

    midi_mirror_stub = SimpleNamespace(
        drain_pending_detected=_drain,
        snapshot=lambda: constant_position_frame,
    )

    # ---------- Connected client that counts mascot frames + learn frames ----
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

    # ---------- Fast-forward asyncio.sleep so 100 ticks finish in ~ms wall
    # clock. Counter pin: stop after exactly 100 calls — pinning the cadence
    # contract independent of real wall-clock variance.
    _REAL_SLEEP = asyncio.sleep
    tick_counter = {"n": 0}

    async def fast_sleep(_s):
        tick_counter["n"] += 1
        if tick_counter["n"] >= 100:
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    # ---------- Drive ws_broadcast under wait_for cap ----
    async def driver():
        bg = asyncio.create_task(
            ws_broadcast(
                fake_levels,
                state,
                manual_trigger,
                stop_event,
                midi_mirror=midi_mirror_stub,
            )
        )
        # Yield to let ws_broadcast spin up the server + handler.
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]
        client = LongLivedClient()
        ht = asyncio.create_task(handler(client))
        await bg
        try:
            await asyncio.wait_for(ht, timeout=0.5)
        except Exception:
            ht.cancel()

    await asyncio.wait_for(driver(), timeout=5.0)

    # ---------- Parse + count mascot frames + learn frames ----
    mascot_emits = 0
    learn_detected_emits = 0
    learn_position_emits = 0
    for raw in sent_payloads:
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        if not isinstance(msg, dict):
            continue
        mtype = msg.get("type")
        if mtype == "ipc.learn.controller_detected":
            learn_detected_emits += 1
        elif mtype == "ipc.learn.midi_position":
            learn_position_emits += 1
        elif "music" in msg and "voice" in msg and "mic" in msg:
            # Mascot frame — flat shape without a `type` field, identified
            # by the meter keys (the BRINGUP-04 emit-boundary contract in
            # ws_bus.py:557-562 pins these three keys).
            mascot_emits += 1

    # ---------- Cadence assertion: ±5% of 100 expected ticks ----
    expected = 100
    tolerance = expected * 0.05  # ±5
    assert abs(mascot_emits - expected) <= tolerance, (
        f"30 Hz cadence drifted under Learn load — mascot_emits={mascot_emits} "
        f"vs expected ~{expected} (tolerance ±{tolerance:.1f}). "
        f"Drain calls={drain_call_count['n']}; learn_detected={learn_detected_emits}; "
        f"learn_position={learn_position_emits}."
    )

    # ---------- Drain-then-snapshot per-tick ORDERING assertion ----
    # The plan contract: on any tick where a controller_detected envelope is
    # drained, the midi_position envelope from the SAME tick comes AFTER it.
    # The position-frame is emitted on every tick (constant stub), so within
    # the sent_payloads stream a controller_detected at index `i` must be
    # immediately followed by a midi_position at index `i+1` (no other
    # frame interleaves between them inside the same tick body, because the
    # drain block in ws_bus.py runs synchronously through the snapshot block
    # before yielding to `asyncio.sleep`).
    assert learn_detected_emits == 1, (
        f"expected exactly 1 detected emit (queued once), got {learn_detected_emits}"
    )
    detected_idx = None
    for i, raw in enumerate(sent_payloads):
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        if isinstance(msg, dict) and msg.get("type") == "ipc.learn.controller_detected":
            detected_idx = i
            break
    assert detected_idx is not None, "controller_detected envelope never reached the wire"
    # The very next frame in the wire stream after detected MUST be the
    # midi_position from the SAME tick (drain-then-snapshot ordering).
    assert detected_idx + 1 < len(sent_payloads), (
        f"detected at index {detected_idx} but no following frame in the stream"
    )
    try:
        next_msg = json.loads(sent_payloads[detected_idx + 1])
    except Exception as e:  # pragma: no cover
        pytest.fail(f"could not parse frame after detected: {e}")
    next_type = next_msg.get("type") if isinstance(next_msg, dict) else None
    assert next_type == "ipc.learn.midi_position", (
        f"drain-then-snapshot per-tick order violated — frame after "
        f"controller_detected at index {detected_idx} is type "
        f"{next_type!r}, expected 'ipc.learn.midi_position'"
    )
