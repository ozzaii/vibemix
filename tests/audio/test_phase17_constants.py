# SPDX-License-Identifier: Apache-2.0
"""Phase 17 — Hard Tek detectors v1 / GenreRouter constants (SENSE-13/SENSE-15).

Locks the shape + values of the new constants introduced for the Phase 17
detector wave so downstream Wave 2 detectors can import them confidently.

Source of truth: 17-01-PLAN.md Task 1 + 17-CONTEXT.md D-04 (genre BPM bands).
The hard_tek upper bound MUST equal `BPM_VALID_MAX` — this locks the SENSE-15
contract that the genre router shares the autocorr-noise-reject ceiling so a
spurious 250 BPM lock can never silently flip the active genre.
"""

from __future__ import annotations

from vibemix.audio.constants import (
    BPM_VALID_MAX,
    BUILDUP_SLOPE_WINDOW_S,
    GENRE_BPM_BANDS,
    GENRE_CENTROID_HARD_TEK_MIN,
)


def test_genre_bpm_bands_constant_shape() -> None:
    """GENRE_BPM_BANDS is a dict of {"house"/"techno"/"hard_tek"/"unknown":
    (min_bpm, max_bpm)} per CONTEXT D-04. Bands intentionally non-overlapping;
    gaps (128-128, 138-140) → "unknown" (per "trust the audio" — don't
    force-classify ambiguous)."""
    assert isinstance(GENRE_BPM_BANDS, dict)
    assert set(GENRE_BPM_BANDS.keys()) == {"house", "techno", "hard_tek", "unknown"}

    for name, band in GENRE_BPM_BANDS.items():
        assert isinstance(band, tuple), f"{name} band must be a tuple"
        assert len(band) == 2, f"{name} band must be (min, max) — got {band}"
        lo, hi = band
        assert isinstance(lo, float), f"{name} min must be float, got {type(lo).__name__}"
        assert isinstance(hi, float), f"{name} max must be float, got {type(hi).__name__}"


def test_genre_bpm_bands_values_match_context_d04() -> None:
    """Per CONTEXT D-04: house 118-128, techno 128-138, hard_tek 140-160+
    (upper sentinel = BPM_VALID_MAX). Locks the SENSE-15 contract."""
    assert GENRE_BPM_BANDS["house"] == (118.0, 128.0)
    assert GENRE_BPM_BANDS["techno"] == (128.0, 138.0)
    # hard_tek upper bound MUST equal BPM_VALID_MAX so genre router shares
    # the autocorr-noise-reject ceiling (anti-hallucination).
    assert GENRE_BPM_BANDS["hard_tek"][0] == 140.0
    assert GENRE_BPM_BANDS["hard_tek"][1] == BPM_VALID_MAX
    # "unknown" is the sentinel band — never matches a BPM.
    assert GENRE_BPM_BANDS["unknown"] == (0.0, 0.0)


def test_buildup_slope_window_is_positive_float() -> None:
    """buildup_score is computed over the trailing window of the energy_curve.
    Curve resolution is 1s hop per refresh.py, so window=8s → 8 samples."""
    assert isinstance(BUILDUP_SLOPE_WINDOW_S, float)
    assert BUILDUP_SLOPE_WINDOW_S > 0.0
    # Plan locks the v2.0 value at 8.0s — change requires re-tune evidence.
    assert BUILDUP_SLOPE_WINDOW_S == 8.0


def test_genre_centroid_hard_tek_min_is_in_unit_range() -> None:
    """When BPM lands in hard_tek band, also require (mid_share + high_share)
    to exceed this floor — distorted-kick spectral signature gate,
    anti-misclassify-on-house-with-fast-tempo. Bands are normalized shares
    (sum to 1.0), so the floor must be in [0.0, 1.0]."""
    assert isinstance(GENRE_CENTROID_HARD_TEK_MIN, float)
    assert 0.0 <= GENRE_CENTROID_HARD_TEK_MIN <= 1.0
    # Plan locks v2.0 value at 0.55 — change requires re-tune evidence
    # against Hard Tek anchor tracks.
    assert GENRE_CENTROID_HARD_TEK_MIN == 0.55
