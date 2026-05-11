# SPDX-License-Identifier: Apache-2.0
"""Event dataclass smoke — 3 fields + default_factory not shared."""

from __future__ import annotations

from vibemix.state import Event, MusicState


def test_event_imports_from_package():
    from vibemix.state import Event as Ev  # noqa: F401


def test_event_constructs_with_defaults():
    ms = MusicState()
    ev = Event(type="HEARTBEAT", state=ms)
    assert ev.type == "HEARTBEAT"
    assert ev.state is ms
    assert ev.extra == {}


def test_event_carries_extra():
    ms = MusicState()
    ev = Event(type="TRACK_CHANGE", state=ms, extra={"prev_track": "X", "new_track": "Y"})
    assert ev.extra == {"prev_track": "X", "new_track": "Y"}


def test_event_extra_default_factory_not_shared():
    ms = MusicState()
    e1 = Event(type="HEARTBEAT", state=ms)
    e2 = Event(type="HEARTBEAT", state=ms)
    assert e1.extra is not e2.extra
