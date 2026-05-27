# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np
import pytest

from vibemix.intel.transition_scorer import (
    LivePosition,
    SectionRecord,
    TransitionScoringInput,
    bpm_score,
    cue_operability_score,
    harmonic_score,
    score_transition_slate,
)


def _section(
    section_id: str,
    track_id: str,
    role: str,
    *,
    confidence: float = 0.9,
    start_s: float = 0.0,
    end_s: float = 64.0,
    start_beat: int | None = 0,
    bar_count: float | None = 32,
    bpm: float | None = 128.0,
    camelot: str | None = "8A",
    energy_mean: float | None = 50.0,
    cue_slot: str | None = "A",
    cue_source: str | None = "dj",
    cue_confidence: float | None = 0.95,
    tags: tuple[str, ...] = (),
) -> SectionRecord:
    return SectionRecord(
        section_id=section_id,
        track_id=track_id,
        role=role,
        confidence=confidence,
        start_s=start_s,
        end_s=end_s,
        start_beat=start_beat,
        bar_count=bar_count,
        bpm=bpm,
        camelot=camelot,
        energy_mean=energy_mean,
        cue_slot=cue_slot,
        cue_source=cue_source,
        cue_confidence=cue_confidence,
        tags=tags,
    )


def test_harmonic_score_same_key_high() -> None:
    score, flags = harmonic_score("8A", "8A")

    assert score == pytest.approx(1.0)
    assert flags == ()


def test_harmonic_score_relative_high() -> None:
    score, flags = harmonic_score("8A", "8B")

    assert score == pytest.approx(0.92)
    assert flags == ()


def test_harmonic_score_clash_low_and_flagged() -> None:
    score, flags = harmonic_score("8A", "3A")

    assert score == pytest.approx(0.12)
    assert flags == ("harmonic_clash",)


def test_harmonic_score_unknown_neutral_flagged() -> None:
    score, flags = harmonic_score(None, "8A")

    assert score == pytest.approx(0.55)
    assert flags == ("key_unknown",)


def test_bpm_score_within_three_percent_high() -> None:
    score, flags = bpm_score(128.0, 131.0)

    assert score == pytest.approx(0.90)
    assert flags == ()


def test_bpm_score_tempo_jump_low_and_flagged() -> None:
    score, flags = bpm_score(128.0, 145.0)

    assert score == pytest.approx(0.10)
    assert flags == ("tempo_jump",)


def test_bpm_score_nonfinite_degrades_to_unknown() -> None:
    score, flags = bpm_score(float("nan"), 128.0)

    assert score == pytest.approx(0.55)
    assert flags == ("bpm_unknown",)


def test_cue_operability_dj_cue_highest() -> None:
    score, flags = cue_operability_score(
        _section("t2#s000", "t2", "intro", cue_slot="A", cue_source="dj")
    )

    assert score == pytest.approx(1.0)
    assert flags == ()


def test_cue_operability_auto_cue_is_reviewable() -> None:
    review_score, review_flags = cue_operability_score(
        _section("t2#s000", "t2", "intro", cue_slot="A", cue_source="auto", cue_confidence=0.62)
    )
    low_score, low_flags = cue_operability_score(
        _section("t2#s001", "t2", "intro", cue_slot="B", cue_source="auto", cue_confidence=0.32)
    )

    assert review_score == pytest.approx(0.63)
    assert {"auto_cue_review", "cue_needs_review"} <= set(review_flags)
    assert low_score < review_score
    assert {"auto_cue_review", "low_cue_confidence"} <= set(low_flags)


def test_scorer_ranks_grounded_cue_aware_transition() -> None:
    source = _section(
        "t1#s000",
        "t1",
        "outro",
        cue_slot="F",
        energy_mean=52.0,
        camelot="8A",
    )
    destination = _section(
        "t2#s000",
        "t2",
        "intro",
        cue_slot="A",
        energy_mean=54.0,
        camelot="9A",
    )
    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            source_vector=np.array([1.0, 0.0], dtype=np.float32),
            destination_vectors={destination.section_id: np.array([0.95, 0.05], dtype=np.float32)},
            candidate_pool_track_ids=frozenset({"t2"}),
        )
    )

    assert len(slate) == 1
    candidate = slate[0]
    assert candidate.candidate_id == "tr_001"
    assert candidate.from_section_id == "t1#s000"
    assert candidate.to_section_id == "t2#s000"
    assert candidate.from_role == "outro"
    assert candidate.to_role == "intro"
    assert candidate.from_start_s == 0.0
    assert candidate.from_end_s == 64.0
    assert candidate.to_start_s == 0.0
    assert candidate.to_end_s == 64.0
    assert candidate.from_bpm == 128.0
    assert candidate.to_bpm == 128.0
    assert candidate.from_camelot == "8A"
    assert candidate.to_camelot == "9A"
    assert candidate.cue_slot == "A"
    assert candidate.cue_source == "dj"
    assert candidate.cue_confidence == pytest.approx(0.95)
    assert candidate.score > 0.70
    assert "outro into intro is a strong role pair" in candidate.reasons


def test_scorer_drops_same_section() -> None:
    source = _section("t1#s000", "t1", "outro")

    slate = score_transition_slate(TransitionScoringInput(source=source, destinations=(source,)))

    assert slate == ()


def test_scorer_excludes_played_tracks_and_respects_pool() -> None:
    source = _section("t1#s000", "t1", "outro")
    played = _section("t2#s000", "t2", "intro")
    outside_pool = _section("t3#s000", "t3", "intro")
    inside_pool = _section("t4#s000", "t4", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(played, outside_pool, inside_pool),
            played_track_ids=frozenset({"t2"}),
            candidate_pool_track_ids=frozenset({"t4"}),
        ),
        max_candidates=3,
    )

    assert [candidate.to_track_id for candidate in slate] == ["t4"]


def test_live_drops_unknown_destination_role() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "unknown")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.95),
        )
    )

    assert slate == ()


def test_prep_keeps_unknown_role_low_score() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "unknown")

    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,), mode="prep")
    )

    assert len(slate) == 1
    assert "role_unknown" in slate[0].risk_flags


def test_missing_vector_does_not_crash_or_claim_texture() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,))
    )

    assert "semantic_unknown" in slate[0].risk_flags
    assert "section texture is close" not in slate[0].reasons


def test_mismatched_semantic_vector_dims_degrade_to_unknown() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            source_vector=np.array([1.0, 0.0], dtype=np.float32),
            destination_vectors={
                destination.section_id: np.array([1.0, 0.0, 0.0], dtype=np.float32)
            },
        )
    )

    assert "semantic_unknown" in slate[0].risk_flags
    assert "semantic_dim_mismatch" in slate[0].risk_flags
    assert slate[0].semantic_basis == "semantic_unknown"


def test_nonfinite_semantic_vector_degrades_to_unknown() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            source_vector=np.array([1.0, float("nan")], dtype=np.float32),
            destination_vectors={destination.section_id: np.array([1.0, 0.0], dtype=np.float32)},
        )
    )

    assert len(slate) == 1
    assert "semantic_unknown" in slate[0].risk_flags
    assert slate[0].semantic_basis == "semantic_unknown"


def test_nonfinite_energy_degrades_to_unknown_not_perfect_match() -> None:
    source = _section("t1#s000", "t1", "outro", energy_mean=float("nan"))
    destination = _section("t2#s000", "t2", "intro", energy_mean=54.0)

    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,))
    )

    assert len(slate) == 1
    assert slate[0].components.energy_shape == pytest.approx(0.50)
    assert "energy_unknown" in slate[0].risk_flags


def test_nonfinite_timing_sections_are_filtered() -> None:
    source = _section("t1#s000", "t1", "outro")
    bad_destination = _section("t2#s000", "t2", "intro", start_s=float("nan"))

    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(bad_destination,))
    )

    assert slate == ()


def test_harmonic_clash_live_melodic_suppresses() -> None:
    source = _section("t1#s000", "t1", "drop", camelot="8A")
    destination = _section("t2#s000", "t2", "drop", camelot="3A")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.95),
        )
    )

    assert slate == ()


def test_low_playhead_confidence_removes_start_in_bars() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.55),
        )
    )

    assert len(slate) == 1
    assert slate[0].start_in_bars is None
    assert "timing_low_confidence" in slate[0].risk_flags


def test_blend_active_keeps_candidate_but_removes_start_in_bars() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(
                remaining_bars=16,
                playhead_confidence=0.95,
                blend_active=True,
            ),
        )
    )

    assert len(slate) == 1
    assert slate[0].start_in_bars is None
    assert "blend_active" in slate[0].risk_flags


def test_recent_source_loop_keeps_candidate_but_removes_start_in_bars() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(
                remaining_bars=16,
                playhead_confidence=0.95,
                source_loop_recent=True,
            ),
        )
    )

    assert len(slate) == 1
    assert slate[0].start_in_bars is None
    assert "source_loop_recent" in slate[0].risk_flags


def test_high_playhead_confidence_allows_start_in_bars() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.95),
        )
    )

    assert len(slate) == 1
    assert slate[0].start_in_bars == 16


def test_nonfinite_live_timing_withholds_exact_bars() -> None:
    source = _section("t1#s000", "t1", "outro")
    destination = _section("t2#s000", "t2", "intro")

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode="live",
            live_position=LivePosition(
                remaining_bars=float("nan"),  # type: ignore[arg-type]
                playhead_confidence=0.95,
            ),
        )
    )

    assert len(slate) == 1
    assert slate[0].start_in_bars is None


def test_live_caps_one_candidate_per_destination_track() -> None:
    source = _section("t1#s000", "t1", "outro")
    first = _section("t2#s000", "t2", "intro", energy_mean=52.0)
    second = _section("t2#s001", "t2", "groove", start_s=64.0, energy_mean=54.0)

    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(first, second),
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.95),
        ),
        max_candidates=5,
    )

    assert len(slate) == 1
    assert slate[0].to_track_id == "t2"


def test_scorer_generates_stable_candidate_ids() -> None:
    source = _section("t1#s000", "t1", "outro")
    destinations = (
        _section("t2#s000", "t2", "intro"),
        _section("t3#s000", "t3", "groove", camelot="9A"),
    )
    scoring_input = TransitionScoringInput(source=source, destinations=destinations)

    first = score_transition_slate(scoring_input, max_candidates=2)
    second = score_transition_slate(scoring_input, max_candidates=2)

    assert [(c.candidate_id, c.transition_key) for c in first] == [
        (c.candidate_id, c.transition_key) for c in second
    ]
