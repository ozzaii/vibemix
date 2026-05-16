# SPDX-License-Identifier: Apache-2.0
"""Phase 31 Plan 03 — Emotion router unit tests."""

from __future__ import annotations

import pytest

from vibemix.state.emotion_router import (
    LONG_PHASE_SEC,
    RMS_HIGH,
    RMS_LOW,
    derive_emotion,
)


class TestHypedPath:
    def test_high_rms_techno_returns_hyped(self) -> None:
        assert derive_emotion("techno", 0.25, 5.0) == "hyped"

    def test_high_rms_house_returns_hyped(self) -> None:
        assert derive_emotion("house", 0.30, 5.0) == "hyped"

    def test_high_rms_hard_tek_returns_hyped(self) -> None:
        assert derive_emotion("hard_tek", 0.50, 5.0) == "hyped"

    def test_high_rms_unknown_genre_returns_hyped(self) -> None:
        # Anti-hallucination: even with unknown genre, real energy maps to hyped.
        assert derive_emotion("unknown", 0.20, 1.0) == "hyped"

    def test_exactly_at_high_threshold_is_hyped(self) -> None:
        assert derive_emotion("techno", RMS_HIGH, 1.0) == "hyped"


class TestFocusedPath:
    def test_techno_at_mid_rms_returns_focused(self) -> None:
        assert derive_emotion("techno", 0.12, 5.0) == "focused"

    def test_house_at_mid_rms_returns_focused(self) -> None:
        assert derive_emotion("house", 0.10, 5.0) == "focused"

    def test_hard_tek_at_mid_rms_does_not_return_focused(self) -> None:
        # hard_tek skips focused — Hard Tek at mid RMS is a build, not a groove.
        assert derive_emotion("hard_tek", 0.12, 5.0) == "neutral"

    def test_unknown_at_mid_rms_does_not_return_focused(self) -> None:
        # Focused requires confident genre.
        assert derive_emotion("unknown", 0.12, 5.0) == "neutral"


class TestConcernedPath:
    def test_low_rms_long_phase_returns_concerned(self) -> None:
        assert derive_emotion("techno", 0.03, 35.0) == "concerned"

    def test_low_rms_short_phase_returns_neutral(self) -> None:
        # Long-phase guard prevents premature concern.
        assert derive_emotion("techno", 0.03, 5.0) == "neutral"

    def test_low_rms_at_long_phase_boundary_is_concerned(self) -> None:
        assert derive_emotion("techno", 0.05, LONG_PHASE_SEC) == "concerned"


class TestNeutralFallthrough:
    def test_default_returns_neutral(self) -> None:
        assert derive_emotion("unknown", 0.10, 5.0) == "neutral"


class TestThresholdSanity:
    def test_thresholds_are_locked_constants(self) -> None:
        assert RMS_HIGH == 0.18
        assert RMS_LOW == 0.08
        assert LONG_PHASE_SEC == 30.0
        assert RMS_LOW < RMS_HIGH


@pytest.mark.parametrize(
    "genre,rms,phase_t,expected",
    [
        ("hard_tek", 0.20, 1.0, "hyped"),
        ("techno", 0.15, 5.0, "focused"),
        ("house", 0.02, 60.0, "concerned"),
        ("unknown", 0.10, 5.0, "neutral"),
    ],
)
def test_emotion_router_parametrized_paths(
    genre: str, rms: float, phase_t: float, expected: str
) -> None:
    assert derive_emotion(genre, rms, phase_t) == expected
