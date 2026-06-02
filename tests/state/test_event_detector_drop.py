# SPDX-License-Identifier: Apache-2.0
"""DROP-call wiring — the EventDetector emits the reserved ``DROP`` event the
instant the audible deck's OWN predicted drop-countdown crosses into the arm
window, but ONLY when opted in (``VIBEMIX_DROP_CALL``). Dormant by default keeps
the v2.0 anti-slop firing gate closed: the prediction is computed every tick, the
spoken call never fires until a live operator flips the flag.
"""
from __future__ import annotations

import vibemix.state.event_detector as ed_mod
from vibemix.audio.constants import MIN_EVENT_GAP_PER_TYPE
from vibemix.state.event_detector import EventDetector
from vibemix.state.music_state import MusicState


def _playing_state(predicted: float | None) -> MusicState:
    """A MusicState that passes ``_music_truly_playing`` with a given drop ETA."""
    ms = MusicState()
    ms.audible = True
    ms.bpm = 130.0
    ms.audible_deck = "mix"
    ms.phase = "groove"
    ms.predicted_drop_in_sec = predicted
    return ms


def _tick(d: EventDetector, ms: MusicState, monkeypatch, *, t: float):
    """Run one detect() at wall-clock ``t`` with the music-presence gate satisfied
    and the earlier-priority PHASE/TRACK_CHANGE branches held steady."""
    monkeypatch.setattr(ed_mod.time, "time", lambda: t)
    d._audible_since = t - 100.0  # audible well past MUSIC_PRESENCE_MIN_SECONDS
    d.last_phase = ms.phase
    d.last_audible_track = ms.audible_track
    return d.detect(ms, kaan_just_spoke=False, manual=False)


def _suppress_heartbeat_fallback(d: EventDetector, *, t: float) -> None:
    """Keep this DROP-specific test from falling through to HEARTBEAT."""
    d.last_per_type_at["HEARTBEAT"] = t


def test_drop_fires_when_countdown_crosses_into_window(monkeypatch) -> None:
    d = EventDetector(drop_call_enabled=True)
    # tick 1: drop still 5s out (outside the 2s window) → primes prev, no DROP
    ev1 = _tick(d, _playing_state(5.0), monkeypatch, t=1000.0)
    assert ev1 is None or ev1.type != "DROP"
    # tick 2 (well clear of any tick-1 cooldown): now 1.5s out → crossed in → DROP
    ev2 = _tick(d, _playing_state(1.5), monkeypatch, t=1200.0)
    assert ev2 is not None and ev2.type == "DROP"
    assert ev2.extra["cue"] == "drop_incoming"
    assert ev2.extra["eta"] == 1.5
    assert ev2.priority == 10  # ties MANUAL at the ceiling (event.py EVENT_PRIORITY)


def test_no_drop_when_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_DROP_CALL", raising=False)
    d = EventDetector()  # reads env → off
    ev = _tick(d, _playing_state(1.0), monkeypatch, t=1000.0)
    assert ev is None or ev.type != "DROP"


def test_does_not_refire_while_still_inside_window(monkeypatch) -> None:
    d = EventDetector(drop_call_enabled=True)
    ev1 = _tick(d, _playing_state(1.5), monkeypatch, t=1000.0)  # fresh: prev None, inside → fires
    assert ev1 is not None and ev1.type == "DROP"
    ev2 = _tick(d, _playing_state(0.5), monkeypatch, t=1200.0)  # still inside → must NOT refire
    assert ev2 is None or ev2.type != "DROP"


def test_drop_has_type_specific_cooldown_between_separate_crossings(monkeypatch) -> None:
    d = EventDetector(drop_call_enabled=True)
    ev1 = _tick(d, _playing_state(1.5), monkeypatch, t=1000.0)
    assert ev1 is not None and ev1.type == "DROP"

    # Leave the arm window, then cross back in before the DROP-specific gap.
    assert _tick(d, _playing_state(5.0), monkeypatch, t=1010.0) is None
    _suppress_heartbeat_fallback(d, t=1023.0)
    too_soon = _tick(d, _playing_state(1.5), monkeypatch, t=1023.0)
    assert too_soon is None or too_soon.type != "DROP"

    # Leave again and cross back in just after the configured per-type gap.
    assert _tick(d, _playing_state(5.0), monkeypatch, t=1024.0) is None
    after_gap = 1000.0 + MIN_EVENT_GAP_PER_TYPE["DROP"] + 0.1
    ev2 = _tick(d, _playing_state(1.5), monkeypatch, t=after_gap)
    assert ev2 is not None and ev2.type == "DROP"


def test_env_flag_arms_without_explicit_kwarg(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_DROP_CALL", "1")
    d = EventDetector()  # picks up the env at construction (no __main__ change needed)
    assert d._drop_call_enabled is True
    ev = _tick(d, _playing_state(1.5), monkeypatch, t=1000.0)
    assert ev is not None and ev.type == "DROP"
