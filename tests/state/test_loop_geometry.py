# SPDX-License-Identifier: Apache-2.0
"""Loop geometry receipt tests."""

from __future__ import annotations

from vibemix.coach import CitationLinter
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.loop_geometry import (
    beatgrid_exact_atom,
    inside_move_dedup_window,
    loop_move_label,
    loop_size_label,
    parse_loop_control_kind,
    retrigger_interval_s,
)


def test_loop_size_labels_use_beat_fractions() -> None:
    assert loop_size_label(4.0) == "4beat"
    assert loop_size_label(0.25) == "1/4beat"
    assert loop_size_label(1 / 16) == "1/16beat"


def test_parse_loop_control_kind_normalizes_future_profile_kinds() -> None:
    roll = parse_loop_control_kind("beatloop_roll_1_4")
    jump = parse_loop_control_kind("beatjump_back_8")

    assert roll is not None
    assert roll.action == "loop_roll"
    assert roll.size_beats == 0.25
    assert jump is not None
    assert jump.action == "beatjump"
    assert jump.size_beats == 8.0
    assert jump.direction == -1


def test_loop_move_label_preserves_legacy_boundaries_and_names_rolls() -> None:
    assert loop_move_label("A", "loop_in", play_on=True) == "A_loop_in_hit (play=ON)"
    assert loop_move_label("A", "loop_out") == "A_loop_out_hit"
    assert loop_move_label("B", "beatloop_roll_1_4") == "B_loop_roll:1/4beat"
    assert loop_move_label("B", "beatjump_fwd_4") == "B_beatjump:+4beat"


def test_fast_roll_intervals_are_inside_legacy_move_dedup_window() -> None:
    assert retrigger_interval_s(0.25, 128.0) == 0.1171875
    assert inside_move_dedup_window(0.25, 128.0) is True
    assert inside_move_dedup_window(4.0, 128.0) is False


def test_beatgrid_exact_atom_is_citable_as_mix_evidence() -> None:
    key = beatgrid_exact_atom("A", "loop_roll", 0.25, beat_index=64)
    registry = EvidenceRegistry()
    registry.write("mix", key, 12.0)

    result = CitationLinter().check(
        f"Loop receipt [mix:{key}]",
        registry.snapshot(),
        mode="live",
    )

    assert key == "loop_boundary_beatgrid_exact=deck_A:loop_roll:1_4beat:beat_64"
    assert result.valid is True
