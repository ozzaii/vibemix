# SPDX-License-Identifier: Apache-2.0
"""Psytrance GenreProfile load + validation coverage (Phase 52 / GENRE-01).

Pins the locked psytrance values and proves the profile validates through the
hand-written ``_parse_profile`` (no pydantic — Critical Constraint 6). The
profile is the data prerequisite for the GENRE-01 auto-detector (Plan 52-03):
the detector scores nearest-match across ``list_profiles()``, so psytrance must
load with a grounded, schema-valid shape before it can ever be picked.
"""

from __future__ import annotations

import json
from importlib import resources

import pytest

from vibemix.audio.constants import BPM_VALID_MAX, BPM_VALID_MIN
from vibemix.state.genre import GenreProfile, load_profile
from vibemix.state.genre.profile import _parse_profile


@pytest.fixture(autouse=True)
def _reset_active_profile():
    """Wipe the module-level active-profile singleton before+after every test."""
    from vibemix.state.genre import profile as _mod

    _mod._ACTIVE_PROFILE = None
    yield
    _mod._ACTIVE_PROFILE = None


def test_load_profile_psytrance_returns_genreprofile():
    prof = load_profile("psytrance")
    assert isinstance(prof, GenreProfile)
    assert prof.name == "psytrance"
    assert prof.label == "Psytrance / Goa / Full-On"
    assert prof.bpm_range == (138.0, 150.0)
    assert prof.expected_crest_factor == (4.0, 7.0)
    assert prof.vocal_likelihood == "rare"


def test_psytrance_band_signature_shape():
    prof = load_profile("psytrance")
    assert prof is not None
    assert set(prof.band_signature.keys()) == {"sub", "low", "mid", "high"}
    for band, (lo, hi) in prof.band_signature.items():
        assert isinstance(lo, float)
        assert isinstance(hi, float)
        assert lo <= hi, f"psytrance/{band}: lo > hi"


def test_psytrance_sub_heavier_than_mid():
    """The offbeat-rolling-bass property: psy's sub band is heavier than its
    mid band — the discriminator vs techno that lets the detector pick psy."""
    prof = load_profile("psytrance")
    assert prof is not None
    sub_lo, sub_hi = prof.band_signature["sub"]
    mid_lo, mid_hi = prof.band_signature["mid"]
    assert sub_hi > mid_hi
    assert sub_lo > mid_lo


def test_psytrance_bpm_range_within_valid_window():
    """bpm_range fully inside [BPM_VALID_MIN, BPM_VALID_MAX] so the BPM gate +
    validate_bpm chain never re-introduces an out-of-range value when psytrance
    is the active profile."""
    prof = load_profile("psytrance")
    assert prof is not None
    lo, hi = prof.bpm_range
    assert BPM_VALID_MIN <= lo < hi <= BPM_VALID_MAX


def test_psytrance_rms_thresholds_strictly_increasing():
    prof = load_profile("psytrance")
    assert prof is not None
    assert prof.silent_rms < prof.low_rms < prof.peak_rms


def test_psytrance_band_signature_midpoint_sums_close_to_one():
    prof = load_profile("psytrance")
    assert prof is not None
    s = sum((lo + hi) / 2 for (lo, hi) in prof.band_signature.values())
    assert 0.85 < s < 1.10, f"psytrance: band-signature midpoint sum {s:.3f} out of bounds"


def test_psytrance_raw_json_passes_handwritten_validator():
    """Explicitly re-validate the raw JSON through _parse_profile (no pydantic)
    so a future schema drift in the JSON is caught directly at the validator."""
    raw = resources.files("vibemix.state.genre.profiles").joinpath("psytrance.json")
    with raw.open("rb") as f:
        payload = json.load(f)
    prof = _parse_profile(payload)
    assert prof.name == "psytrance"
    assert prof.bpm_range == (138.0, 150.0)
