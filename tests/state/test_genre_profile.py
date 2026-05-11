# SPDX-License-Identifier: Apache-2.0
"""GenreProfile loader + active-profile singleton coverage (Phase 6 Wave 1).

Tests pin:
- 5 hand-tuned profiles load via ``load_profile``.
- ``list_profiles`` returns the canonical sorted 5-element list.
- Schema validator raises on missing/malformed fields (no silent defaults).
- ``set_active_profile(None)`` is a valid call that clears the singleton —
  Critical Constraint 8 (Phase 3 absolute-threshold fallback path).
- Each shipped profile's hand-tuned values are sensible (band shares sum near
  1.0, BPM range increasing in 80-200, crest range positive in 0-12, RMS
  thresholds strictly increasing).
"""

from __future__ import annotations

import pytest

from vibemix.state.genre import (
    GenreProfile,
    get_active_profile,
    list_profiles,
    load_profile,
    set_active_profile,
)
from vibemix.state.genre.profile import _parse_profile

PROFILE_NAMES = ["disco", "drum_and_bass", "house", "pop", "techno"]


@pytest.fixture(autouse=True)
def _reset_active_profile():
    """Wipe the module-level active-profile singleton before and after every
    test so cross-test pollution can't leak."""
    from vibemix.state.genre import profile as _mod

    _mod._ACTIVE_PROFILE = None
    yield
    _mod._ACTIVE_PROFILE = None


# ---------- Loader smoke ----------


def test_list_profiles_returns_all_five():
    assert list_profiles() == PROFILE_NAMES


def test_load_profile_techno_returns_genreprofile():
    prof = load_profile("techno")
    assert isinstance(prof, GenreProfile)
    assert prof.name == "techno"
    assert prof.label == "Techno / Hard Tek / Acidcore"
    assert prof.bpm_range == (125.0, 175.0)
    assert prof.silent_rms == 0.012
    assert prof.low_rms == 0.040
    assert prof.peak_rms == 0.110
    assert prof.expected_crest_factor == (3.5, 6.5)
    assert prof.vocal_likelihood == "rare"
    assert prof.build_climb_threshold == 0.025
    assert prof.breakdown_ratio == 0.4
    assert prof.drop_jump_threshold == 0.060


def test_load_profile_unknown_returns_none():
    assert load_profile("reggaeton") is None


def test_load_profile_empty_string_returns_none():
    assert load_profile("") is None


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_each_profile_loads_cleanly(name: str):
    prof = load_profile(name)
    assert prof is not None
    assert prof.name == name
    # Band signature has exactly the 4 expected bands:
    assert set(prof.band_signature.keys()) == {"sub", "low", "mid", "high"}
    # Each band's (lo, hi) tuple is a 2-element tuple of floats:
    for band, (lo, hi) in prof.band_signature.items():
        assert isinstance(lo, float)
        assert isinstance(hi, float)
        assert lo <= hi, f"{name}/{band}: lo > hi"


# ---------- Schema validation ----------


def _valid_payload() -> dict:
    """A baseline schema-valid payload for negative-path tests to mutate."""
    return {
        "name": "test",
        "label": "Test Profile",
        "bpm_range": [120, 140],
        "absolute_thresholds": {"silent_rms": 0.01, "low_rms": 0.04, "peak_rms": 0.11},
        "expected_crest_factor": [3.0, 6.0],
        "band_signature": {
            "sub": [0.20, 0.40],
            "low": [0.20, 0.30],
            "mid": [0.20, 0.30],
            "high": [0.10, 0.20],
        },
        "vocal_likelihood": "rare",
        "build_climb_threshold": 0.025,
        "breakdown_ratio": 0.4,
        "drop_jump_threshold": 0.060,
    }


def test_parse_valid_payload_succeeds():
    prof = _parse_profile(_valid_payload())
    assert prof.name == "test"


def test_parse_non_dict_payload_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        _parse_profile("not a dict")  # type: ignore[arg-type]


def test_parse_missing_name_raises():
    payload = _valid_payload()
    del payload["name"]
    with pytest.raises(ValueError, match="name"):
        _parse_profile(payload)


def test_parse_missing_bpm_range_raises():
    payload = _valid_payload()
    del payload["bpm_range"]
    with pytest.raises(ValueError, match="bpm_range"):
        _parse_profile(payload)


def test_parse_bad_bpm_range_length_raises():
    payload = _valid_payload()
    payload["bpm_range"] = [125]
    with pytest.raises(ValueError, match="bpm_range"):
        _parse_profile(payload)


def test_parse_bad_bpm_range_non_numeric_raises():
    payload = _valid_payload()
    payload["bpm_range"] = ["fast", "slow"]
    with pytest.raises(ValueError, match="bpm_range"):
        _parse_profile(payload)


def test_parse_missing_absolute_thresholds_raises():
    payload = _valid_payload()
    del payload["absolute_thresholds"]
    with pytest.raises(ValueError, match="absolute_thresholds"):
        _parse_profile(payload)


def test_parse_missing_silent_rms_in_thresholds_raises():
    payload = _valid_payload()
    del payload["absolute_thresholds"]["silent_rms"]
    with pytest.raises(ValueError, match="silent_rms"):
        _parse_profile(payload)


def test_parse_negative_threshold_raises():
    payload = _valid_payload()
    payload["absolute_thresholds"]["silent_rms"] = -0.5
    with pytest.raises(ValueError, match="silent_rms"):
        _parse_profile(payload)


def test_parse_missing_band_raises():
    payload = _valid_payload()
    del payload["band_signature"]["mid"]
    with pytest.raises(ValueError, match=r"band_signature\.mid"):
        _parse_profile(payload)


def test_parse_bad_vocal_likelihood_raises():
    payload = _valid_payload()
    payload["vocal_likelihood"] = "sometimes"
    with pytest.raises(ValueError, match="vocal_likelihood"):
        _parse_profile(payload)


def test_parse_missing_build_climb_threshold_raises():
    payload = _valid_payload()
    del payload["build_climb_threshold"]
    with pytest.raises(ValueError, match="build_climb_threshold"):
        _parse_profile(payload)


# ---------- Per-profile sanity (golden constraints) ----------


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_each_profile_band_signature_midpoint_sums_close_to_one(name: str):
    prof = load_profile(name)
    s = sum((lo + hi) / 2 for (lo, hi) in prof.band_signature.values())
    # Loose tolerance — bands need not sum to 1.0 exactly; transients absorb residual.
    assert 0.85 < s < 1.10, f"{name}: band-signature midpoint sum {s:.3f} outside [0.85, 1.10]"


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_each_profile_bpm_range_increasing_in_dance_bounds(name: str):
    prof = load_profile(name)
    lo, hi = prof.bpm_range
    assert lo < hi, f"{name}: bpm_range lo >= hi"
    assert 80 <= lo < hi <= 200, f"{name}: bpm_range outside [80, 200]"


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_each_profile_crest_factor_range_increasing_positive(name: str):
    prof = load_profile(name)
    lo, hi = prof.expected_crest_factor
    assert 0 < lo < hi <= 12, f"{name}: crest range outside (0, 12]"


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_each_profile_thresholds_increasing(name: str):
    prof = load_profile(name)
    assert prof.silent_rms < prof.low_rms < prof.peak_rms, (
        f"{name}: thresholds not strictly increasing: "
        f"{prof.silent_rms} {prof.low_rms} {prof.peak_rms}"
    )


# ---------- Active-profile singleton ----------


def test_set_active_profile_techno_then_get_returns_techno():
    set_active_profile("techno")
    prof = get_active_profile()
    assert prof is not None
    assert prof.name == "techno"


def test_set_active_profile_none_clears_singleton():
    set_active_profile("techno")
    assert get_active_profile() is not None
    set_active_profile(None)
    assert get_active_profile() is None


def test_set_active_profile_unknown_raises():
    with pytest.raises(ValueError, match="unknown profile"):
        set_active_profile("reggaeton")


def test_get_active_profile_returns_none_by_default():
    # Fixture resets to None before this test
    assert get_active_profile() is None


def test_set_active_profile_round_trip_each_genre():
    for name in PROFILE_NAMES:
        set_active_profile(name)
        prof = get_active_profile()
        assert prof is not None and prof.name == name
