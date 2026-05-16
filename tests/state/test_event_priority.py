# SPDX-License-Identifier: Apache-2.0
"""Plan 19-01 Task 1: Event.priority field + EVENT_PRIORITY default map.

The priority field is the deterministic ladder CancelGate reads to decide
whether a higher-priority incoming Event should preempt an in-flight one.
No string comparisons, no enum — just a plain int per CONTEXT D-04.
"""

from __future__ import annotations

import pytest

from vibemix.state import MusicState
from vibemix.state.event import EVENT_PRIORITY, Event


@pytest.fixture
def ms() -> MusicState:
    return MusicState()


def test_priority_default_mix_move(ms: MusicState) -> None:
    ev = Event(type="MIX_MOVE", state=ms)
    assert ev.priority == 5


def test_priority_default_heartbeat(ms: MusicState) -> None:
    ev = Event(type="HEARTBEAT", state=ms)
    assert ev.priority == 1


def test_priority_default_track_change(ms: MusicState) -> None:
    ev = Event(type="TRACK_CHANGE", state=ms)
    assert ev.priority == 7


def test_priority_default_phase(ms: MusicState) -> None:
    ev = Event(type="PHASE", state=ms)
    assert ev.priority == 6


def test_priority_default_layer_arrival(ms: MusicState) -> None:
    ev = Event(type="LAYER_ARRIVAL", state=ms)
    assert ev.priority == 4


def test_priority_default_kaan_spoke(ms: MusicState) -> None:
    """Kaan's voice always wins over passive music events."""
    ev = Event(type="KAAN_SPOKE", state=ms)
    assert ev.priority == 9


def test_priority_default_manual(ms: MusicState) -> None:
    """Manual trigger is the user-issued ceiling."""
    ev = Event(type="MANUAL", state=ms)
    assert ev.priority == 10


def test_priority_default_drop_reserved(ms: MusicState) -> None:
    """Phase 17 reserves DROP — pre-wire the slot per CONTEXT D-04 ladder."""
    ev = Event(type="DROP", state=ms)
    assert ev.priority == 10


def test_priority_default_unknown_type(ms: MusicState) -> None:
    """Unknown type → priority 0 (lowest; never preempts)."""
    ev = Event(type="WHO_KNOWS", state=ms)
    assert ev.priority == 0


def test_priority_explicit_override_wins(ms: MusicState) -> None:
    """Explicit non-zero priority kwarg bypasses the EVENT_PRIORITY lookup."""
    ev = Event(type="MIX_MOVE", state=ms, priority=99)
    assert ev.priority == 99


def test_priority_is_plain_int_for_comparison(ms: MusicState) -> None:
    """Two Events comparable via a.priority > b.priority cleanly."""
    a = Event(type="MANUAL", state=ms)
    b = Event(type="HEARTBEAT", state=ms)
    assert a.priority > b.priority
    assert isinstance(a.priority, int)
    assert isinstance(b.priority, int)


def test_event_priority_map_is_module_constant() -> None:
    """EVENT_PRIORITY exported from vibemix.state.event as a dict[str, int]."""
    assert isinstance(EVENT_PRIORITY, dict)
    assert EVENT_PRIORITY["MANUAL"] == 10
    assert EVENT_PRIORITY["DROP"] == 10
    assert EVENT_PRIORITY["KAAN_SPOKE"] == 9
    assert EVENT_PRIORITY["TRACK_CHANGE"] == 7
    assert EVENT_PRIORITY["PHASE"] == 6
    assert EVENT_PRIORITY["MIX_MOVE"] == 5
    assert EVENT_PRIORITY["LAYER_ARRIVAL"] == 4
    assert EVENT_PRIORITY["HEARTBEAT"] == 1
