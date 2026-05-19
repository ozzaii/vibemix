# SPDX-License-Identifier: Apache-2.0
"""AICoach golden-string tests — every byte matters.

Pins the v4:1331-1433 output byte-for-byte. The MIX_MOVE 'do NOT name controls'
clause and the HEARTBEAT 'don't go silent' clause are LOAD-BEARING IP — tests
would catch any paraphrase or accidental tightening on a refactor.

The v4:1350-1351 anti-hallucination invariant (NO ``phase=`` in evidence_line)
is pinned by exclusion: a state with ``phase`` set to every non-silent label
is fed to evidence_line and the output is asserted to NOT contain ``phase=``.
"""

from __future__ import annotations

import inspect

from vibemix.state import AICoach, Event, MusicState

# ---------- Class shape ----------


def test_aicoach_imports_from_package():
    from vibemix.state import AICoach as AC  # noqa: F401


def test_aicoach_has_no_custom_init():
    """AICoach is static-method-only; no __init__ override means default
    object.__init__ is in effect."""
    assert AICoach.__init__ is object.__init__


def test_aicoach_three_public_methods():
    public = [n for n in dir(AICoach) if not n.startswith("_")]
    assert sorted(public) == ["build_prompt", "evidence_line", "task_for_event"]


def test_aicoach_methods_are_static():
    """All three callable surfaces are @staticmethod (no `self` binding)."""
    for name in ("evidence_line", "task_for_event", "build_prompt"):
        method = inspect.getattr_static(AICoach, name)
        assert isinstance(method, staticmethod), f"{name} must be @staticmethod"


# ---------- evidence_line: structural ----------


def test_evidence_line_silent_state_full_format():
    """Minimal silent state — exact byte-for-byte expected output."""
    state = MusicState()  # audible=False, no history, no moves
    out = AICoach.evidence_line(state)
    assert out == (
        "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
    )


def test_evidence_line_audible_block_format(mocker):
    """Pin the exact audible-block format from v4:1336-1339."""
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        audible_track="Daft Punk - Around the World",
        audible_track_confidence=0.6,
        audible_deck="A",
        set_start_at=755.0,  # now-set = 245s → 4:05
    )
    out = AICoach.evidence_line(state)
    # Substring tests for each component (in order):
    assert "hearing[rms=0.094 sub=0.20 low=0.30 mid=0.30 high=0.20 bpm=126]" in out
    assert "track='Daft Punk - Around the World'" in out
    assert "deck=A" in out
    assert "set_time=4:05" in out
    assert "recent_moves[8s]: NONE" in out


def test_evidence_line_track_unknown_below_03():
    """audible_track_confidence < 0.3 → 'track=unknown', title not quoted."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        bands={"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2},
        audible_track="X",
        audible_track_confidence=0.25,
    )
    out = AICoach.evidence_line(state)
    assert "track=unknown" in out
    assert "'X'" not in out


def test_evidence_line_track_quoted_at_exact_03_boundary():
    """v4:1343 uses `>=` so 0.3 itself quotes the title."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        bands={"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2},
        audible_track="X",
        audible_track_confidence=0.3,
    )
    out = AICoach.evidence_line(state)
    assert "track='X'" in out
    assert "track=unknown" not in out


def test_evidence_line_HAS_NO_phase_field():
    """LOAD-BEARING ANTI-HALLUCINATION: v4:1350-1351 removed `phase=`.
    Verify the substring is ABSENT for every non-silent phase label."""
    for phase_value in ("silent", "low", "groove", "build", "drop", "peak", "breakdown"):
        state = MusicState(audible=True, rms=0.05, bpm=120.0, phase=phase_value)
        out = AICoach.evidence_line(state)
        assert "phase=" not in out, f"unexpected phase= field with phase={phase_value!r}"
        # phase_age IS allowed when phase_history is populated; only the literal
        # substring "phase=" (with no underscore) is banned.


def test_evidence_line_phase_age_when_history_present(mocker):
    """phase_history non-empty → `phase_age=...s` (note: trailing 's')."""
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        phase_history=[(988.0, "groove", "build")],
    )
    out = AICoach.evidence_line(state)
    assert "phase_age=12.0s" in out


def test_evidence_line_track_age_when_history_present(mocker):
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        track_history=[(992.5, "Title")],
    )
    out = AICoach.evidence_line(state)
    assert "track_age=7.5s" in out


def test_evidence_line_recent_moves_rendering():
    """Newest-first ordering by age (smallest age = most recent)."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        recent_moves=[(5.4, "xfader→A-side"), (2.1, "A_low: flat→killed (big twist)")],
    )
    out = AICoach.evidence_line(state)
    # Sorted ascending by age → 2.1 first, then 5.4.
    assert (
        "recent_moves[8s]: 2.1s ago A_low: flat→killed (big twist), 5.4s ago xfader→A-side" in out
    )


def test_evidence_line_recent_moves_filtered_by_age():
    """Moves with age > 8.0 are filtered out (v4:1362)."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        recent_moves=[(2.0, "A_play→ON"), (10.5, "B_low: cut→killed (big twist)")],
    )
    out = AICoach.evidence_line(state)
    assert "A_play→ON" in out
    assert "B_low" not in out  # filtered (age 10.5 > 8.0)


def test_evidence_line_set_arc_only_when_len_ge_2():
    state_short = MusicState(audible=True, rms=0.05, bpm=120.0, long_arc=[0.05])
    out_short = AICoach.evidence_line(state_short)
    assert "set_arc" not in out_short

    state_long = MusicState(audible=True, rms=0.05, bpm=120.0, long_arc=[0.05, 0.06, 0.08])
    out_long = AICoach.evidence_line(state_long)
    assert "set_arc[30s]=[0.05, 0.06, 0.08]" in out_long


def test_evidence_line_phase_history_chain():
    """phase_history → 'silent→low→groove→drop' chain (v4:1376-1382)."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        phase_history=[
            (100.0, "silent", "low"),
            (200.0, "low", "groove"),
            (300.0, "groove", "drop"),
        ],
    )
    out = AICoach.evidence_line(state)
    assert "phase_history: silent→low→groove→drop" in out


def test_evidence_line_recent_tracks_at_2_entries():
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        track_history=[(100.0, "Song A"), (200.0, "Song B"), (300.0, "Song C")],
    )
    out = AICoach.evidence_line(state)
    assert "recent_tracks: 'Song A'→'Song B'→'Song C'" in out


def test_evidence_line_uses_pipe_separator():
    """v4:1389 joins with ' | ' (pipe), NOT comma."""
    state = MusicState()
    out = AICoach.evidence_line(state)
    # The fields are separated by " | " — 4 components in the minimal case
    # (hearing, track, deck, set_time, recent_moves[8s]) — so 4 separators.
    assert out.count(" | ") == 4


# ---------- task_for_event: golden strings ----------


def _ev(type_: str, extra: dict | None = None) -> Event:
    return Event(type=type_, state=MusicState(), extra=extra or {})


def test_task_kaan_spoke_exact_string():
    """2026-05-18 — word-count clauses dropped from prompts; Gemini routinely
    blew past the budget and the clause was just noise. Reactions stay
    short by `style:` rules in the system instruction, not per-prompt budget."""
    out = AICoach.task_for_event(_ev("KAAN_SPOKE"))
    assert (
        out
        == "Kaan just SPOKE — answer him directly, friend tone. Short. Not a music reaction."
    )


def test_task_manual_exact_string():
    out = AICoach.task_for_event(_ev("MANUAL"))
    assert out == (
        "Kaan hit his trigger — react with substance to ONE concrete thing "
        "(audible event or recent move)."
    )


def test_task_track_change_no_prev_track():
    """prev_clause is empty when prev_track is None/missing."""
    out = AICoach.task_for_event(_ev("TRACK_CHANGE", {"new_track": "X"}))
    assert "Track flipped." in out
    assert "(was:" not in out
    assert "React to the NEW track's vibe vs the previous" in out
    assert "heavier, weirder, darker, more euphoric?" in out


def test_task_track_change_with_prev_track():
    """prev_clause uses `!r` (repr → single-quoted)."""
    out = AICoach.task_for_event(_ev("TRACK_CHANGE", {"prev_track": "Old Title"}))
    assert "Track flipped (was: 'Old Title')." in out


def test_task_phase_exact_format():
    out = AICoach.task_for_event(_ev("PHASE", {"prev_phase": "groove", "new_phase": "drop"}))
    assert "Phase shifted: groove→drop." in out
    assert "FEELS like, not the label." in out


def test_task_phase_fallback_when_extras_missing():
    """Missing prev_phase/new_phase → '?' fallback (v4:1407-1408)."""
    out = AICoach.task_for_event(_ev("PHASE"))
    assert "Phase shifted: ?→?." in out


def test_task_layer_arrival_exact_string():
    out = AICoach.task_for_event(_ev("LAYER_ARRIVAL"))
    assert out == (
        "A new sonic layer arrived — synth lead, hi-hat layer, vocal, "
        "riff, pad. Name what arrived and how it feels."
    )


def test_task_mix_move_LOAD_BEARING_anti_slop_clause():
    """The 'Do NOT name faders/EQs/knobs/decks/controls' clause is the v4
    anti-slop tightening — DO NOT paraphrase on refactor."""
    out = AICoach.task_for_event(
        _ev("MIX_MOVE", {"moves": ["A_play→ON", "A_low: cut→killed (big twist)"]})
    )
    assert "MIDI moves [A_play→ON, A_low: cut→killed (big twist)]" in out
    assert "Do NOT name faders/EQs/knobs/decks/controls" in out
    assert "If the audio didn't actually change, output a single space to stay silent." in out


def test_task_heartbeat_LOAD_BEARING_anti_silence_clause():
    """The 'don't go silent' clause is the v4 anti-mute tightening."""
    out = AICoach.task_for_event(_ev("HEARTBEAT"))
    assert "don't go silent" in out
    assert out == (
        "Steady stretch. ONE sharp observation about the SOUND right "
        "now — groove, texture, what the track is doing musically. "
        "Always reply with something fresh; don't go silent."
    )


def test_task_fallback_unknown_type():
    out = AICoach.task_for_event(_ev("UNKNOWN_TYPE"))
    assert out == "React naturally."


# ---------- build_prompt: format wrapper ----------


def test_build_prompt_format():
    """v4:1429-1433 format: f'[{evidence} | event={ev.type}] {task}'."""
    ev = _ev("HEARTBEAT")
    out = AICoach.build_prompt(ev)
    assert out.startswith("[")
    # The closing bracket comes immediately after 'event=HEARTBEAT' then space + task.
    assert " | event=HEARTBEAT] " in out
    # The task tail is present:
    assert "Steady stretch." in out


def test_build_prompt_integrates_evidence_and_task():
    """Verify the full chain: evidence + event marker + task all stitched together."""
    ev = _ev("KAAN_SPOKE")
    out = AICoach.build_prompt(ev)
    # Evidence opens the string:
    assert "hearing[silent]" in out
    # Event marker present:
    assert "event=KAAN_SPOKE" in out
    # Task is at the end (after `]`):
    assert out.endswith("Not a music reaction.")


def test_build_prompt_track_change_with_prev_flows_through():
    ms = MusicState()
    ev = Event("TRACK_CHANGE", ms, extra={"prev_track": "A", "new_track": "B"})
    out = AICoach.build_prompt(ev)
    assert "event=TRACK_CHANGE" in out
    assert "(was: 'A')" in out


# =============================================================================
# Phase 18 Plan 02 — AICoach evidence_line + build_prompt registry_snapshot
# =============================================================================


def test_18_02_evidence_line_byte_identical_when_no_snapshot():
    """Test L — backward-compat: existing signature still works.

    AICoach.evidence_line(state) without snapshot kwarg returns the SAME
    string it does today (byte-for-byte). Existing test_coach.py tests stay
    GREEN unchanged (verified by the rest of this file). This test pins
    the no-kwarg path explicitly.
    """
    state = MusicState()  # silent default
    out_no_kwarg = AICoach.evidence_line(state)
    out_none_kwarg = AICoach.evidence_line(state, registry_snapshot=None)
    assert out_no_kwarg == out_none_kwarg
    # Byte-identical to the v4 silent baseline pinned in
    # test_evidence_line_silent_state_full_format above.
    assert out_no_kwarg == (
        "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
    )


def test_18_02_evidence_line_appends_corpus_footer_when_snapshot_present():
    """Test M — snapshot kwarg appended as evidence-corpus footer.

    AICoach.evidence_line(state, registry_snapshot={...}) appends a single
    line "evidence_corpus[ev=N,aud=M,mix=K]" at the end where N/M/K are
    integer counts of observations per source. Only present when snapshot
    is non-None AND has at least one observation; otherwise omitted.
    """
    state = MusicState()
    snapshot = {
        "ev": {"HEARTBEAT": (10.0, 80.0), "MIX_MOVE": (45.0,)},  # 3 obs
        "aud": {"rms": (5.0, 6.0, 7.0, 8.0), "bpm": (5.0,)},     # 5 obs
        "mix": {"phase=drop": (45.0,)},                           # 1 obs
    }
    out = AICoach.evidence_line(state, registry_snapshot=snapshot)
    assert "evidence_corpus[ev=3,aud=5,mix=1]" in out
    # Footer appears once, at the very end (after the last existing pipe)
    assert out.endswith("evidence_corpus[ev=3,aud=5,mix=1]")


def test_18_02_evidence_line_omits_footer_when_snapshot_empty():
    """Empty snapshot dict → footer omitted (no zero-only line)."""
    state = MusicState()
    out_empty = AICoach.evidence_line(state, registry_snapshot={})
    assert "evidence_corpus" not in out_empty

    # All-zero counts (snapshot has source keys but no observations) → omitted
    out_zero_obs = AICoach.evidence_line(state, registry_snapshot={"ev": {}, "aud": {}, "mix": {}})
    assert "evidence_corpus" not in out_zero_obs


def test_18_02_evidence_line_handles_missing_source_keys():
    """Snapshot with only some source keys → counts the present ones, treats
    missing keys as 0. No KeyError."""
    state = MusicState()
    snapshot = {"ev": {"HEARTBEAT": (10.0,)}}  # only ev, no aud/mix
    out = AICoach.evidence_line(state, registry_snapshot=snapshot)
    assert "evidence_corpus[ev=1,aud=0,mix=0]" in out


def test_18_02_build_prompt_threads_snapshot_kwarg():
    """Test N — build_prompt accepts and threads snapshot.

    AICoach.build_prompt(ev, registry_snapshot=...) calls evidence_line with
    the same snapshot. Default None preserves Phase 4 invariant.
    """
    ev = _ev("HEARTBEAT")
    snapshot = {"ev": {"HEARTBEAT": (45.0,)}}
    out = AICoach.build_prompt(ev, registry_snapshot=snapshot)
    assert "evidence_corpus[ev=1,aud=0,mix=0]" in out

    # Default None preserves Phase 4 invariant — same as build_prompt(ev)
    out_default = AICoach.build_prompt(ev)
    out_none = AICoach.build_prompt(ev, registry_snapshot=None)
    assert out_default == out_none
    assert "evidence_corpus" not in out_default
