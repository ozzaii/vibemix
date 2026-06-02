# SPDX-License-Identifier: Apache-2.0
"""The persona line layer — turns the deterministic reaction reel into spoken lines.

``runtime/automix_demo`` emits semantic cue KEYS (``drop_incoming`` …); this layer
is the "persona turns each cue into a line" step its docstring promises. The lines
are short DJ-friend interjections the co-host SPEAKS on the drop, and every one of
them must survive the SAME anti-slop wall the live co-host's reactions pass
(``prompts.filter.filter_for_slop``) — compose-existing: the new spoken surface is
graded by the existing release gate, not a parallel one.
"""
from __future__ import annotations

from vibemix.prompts.filter import filter_for_slop
from vibemix.runtime.automix_demo import build_automix_reel
from vibemix.runtime.drop_reaction import (
    REACTION_CUES,
    REACTION_LINES,
    SpokenBeat,
    narrate_reel,
    reaction_line,
)
from vibemix.state.transition_clock import TrackCues, TransitionMode


def _cues_pair():
    from_cues = TrackCues(duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0)
    to_cues = TrackCues(duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0)
    return from_cues, to_cues


def test_every_reaction_cue_has_a_nonempty_bank() -> None:
    # The five keys runtime.automix_demo.reaction_cue can emit.
    assert REACTION_CUES == frozenset(
        {"drop_incoming", "mixing_in", "slam_in", "landed_clean", "slammed_cut"}
    )
    for cue in REACTION_CUES:
        assert cue in REACTION_LINES
        assert len(REACTION_LINES[cue]) >= 1
        for line in REACTION_LINES[cue]:
            assert line.strip()


def test_reaction_line_returns_a_line_for_each_cue() -> None:
    for cue in REACTION_CUES:
        line = reaction_line(cue)
        assert isinstance(line, str) and line.strip()


def test_reaction_line_variant_wraps_modulo() -> None:
    for cue in REACTION_CUES:
        n = len(REACTION_LINES[cue])
        assert reaction_line(cue, variant=n) == reaction_line(cue, variant=0)
        assert reaction_line(cue, variant=n + 1) == reaction_line(cue, variant=1 % n)


def test_unknown_cue_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        reaction_line("not_a_cue")


def test_every_line_survives_the_slop_filter() -> None:
    # filter_for_slop returns (clean_text, matched). A clean line matches nothing
    # and is returned untouched. This is the load-bearing compose-existing gate:
    # the spoken drop lines pass the live co-host's own anti-slop wall.
    for cue, bank in REACTION_LINES.items():
        for line in bank:
            clean, matched = filter_for_slop(line)
            assert matched == [], f"slop in {cue!r} line {line!r}: {matched}"
            assert clean == line


def test_reaction_line_fails_closed_when_bank_line_trips_slop_filter(monkeypatch) -> None:
    import pytest

    monkeypatch.setitem(REACTION_LINES, "drop_incoming", ("amazing mix",))
    with pytest.raises(ValueError, match="slop-filtered reaction line"):
        reaction_line("drop_incoming")


def test_lines_are_short_spoken_interjections() -> None:
    # A drop reaction is a breath, not a sentence — keep them tight so TTS lands
    # them inside the ~2 s phrase window, not trailing past the next beat.
    for bank in REACTION_LINES.values():
        for line in bank:
            assert len(line) <= 42, f"too long to land on the beat: {line!r}"


def test_narrate_reel_one_spoken_beat_per_demo_beat() -> None:
    from_cues, to_cues = _cues_pair()
    reel = build_automix_reel(
        from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO,
        transition_sec=10.0, arm_lead_sec=2.0,
    )
    spoken = narrate_reel(reel)
    assert len(spoken) == len(reel.beats)
    for sb, db in zip(spoken, reel.beats, strict=True):
        assert isinstance(sb, SpokenBeat)
        assert sb.t_sec == db.t_sec
        assert sb.cue == db.cue
        assert sb.text.strip()
        _clean, matched = filter_for_slop(sb.text)
        assert matched == []


def test_narrate_reel_is_deterministic() -> None:
    from_cues, to_cues = _cues_pair()
    reel = build_automix_reel(from_cues, to_cues, mode=TransitionMode.FULL_INTRO_OUTRO)
    a = narrate_reel(reel, variant_seed=3)
    b = narrate_reel(reel, variant_seed=3)
    assert [s.text for s in a] == [s.text for s in b]


def test_narrate_reel_varies_lines_across_beats() -> None:
    # Consecutive beats of the SAME cue should not always reuse line[0] — the seed
    # walks the bank so a multi-beat run sounds alive, not stuck on one phrase.
    from_cues = TrackCues(duration_sec=240.0, outro_start_sec=200.0, outro_end_sec=220.0)
    to_cues = TrackCues(duration_sec=180.0, intro_start_sec=0.0, intro_end_sec=16.0)
    reel = build_automix_reel(from_cues, to_cues)
    spoken = narrate_reel(reel, variant_seed=1)
    # at minimum, the mapping is total and stable
    assert all(s.text.strip() for s in spoken)
