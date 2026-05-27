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
from types import SimpleNamespace

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


# Marked async via pytest-anyio (the repo's canonical async-test plugin —
# see ``tests/debrief/test_ws_server_progressive_emit.py`` for precedent).
@pytest.mark.anyio("asyncio")
async def test_30hz_cadence_holds_with_midi_mirror_kwarg() -> None:
    """Drive ``ws_broadcast`` for ~100 ticks (~3.3 s simulated, capped at 5 s
    wall-clock via ``asyncio.wait_for``) with a fake MidiMirror that returns
    a constant snapshot every call. Assert the mascot-frame emit count is
    within ±5% of 100 — pinning RESEARCH §Assumption A1.

    SKIPS until Plan 03 lands the ``midi_mirror`` kwarg in
    ``ws_broadcast``.
    """
    # Per-test importorskip — keeps the test collectable today (1 item)
    # but cleanly skips until Plan 03 lands both pieces.
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

    # Fake MidiMirror — `.snapshot()` returns a constant LearnMidiPosition
    # dict every call, simulating "controller present, no movement" so the
    # delta-suppression branch in MidiMirror itself isn't exercised here;
    # this test pins WS_BROADCAST behaviour under the extra per-tick call.
    constant_frame = {
        "type": "ipc.learn.midi_position",
        "ts": "2026-05-27T00:00:00Z",
        "payload": {
            "controller_id": "pioneer_ddj_flx4",
            "positions": {"eq_hi:A": 64, "xfader": 64},
        },
    }

    midi_mirror_stub = SimpleNamespace(
        snapshot=lambda: constant_frame,
    )

    # The exact harness implementation depends on the Plan 03 wiring shape
    # (kwarg name, ws_broadcast signature, mascot-frame emit accounting).
    # The plan executor for Plan 03 fills this in — for now the test simply
    # documents the contract via the assertion below; the assertion itself
    # never runs because the early-skip above gates the body.
    raise pytest.skip.Exception(
        "Plan 91-03 fills in the harness body; see RESEARCH §Code Example 6 "
        "for the midi_mirror kwarg signature."
    )

    # Asserted contract (lifted out of the unreachable harness body for
    # documentation; flip the skip to a real harness in Plan 03):
    # ----------------------------------------------------------------------
    # tick_count = 100
    # expected = 100
    # tolerance = expected * 0.05  # ±5%
    # mascot_emits = run_ws_broadcast_for_n_ticks(
    #     tick_count, midi_mirror=midi_mirror_stub, wall_clock_cap_s=5.0,
    # )
    # assert abs(mascot_emits - expected) <= tolerance, (
    #     f"30 Hz cadence drifted under Learn load — mascot_emits={mascot_emits} "
    #     f"vs expected ~{expected} (tolerance ±{tolerance:.1f})"
    # )
    # ----------------------------------------------------------------------
    _ = asyncio  # mark imported (skip path)
