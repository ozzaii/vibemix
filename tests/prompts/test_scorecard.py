# SPDX-License-Identifier: Apache-2.0
"""PROMPT-06: Coach scorecard — qualitative band classifier.

summarize_session(events: list[dict]) → str ∈ {"clean", "decent", "abrupt",
"train-wreck"} — NEVER numeric.

Bands derived from CONTEXT §Coach scorecard:
- "clean":       0-1 slop_suppressed AND 0-2 abrupt MIX_MOVE
- "decent":      2-3 slop_suppressed OR 3-5 abrupt MIX_MOVE
- "abrupt":      4-7 slop_suppressed OR 6-10 abrupt MIX_MOVE
- "train-wreck": 8+ slop_suppressed OR 11+ abrupt MIX_MOVE

The function counts:
- slop_suppressed events
- silence_short_circuit events (LLM emitted <silence/>)
- MIX_MOVE events with extra={"abrupt": True}
"""

from __future__ import annotations

import re

import pytest

from vibemix.prompts.scorecard import summarize_session

VALID_BANDS = {"clean", "decent", "abrupt", "train-wreck"}


# ---------------------------------------------------------------------------
# Empty + return-type invariants
# ---------------------------------------------------------------------------


def test_scorecard_01_empty_events_returns_clean() -> None:
    """No events at all → 'clean'."""
    assert summarize_session([]) == "clean"


def test_scorecard_02_return_is_one_of_four_bands() -> None:
    """Return is always one of 4 strings — never numeric."""
    out = summarize_session([])
    assert isinstance(out, str)
    assert out in VALID_BANDS


def test_scorecard_03_never_numeric() -> None:
    """The output never contains a numeric score (no '8/10', '0.8', etc.)."""
    cases = [
        [],
        [{"kind": "slop_suppressed", "matches": ["amazing"]}],
        [{"kind": "slop_suppressed"}] * 10,
        [{"kind": "MIX_MOVE", "extra": {"abrupt": True}}] * 12,
    ]
    for ev_list in cases:
        out = summarize_session(ev_list)
        assert not re.search(r"\d+\s*/\s*\d+", out), f"numeric score in: {out!r}"
        assert not re.search(r"\d+\.\d+", out), f"decimal score in: {out!r}"
        assert out in VALID_BANDS


# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------


def test_scorecard_04_one_slop_suppressed_is_clean() -> None:
    """1 slop suppression alone → 'clean' (within the noise floor)."""
    events = [{"kind": "slop_suppressed", "matches": ["amazing"]}]
    assert summarize_session(events) == "clean"


@pytest.mark.parametrize("count", [2, 3])
def test_scorecard_05_two_or_three_slop_is_decent(count: int) -> None:
    """2-3 slop suppressions → 'decent'."""
    events = [{"kind": "slop_suppressed", "matches": ["amazing"]}] * count
    assert summarize_session(events) == "decent"


@pytest.mark.parametrize("count", [4, 5, 6, 7])
def test_scorecard_06_four_to_seven_slop_is_abrupt(count: int) -> None:
    """4-7 slop suppressions → 'abrupt'."""
    events = [{"kind": "slop_suppressed", "matches": ["amazing"]}] * count
    assert summarize_session(events) == "abrupt"


@pytest.mark.parametrize("count", [8, 12, 50])
def test_scorecard_07_eight_plus_slop_is_train_wreck(count: int) -> None:
    """8+ slop suppressions → 'train-wreck'."""
    events = [{"kind": "slop_suppressed", "matches": ["amazing"]}] * count
    assert summarize_session(events) == "train-wreck"


# ---------------------------------------------------------------------------
# Mix-move abrupt counting
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [3, 5])
def test_scorecard_08_three_to_five_abrupt_mix_moves_is_decent(count: int) -> None:
    """3-5 abrupt MIX_MOVE events → 'decent'."""
    events = [{"kind": "MIX_MOVE", "extra": {"abrupt": True}}] * count
    assert summarize_session(events) == "decent"


@pytest.mark.parametrize("count", [6, 10])
def test_scorecard_09_six_to_ten_abrupt_mix_moves_is_abrupt(count: int) -> None:
    """6-10 abrupt MIX_MOVE events → 'abrupt'."""
    events = [{"kind": "MIX_MOVE", "extra": {"abrupt": True}}] * count
    assert summarize_session(events) == "abrupt"


def test_scorecard_10_eleven_plus_abrupt_mix_moves_is_train_wreck() -> None:
    """11+ abrupt MIX_MOVE events → 'train-wreck'."""
    events = [{"kind": "MIX_MOVE", "extra": {"abrupt": True}}] * 11
    assert summarize_session(events) == "train-wreck"


def test_scorecard_11_clean_mix_moves_dont_count() -> None:
    """MIX_MOVE without abrupt:True does NOT count toward bands."""
    events = [{"kind": "MIX_MOVE", "extra": {}}] * 20
    assert summarize_session(events) == "clean"


# ---------------------------------------------------------------------------
# Combined / worst-band wins
# ---------------------------------------------------------------------------


def test_scorecard_12_worst_band_wins() -> None:
    """When slop and abrupt thresholds disagree → worst band wins."""
    # 2 slop = decent; 11 abrupt = train-wreck → train-wreck overall.
    events = [{"kind": "slop_suppressed"}] * 2 + [
        {"kind": "MIX_MOVE", "extra": {"abrupt": True}}
    ] * 11
    assert summarize_session(events) == "train-wreck"


def test_scorecard_13_silence_short_circuit_does_not_count_as_slop() -> None:
    """silence_short_circuit (LLM behaved correctly) does NOT degrade band."""
    events = [{"kind": "silence_short_circuit"}] * 50
    # 50 well-behaved silences = the LLM correctly skipped 50 turns. Clean.
    assert summarize_session(events) == "clean"


def test_scorecard_14_unrelated_events_ignored() -> None:
    """Non-slop, non-mix-move events are ignored."""
    events = [
        {"kind": "llm_invoke"},
        {"kind": "ai_text"},
        {"kind": "track_resolved"},
    ] * 30
    assert summarize_session(events) == "clean"
