# SPDX-License-Identifier: Apache-2.0
"""The auto-mix demo reel — the owned-deck viral vertical, headless + deterministic.

``build_automix_reel`` composes the scar-20 transition clock + phase tracker into a
single artifact: given two tracks' cues, it steps an owned mix across the fromDeck
at 15 Hz and emits the phrase-locked reaction beats (armed → mixing-in → landed)
the co-host speaks ON the drop. This is the data-available home for the clock (the
live co-host has no playposition/cues; an owned MiniDeck does), and the headless
reel is the deterministic core the audio/waveform/TTS layers render.

The jump-cut distinction (rank 27) is folded in: a hard cut never emits the
"mixing in" blend beat — it slams straight to landed, so the co-host never narrates
a smooth blend over a cut.
"""
from __future__ import annotations

from vibemix.runtime.automix_demo import (
    AutomixReel,
    DemoBeat,
    build_automix_reel,
    reaction_cue,
)
from vibemix.state.transition_clock import (
    TrackCues,
    TransitionMode,
    TransitionPhase,
)


def _cues_pair():
    from_cues = TrackCues(duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0)
    to_cues = TrackCues(duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0)
    return from_cues, to_cues


def test_blend_reel_fires_armed_mixing_landed_in_order() -> None:
    from_cues, to_cues = _cues_pair()  # fade 204..220 s of a 240 s track
    reel = build_automix_reel(
        from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO,
        transition_sec=10.0, arm_lead_sec=2.0,
    )
    assert isinstance(reel, AutomixReel)
    phases = [b.phase for b in reel.beats]
    cues = [b.cue for b in reel.beats]
    assert phases == [TransitionPhase.ARMED, TransitionPhase.FADING, TransitionPhase.LANDED]
    assert cues == ["drop_incoming", "mixing_in", "landed_clean"]
    assert reel.is_cut is False


def test_reel_beats_land_on_the_real_fade_window() -> None:
    from_cues, to_cues = _cues_pair()
    reel = build_automix_reel(
        from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO,
        transition_sec=10.0, arm_lead_sec=2.0,
    )
    by_phase = {b.phase: b for b in reel.beats}
    # armed ~2 s (arm_lead) before the 204 s trigger; fading at/just past 204 s;
    # landed at the 220 s fade end. Allow one 15 Hz tick (~0.067 s) of grid jitter.
    assert abs(by_phase[TransitionPhase.ARMED].t_sec - 202.0) <= 0.2
    assert 204.0 - 0.1 <= by_phase[TransitionPhase.FADING].t_sec <= 204.0 + 0.2
    assert abs(by_phase[TransitionPhase.LANDED].t_sec - 220.0) <= 0.2


def test_hard_cut_reel_never_emits_a_blend_beat() -> None:
    cut_cues = TrackCues(duration_sec=200.0)
    reel = build_automix_reel(
        cut_cues, cut_cues, mode=TransitionMode.FIXED_FULL_TRACK,
        transition_sec=0.0, arm_lead_sec=2.0,
    )
    assert reel.is_cut is True
    cues = [b.cue for b in reel.beats]
    assert "mixing_in" not in cues  # never narrate a smooth blend over a cut
    assert cues == ["drop_incoming", "slammed_cut"]
    assert TransitionPhase.FADING not in [b.phase for b in reel.beats]


def test_reel_is_deterministic() -> None:
    from_cues, to_cues = _cues_pair()
    kw = dict(mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0, arm_lead_sec=2.0)
    a = build_automix_reel(from_cues, to_cues, **kw)
    b = build_automix_reel(from_cues, to_cues, **kw)
    assert [(x.t_sec, x.phase, x.cue) for x in a.beats] == [
        (y.t_sec, y.phase, y.cue) for y in b.beats
    ]


def test_beats_are_strictly_time_ordered_and_monotonic_phase() -> None:
    from_cues, to_cues = _cues_pair()
    reel = build_automix_reel(
        from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO,
        transition_sec=10.0, arm_lead_sec=2.0,
    )
    times = [b.t_sec for b in reel.beats]
    phases = [int(b.phase) for b in reel.beats]
    assert times == sorted(times)
    assert all(b > a for a, b in zip(phases, phases[1:]))  # strictly advancing phase
    assert all(isinstance(b, DemoBeat) for b in reel.beats)


def test_reaction_cue_center_start_is_a_slam_not_a_blend() -> None:
    # mode-4 center-start slams the incoming intro in at full volume — a distinct,
    # punchy beat, not a smooth blend (scar 20 §4.5). reaction_cue distinguishes it.
    assert reaction_cue(TransitionPhase.FADING, is_cut=False, center_start=False) == "mixing_in"
    assert reaction_cue(TransitionPhase.FADING, is_cut=False, center_start=True) == "slam_in"
    assert reaction_cue(TransitionPhase.LANDED, is_cut=True, center_start=False) == "slammed_cut"
    assert reaction_cue(TransitionPhase.LANDED, is_cut=False, center_start=False) == "landed_clean"
    assert reaction_cue(TransitionPhase.ARMED, is_cut=False, center_start=False) == "drop_incoming"
