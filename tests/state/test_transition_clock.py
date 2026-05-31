# SPDX-License-Identifier: Apache-2.0
"""The drop-timing oracle — pins the scar-20 (AutoDJ) plan algebra clean-room.

``state/transition_clock.py`` is the deterministic 15 Hz drop-timing spine of the
viral co-host vertical: it reduces a whole transition to three normalized
fractions + one monotonic ``transition_progress`` scalar the co-host phrase-locks
to. It is a PURE leaf — ``calculate_transition`` takes ``TrackCues`` as input
(the caller fills them from vibemix's own analyzer), reaches into no audio engine,
and depends only on the committed grid/numpy stack.

Oracles are hand-derived from ``scars/20-autodj-transitions.md`` §3.4 worked
values so the algebra is pinned independent of the implementation.
"""
from __future__ import annotations

import math

from vibemix.state.transition_clock import (
    GRID_HZ,
    SILENCE_THRESHOLD,
    TrackCues,
    TransitionMode,
    TransitionPhase,
    calculate_transition,
    drop_eta_seconds,
    frame_to_seconds,
    snap_to_update_grid,
    step_progress,
    transition_phase,
)


def _phase_edges(plan, positions_sec, *, arm_lead_sec=2.0):
    """Drive the tracker across a fromDeck position trace; return the ordered list
    of phase EDGES (a new phase is fired only when ``phase > prev_phase``)."""
    prev_phase = TransitionPhase.IDLE
    prev_progress = 0.0
    edges: list[TransitionPhase] = []
    for pos_sec in positions_sec:
        frac = snap_to_update_grid(pos_sec) / plan.from_duration_sec
        phase, prev_progress = transition_phase(
            plan, frac, prev_phase, prev_progress=prev_progress, arm_lead_sec=arm_lead_sec
        )
        if phase > prev_phase:
            edges.append(phase)
        prev_phase = phase
    return edges


# --- frame_to_seconds: rate-aware cue conversion (§3.1) ---------------------
def test_frame_to_seconds_rate_aware() -> None:
    # one second of frames at the sample rate -> 1.0 s at normal speed
    assert math.isclose(frame_to_seconds(44100, 44100), 1.0, rel_tol=1e-12)
    # a sped-up track (rate 2.0) has proportionally EARLIER cues -> half the seconds
    assert math.isclose(frame_to_seconds(44100, 44100, 2.0), 0.5, rel_tol=1e-12)
    # fail-safe guards: None / negative frame / bad sample-rate / bad rate -> 0.0
    assert frame_to_seconds(None, 44100) == 0.0
    assert frame_to_seconds(-5, 44100) == 0.0
    assert frame_to_seconds(44100, 0) == 0.0
    assert frame_to_seconds(44100, 44100, 0.0) == 0.0


# --- constants (scar 20 §2) -------------------------------------------------
def test_scar_constants_are_byte_exact() -> None:
    assert GRID_HZ == 15  # kPlaypositionUpdateRate (enginebuffer.cpp:52)
    assert SILENCE_THRESHOLD == 0.001  # 10**(-60/20) (analyzersilence.cpp:11)
    # the -60 dB threshold MUST equal the closed-form, not a rounded literal
    assert math.isclose(SILENCE_THRESHOLD, 10.0 ** (-60.0 / 20.0), rel_tol=1e-12)


# --- Mode 0 FullIntroOutro: the worked oracle -------------------------------
def test_full_intro_outro_worked_plan() -> None:
    # from: 240 s track, outro marked 200..220; to: 180 s, intro marked 0..16; tt=10.
    # Hand-derived (§3.4): fade_begin = (outro_end - intro_len)/dur = (220-16)/240.
    from_cues = TrackCues(
        duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0,
    )
    to_cues = TrackCues(
        duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0,
        outro_start_sec=160.0, outro_end_sec=175.0,
    )
    plan = calculate_transition(
        from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0,
    )
    assert math.isclose(plan.from_fade_begin, 204.0 / 240.0, rel_tol=1e-9)  # 0.85
    assert math.isclose(plan.from_fade_end, 220.0 / 240.0, rel_tol=1e-9)  # 0.916666…
    assert math.isclose(plan.to_start, 0.0, abs_tol=1e-9)
    assert plan.is_cut is False
    assert plan.crossfader_start_center is False


# --- hard-cut sentinel: transition_sec == 0 ⇒ fadeBegin >= fadeEnd ----------
def test_zero_transition_is_a_hard_cut() -> None:
    # tt==0 forces the use_fixed_fade_time else-branch: begin == end == fade_end.
    cues = TrackCues(duration_sec=200.0)
    plan = calculate_transition(
        cues, cues, mode=TransitionMode.FIXED_FULL_TRACK, transition_sec=0.0,
    )
    assert plan.is_cut is True
    assert plan.from_fade_begin >= plan.from_fade_end
    assert math.isclose(plan.from_fade_begin, 1.0, abs_tol=1e-9)


# --- fractions always in [0,1], fadeBegin clamped to 1.0 --------------------
def test_plan_fractions_bounded() -> None:
    cues = TrackCues(duration_sec=120.0, outro_start_sec=100.0, outro_end_sec=118.0)
    plan = calculate_transition(
        cues, cues, mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=8.0,
    )
    for frac in (plan.from_fade_begin, plan.from_fade_end, plan.to_start):
        assert 0.0 <= frac <= 1.0


# --- cue-ladder sentinels (§3.2) --------------------------------------------
def test_intro_sentinel_no_intro_when_start_equals_end() -> None:
    # introEnd == introStart is the "no intro marked" sentinel: zero intro length,
    # so FullIntroOutro must fall back to the fixed fade (no intro to ride).
    from_cues = TrackCues(duration_sec=200.0, outro_start_sec=180.0, outro_end_sec=195.0)
    to_cues = TrackCues(
        duration_sec=200.0, intro_start_sec=10.0, intro_end_sec=10.0,  # sentinel
    )
    plan = calculate_transition(
        from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0,
    )
    # outro_length (15) rides; with no intro, tlen = outro_length = 15 -> begin at
    # outro_end - 15 = 180/200 = 0.9.
    assert math.isclose(plan.from_fade_begin, 0.9, rel_tol=1e-9)
    assert math.isclose(plan.from_fade_end, 195.0 / 200.0, rel_tol=1e-9)


def test_unmarked_outro_falls_back_to_last_sound() -> None:
    # No outro markers -> outro_end resolves to last_sound (-60 dB), not track end.
    from_cues = TrackCues(duration_sec=200.0, last_sound_sec=190.0)
    to_cues = TrackCues(duration_sec=200.0, intro_start_sec=0.0, intro_end_sec=12.0)
    plan = calculate_transition(
        from_cues, to_cues, mode=TransitionMode.FADE_AT_OUTRO_START, transition_sec=10.0,
    )
    # fade must end no later than the last audible sample (190/200 = 0.95).
    assert plan.from_fade_end <= 190.0 / 200.0 + 1e-9


# --- step_progress: monotonic, reset, freeze-on-backward, clamp -------------
def test_step_progress_monotonic_trace() -> None:
    cues_from = TrackCues(duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0)
    cues_to = TrackCues(duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0)
    plan = calculate_transition(
        cues_from, cues_to, mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0,
    )
    b, e = plan.from_fade_begin, plan.from_fade_end  # 0.85 .. 0.91667

    # before the trigger -> 0.0 (reset state)
    assert step_progress(plan, b - 0.02, 0.0) == 0.0
    # at trigger -> 0.0
    assert step_progress(plan, b, 0.0) == 0.0
    # halfway -> ~0.5
    mid = (b + e) / 2.0
    p_mid = step_progress(plan, mid, 0.0)
    assert math.isclose(p_mid, 0.5, abs_tol=0.02)
    # at/after fade end -> clamps to 1.0
    assert step_progress(plan, e, p_mid) == 1.0
    assert step_progress(plan, e + 0.05, 1.0) == 1.0
    # backward seek freezes (monotonic): feeding an earlier pos keeps prev
    assert step_progress(plan, b + 0.001, p_mid) == p_mid


def test_step_progress_full_trace_is_non_decreasing() -> None:
    cues = TrackCues(duration_sec=120.0, outro_start_sec=96.0, outro_end_sec=114.0)
    plan = calculate_transition(
        cues, cues, mode=TransitionMode.FADE_AT_OUTRO_START, transition_sec=12.0,
    )
    prev = 0.0
    trace = []
    # sample the fromDeck position across the fade on the 15 Hz grid
    for i in range(0, int(GRID_HZ * 120) + 1):
        t = i / GRID_HZ
        pos_frac = snap_to_update_grid(t) / plan.from_duration_sec
        prev = step_progress(plan, pos_frac, prev)
        trace.append(prev)
    assert all(b >= a - 1e-12 for a, b in zip(trace, trace[1:]))  # non-decreasing
    assert trace[-1] == 1.0  # fully landed by track end


def test_determinism_same_inputs_bit_identical() -> None:
    cues = TrackCues(duration_sec=200.0, outro_start_sec=170.0, outro_end_sec=190.0)
    kw = dict(mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0)
    a = calculate_transition(cues, cues, **kw)
    b = calculate_transition(cues, cues, **kw)
    assert (a.from_fade_begin, a.from_fade_end, a.to_start) == (
        b.from_fade_begin, b.from_fade_end, b.to_start
    )


# --- drop_eta_seconds -------------------------------------------------------
def test_drop_eta_counts_down_to_the_trigger() -> None:
    cues = TrackCues(duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0)
    plan = calculate_transition(
        cues, TrackCues(duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0),
        mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0,
    )
    # fade begins at 0.85 * 240 = 204 s. At pos 0.80 -> 0.05*240 = 12 s out.
    assert math.isclose(drop_eta_seconds(plan, 0.80), (0.85 - 0.80) * 240.0, rel_tol=1e-9)
    # past the trigger -> negative (already dropping)
    assert drop_eta_seconds(plan, 0.90) < 0.0


def test_snap_to_update_grid_floors_to_15hz() -> None:
    # 66.7 ms granularity: anything inside a grid cell floors to the cell start.
    assert math.isclose(snap_to_update_grid(0.10), round(math.floor(0.10 * 15) / 15, 12), abs_tol=1e-12)
    assert snap_to_update_grid(0.0) == 0.0
    # two times within the same 1/15 s cell snap identically (the determinism floor)
    assert snap_to_update_grid(0.20) == snap_to_update_grid(0.20 + 0.001)


# --- transition_phase: armed -> fading -> landed edge machine ----------------
def _fade_plan():
    return calculate_transition(
        TrackCues(duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0),
        TrackCues(duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0),
        mode=TransitionMode.FULL_INTRO_OUTRO, transition_sec=10.0,
    )  # fade 204..220 s of a 240 s track (begin 0.85)


def test_phase_progression_fade_fires_armed_fading_landed() -> None:
    plan = _fade_plan()
    # sweep the fromDeck from well before the arm window to past the fade end
    trace = [200.0 + i / GRID_HZ for i in range(0, int(GRID_HZ * 24))]  # 200..224 s
    edges = _phase_edges(plan, trace, arm_lead_sec=2.0)
    assert edges == [TransitionPhase.ARMED, TransitionPhase.FADING, TransitionPhase.LANDED]


def test_phase_progression_cut_skips_fading() -> None:
    # A hard cut has no ramp -> armed then straight to landed (never "smooth blend").
    cut = calculate_transition(
        TrackCues(duration_sec=200.0), TrackCues(duration_sec=200.0),
        mode=TransitionMode.FIXED_FULL_TRACK, transition_sec=0.0,
    )
    trace = [196.0 + i / GRID_HZ for i in range(0, int(GRID_HZ * 5))]  # 196..201 s, crosses end
    edges = _phase_edges(cut, trace, arm_lead_sec=2.0)
    assert edges == [TransitionPhase.ARMED, TransitionPhase.LANDED]
    assert TransitionPhase.FADING not in edges


def test_phase_no_arm_when_drop_too_far() -> None:
    plan = _fade_plan()  # fade begins at 204 s
    # at 200 s the drop is 4 s out; with a 2 s arm-lead the co-host must stay IDLE
    frac = 200.0 / plan.from_duration_sec
    phase, _ = transition_phase(plan, frac, TransitionPhase.IDLE, prev_progress=0.0, arm_lead_sec=2.0)
    assert phase == TransitionPhase.IDLE


def test_phase_is_monotonic_no_regress_on_backward_seek() -> None:
    plan = _fade_plan()
    b = plan.from_fade_begin
    # advance to FADING mid-fade
    mid = (plan.from_fade_begin + plan.from_fade_end) / 2.0
    phase, prog = transition_phase(plan, mid, TransitionPhase.ARMED, prev_progress=0.0, arm_lead_sec=2.0)
    assert phase == TransitionPhase.FADING
    # a backward seek to just past the trigger must NOT drop back to ARMED/IDLE
    phase2, _ = transition_phase(plan, b + 1e-4, phase, prev_progress=prog, arm_lead_sec=2.0)
    assert phase2 == TransitionPhase.FADING


def test_phase_no_landed_before_fading_in_a_real_fade() -> None:
    plan = _fade_plan()
    trace = [200.0 + i / GRID_HZ for i in range(0, int(GRID_HZ * 24))]
    prev_phase = TransitionPhase.IDLE
    prev_progress = 0.0
    saw_fading = False
    for pos_sec in trace:
        frac = snap_to_update_grid(pos_sec) / plan.from_duration_sec
        phase, prev_progress = transition_phase(
            plan, frac, prev_phase, prev_progress=prev_progress, arm_lead_sec=2.0
        )
        if phase == TransitionPhase.FADING:
            saw_fading = True
        if phase == TransitionPhase.LANDED:
            assert saw_fading, "a real fade must pass through FADING before LANDED"
        prev_phase = phase
