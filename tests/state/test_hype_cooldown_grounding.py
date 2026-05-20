# SPDX-License-Identifier: Apache-2.0
"""LIVE-03 — cooldown respect + in-bar tolerance baseline (Phase 54 Plan 02).

PINS three things with the REAL EventDetector + a patched clock:

(a) Cooldowns GATE without DEAFENING — a consecutive same-type (PHASE) event
    INSIDE the per-type cooldown does NOT double-fire, and a same-type event
    AFTER the cooldown window DOES fire. The "let the music breathe" cooldown
    keeps spacing without dropping the next real moment.

(b) IN_BAR_TOLERANCE_S is the named, one-line-editable in-bar reaction-timing
    knob — pinned to 2.0 (the value Plan 01's trace-replay uses) and asserted
    inside a sane bar-length band (0 < x <= 2.5, i.e. <= ~1 bar at 100 BPM).
    A tuning change is then a visible one-line diff.

(c) The v4-tuned cooldown VALUES are pinned as the baseline so any future
    re-tune is a deliberate, visible diff (data-driven from a --print-cooldowns
    delta, not vibes). This plan does NOT change any cooldown value.
"""

from __future__ import annotations

from vibemix.audio.constants import (
    EVENT_GLOBAL_MIN_GAP,
    HEARTBEAT_SEC,
    IN_BAR_TOLERANCE_S,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state import EventDetector, MusicState


def _state(*, audible: bool = True, bpm: float = 130.0, phase: str = "groove") -> MusicState:
    ms = MusicState()
    ms.audible = audible
    ms.bpm = bpm
    ms.phase = phase
    ms.bands = {"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2}
    ms.rms = 0.06
    return ms


def _patch_time(mocker, value: float):
    return mocker.patch("vibemix.state.event_detector.time.time", return_value=value)


# --------------------------------------------------------------------------- #
# (a) Cooldown gates without deafening                                        #
# --------------------------------------------------------------------------- #


def test_phase_cooldown_blocks_double_fire_then_fires_after_window(mocker):
    """A PHASE fire at t0; a second PHASE transition INSIDE the cooldown window
    returns None (cooldown gates the double-fire); a PHASE transition AFTER the
    window fires (cooldown gates, it doesn't deafen).

    PHASE per-type gap = 10.0; EVENT_GLOBAL_MIN_GAP = 10.0 — _cooldown_ok needs
    BOTH to elapse. So the "after" tick must clear max(PHASE gap, global) + a
    margin.
    """
    phase_gap = MIN_EVENT_GAP_PER_TYPE["PHASE"]
    t0 = 1000.0

    d = EventDetector()
    # Seed the music-presence gate without polluting change refs (set
    # _audible_since directly), and seed last_phase so the FIRST transition is
    # real (groove -> drop).
    d._audible_since = t0 - 5.0
    d.last_phase = "groove"

    # Fire 1 — PHASE at t0.
    _patch_time(mocker, t0)
    ev1 = d.detect(_state(phase="drop"), kaan_just_spoke=False, manual=False)
    assert ev1 is not None and ev1.type == "PHASE"

    # Inside the cooldown — flip phase again; cooldown blocks the double-fire.
    t_inside = t0 + (phase_gap - 0.5)
    _patch_time(mocker, t_inside)
    ev2 = d.detect(_state(phase="build"), kaan_just_spoke=False, manual=False)
    assert ev2 is None, "PHASE double-fired inside the cooldown window"

    # After both per-type AND global windows clear — a real PHASE transition
    # fires again (cooldowns gate, they don't deafen).
    t_after = t0 + max(phase_gap, EVENT_GLOBAL_MIN_GAP) + 0.5
    _patch_time(mocker, t_after)
    # last_phase is now "build" (updated on the blocked tick); flip to "peak".
    ev3 = d.detect(_state(phase="peak"), kaan_just_spoke=False, manual=False)
    assert ev3 is not None and ev3.type == "PHASE", (
        "PHASE did not re-fire after the cooldown window — cooldown deafened"
    )
    assert ev3.extra["new_phase"] == "peak"


# --------------------------------------------------------------------------- #
# (b) IN_BAR_TOLERANCE_S pin + sane band                                      #
# --------------------------------------------------------------------------- #


def test_in_bar_tolerance_matches_trace_replay_value():
    """IN_BAR_TOLERANCE_S equals the value Plan 01's trace-replay uses (2.0)
    so the two Wave-1 plans stay consistent — a tuning change is then a visible
    diff in both the constant and this assertion."""
    assert IN_BAR_TOLERANCE_S == 2.0


def test_in_bar_tolerance_is_in_sane_bar_length_band():
    """0 < IN_BAR_TOLERANCE_S <= 2.5 — a positive tolerance no wider than ~1 bar
    at 100 BPM (4 * 60/100 = 2.4s). Catches an accidental fat-finger re-tune
    that would let reactions land arbitrarily late."""
    assert 0 < IN_BAR_TOLERANCE_S <= 2.5


# --------------------------------------------------------------------------- #
# (c) v4 cooldown baseline pin                                                #
# --------------------------------------------------------------------------- #


def test_v4_cooldown_baseline_values_are_pinned():
    """The v4-tuned cooldown VALUES are the locked baseline. Any future re-tune
    must be a deliberate, visible diff (data-driven from a --print-cooldowns
    delta), not an accidental edit. Plan 54-02 changes NONE of these."""
    assert MIN_EVENT_GAP_PER_TYPE["PHASE"] == 10.0
    assert MIN_EVENT_GAP_PER_TYPE["MIX_MOVE"] == 14.0
    assert MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"] == 10.0
    assert MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"] == 5.0
    assert EVENT_GLOBAL_MIN_GAP == 10.0
    assert HEARTBEAT_SEC == 45.0
    # HEARTBEAT per-type gap flows from HEARTBEAT_SEC.
    assert MIN_EVENT_GAP_PER_TYPE["HEARTBEAT"] == HEARTBEAT_SEC
