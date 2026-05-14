# SPDX-License-Identifier: Apache-2.0
"""Plan 19-01 Task 2: CancelGate — single chokepoint for SpeechHandle.interrupt.

Three gates in order: priority ladder → 8s hard cooldown → 30/session soft cap
with auto-disable. Telemetry callback fires exactly once on soft-cap breach.

Time is driven by an injected ``time_fn`` so tests advance the clock by hand
— no monkeypatching of ``time.monotonic``, no real sleeps.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vibemix.runtime.cancel import (
    CANCEL_COOLDOWN_S,
    CANCEL_SOFT_CAP,
    CancelGate,
)
from vibemix.state import MusicState
from vibemix.state.event import Event


# ---------------------------------------------------------------- helpers


class FakeClock:
    """Caller-driven monotonic clock for deterministic cooldown tests."""

    def __init__(self, t0: float = 1000.0) -> None:
        self.t = t0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


@pytest.fixture
def ms() -> MusicState:
    return MusicState()


@pytest.fixture
def handle() -> MagicMock:
    """SpeechHandle stub — only ``interrupt`` is exercised."""
    h = MagicMock()
    h.interrupt = MagicMock()
    return h


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def gate(clock: FakeClock) -> CancelGate:
    return CancelGate(time_fn=clock)


# ---------------------------------------------------------------- module constants


def test_module_constants_match_d04_lock() -> None:
    assert CANCEL_COOLDOWN_S == 8.0
    assert CANCEL_SOFT_CAP == 30


# ---------------------------------------------------------------- priority gate


def test_priority_gate_blocks_when_incoming_lte_in_flight(
    gate: CancelGate, handle: MagicMock, ms: MusicState
) -> None:
    """incoming.priority <= in_flight.priority → no cancel."""
    incoming = Event(type="HEARTBEAT", state=ms)  # 1
    in_flight = Event(type="MIX_MOVE", state=ms)  # 5

    reason: list[str] = []
    fired = gate.try_cancel(handle, incoming, in_flight, reason_out=reason)

    assert fired is False
    assert reason == ["priority"]
    handle.interrupt.assert_not_called()
    assert gate.cancel_count == 0


def test_priority_gate_passes_when_incoming_strictly_higher(
    gate: CancelGate, handle: MagicMock, ms: MusicState
) -> None:
    """incoming.priority > in_flight.priority → cancel fires with force=True."""
    incoming = Event(type="MANUAL", state=ms)  # 10
    in_flight = Event(type="MIX_MOVE", state=ms)  # 5

    fired = gate.try_cancel(handle, incoming, in_flight)

    assert fired is True
    handle.interrupt.assert_called_once_with(force=True)
    assert gate.cancel_count == 1


def test_priority_gate_blocks_on_equal_priority(
    gate: CancelGate, handle: MagicMock, ms: MusicState
) -> None:
    """Equal priority must NOT preempt — only strictly-higher wins."""
    incoming = Event(type="MANUAL", state=ms)  # 10
    in_flight = Event(type="DROP", state=ms)  # 10

    fired = gate.try_cancel(handle, incoming, in_flight)

    assert fired is False
    handle.interrupt.assert_not_called()


# ---------------------------------------------------------------- cooldown gate


def test_cooldown_blocks_within_8s_window(
    gate: CancelGate, handle: MagicMock, clock: FakeClock, ms: MusicState
) -> None:
    """Synthetic 4-cancel-in-2s burst: only the first fires."""
    incoming = Event(type="MANUAL", state=ms)
    in_flight = Event(type="MIX_MOVE", state=ms)

    # Burst: first fires at t=1000.
    assert gate.try_cancel(handle, incoming, in_flight) is True
    # Three more within 2s — all blocked by cooldown.
    for _ in range(3):
        clock.advance(0.5)
        reason: list[str] = []
        fired = gate.try_cancel(handle, incoming, in_flight, reason_out=reason)
        assert fired is False
        assert reason == ["cooldown"]

    assert handle.interrupt.call_count == 1
    assert gate.cancel_count == 1


def test_cooldown_clears_after_8s(
    gate: CancelGate, handle: MagicMock, clock: FakeClock, ms: MusicState
) -> None:
    incoming = Event(type="MANUAL", state=ms)
    in_flight = Event(type="MIX_MOVE", state=ms)

    assert gate.try_cancel(handle, incoming, in_flight) is True
    clock.advance(7.99)
    assert gate.try_cancel(handle, incoming, in_flight) is False  # cooldown

    clock.advance(0.02)  # now 8.01s past the first cancel
    assert gate.try_cancel(handle, incoming, in_flight) is True

    assert handle.interrupt.call_count == 2
    assert gate.cancel_count == 2


# ---------------------------------------------------------------- soft-cap gate


def test_soft_cap_fires_at_30_then_blocks(
    gate: CancelGate, handle: MagicMock, clock: FakeClock, ms: MusicState
) -> None:
    """31-cancel burst, each spaced 9s: cancels 1-30 fire; #31 blocks
    with reason=soft_cap_breach. Subsequent attempts also blocked."""
    incoming = Event(type="MANUAL", state=ms)
    in_flight = Event(type="MIX_MOVE", state=ms)

    for i in range(CANCEL_SOFT_CAP):
        if i > 0:
            clock.advance(9.0)
        assert gate.try_cancel(handle, incoming, in_flight) is True, (
            f"cancel #{i + 1} should fire"
        )

    assert gate.cancel_count == CANCEL_SOFT_CAP
    assert handle.interrupt.call_count == CANCEL_SOFT_CAP

    # cancel #31 — soft-cap breach.
    clock.advance(9.0)
    reason: list[str] = []
    fired = gate.try_cancel(handle, incoming, in_flight, reason_out=reason)
    assert fired is False
    assert reason == ["soft_cap_breach"]
    assert gate.disabled is True

    # Subsequent attempts: stay disabled.
    for _ in range(9):
        clock.advance(9.0)
        reason2: list[str] = []
        fired2 = gate.try_cancel(handle, incoming, in_flight, reason_out=reason2)
        assert fired2 is False
        assert reason2 == ["disabled"]

    assert handle.interrupt.call_count == CANCEL_SOFT_CAP


# ---------------------------------------------------------------- telemetry


def test_telemetry_callback_fires_exactly_once_on_breach(
    handle: MagicMock, clock: FakeClock, ms: MusicState
) -> None:
    """telemetry_cb is invoked once when cancel #31 trips the soft cap;
    further blocked attempts do NOT re-fire it."""
    sink: list[dict] = []
    gate = CancelGate(time_fn=clock, telemetry_cb=sink.append)

    incoming = Event(type="MANUAL", state=ms)
    in_flight = Event(type="MIX_MOVE", state=ms)

    for i in range(CANCEL_SOFT_CAP):
        if i > 0:
            clock.advance(9.0)
        gate.try_cancel(handle, incoming, in_flight)

    assert sink == []  # not yet — only fires when the breach attempt happens

    clock.advance(9.0)
    gate.try_cancel(handle, incoming, in_flight)
    assert len(sink) == 1
    assert sink[0] == {"event": "cancel_soft_cap_breach", "count": CANCEL_SOFT_CAP}

    # Further blocked attempts → no additional telemetry.
    for _ in range(5):
        clock.advance(9.0)
        gate.try_cancel(handle, incoming, in_flight)
    assert len(sink) == 1


def test_handle_interrupt_called_with_force_true(
    gate: CancelGate, handle: MagicMock, ms: MusicState
) -> None:
    """The chokepoint contract: ``handle.interrupt(force=True)`` is the ONLY
    mutation against the SpeechHandle."""
    incoming = Event(type="MANUAL", state=ms)
    in_flight = Event(type="HEARTBEAT", state=ms)

    gate.try_cancel(handle, incoming, in_flight)

    handle.interrupt.assert_called_once_with(force=True)
    # No other method touched.
    handle.cancel.assert_not_called() if hasattr(handle, "cancel") else None


# ---------------------------------------------------------------- state accessors


def test_state_accessors_reflect_progress(
    gate: CancelGate, handle: MagicMock, clock: FakeClock, ms: MusicState
) -> None:
    incoming = Event(type="MANUAL", state=ms)
    in_flight = Event(type="MIX_MOVE", state=ms)

    assert gate.cancel_count == 0
    assert gate.disabled is False
    assert gate.last_cancel_at == 0.0

    gate.try_cancel(handle, incoming, in_flight)
    assert gate.cancel_count == 1
    assert gate.last_cancel_at == 1000.0

    clock.advance(9.0)
    gate.try_cancel(handle, incoming, in_flight)
    assert gate.cancel_count == 2
    assert gate.last_cancel_at == 1009.0
