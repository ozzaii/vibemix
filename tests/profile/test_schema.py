# SPDX-License-Identifier: Apache-2.0
"""Profile schema tests — Phase 32-01 / PROFILE-02 (allowlist) + P51 (privacy)."""

from __future__ import annotations

import pytest

from vibemix.profile import ProfileError, validate_profile


def _valid_profile() -> dict:
    return {
        "preferred_genre": "techno",
        "avg_session_duration": 72.0,
        "mix_style_tags": ["long_blends", "filter_sweeps"],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {
            "TRACK_CHANGE": "always",
            "PHASE": "sometimes",
            "KAAN_SPOKE": "rarely",
            "MIX_MOVE": "sometimes",
            "DISTORTION_CLIMB": "never",
            "ACID_LINE_ENTRY": "never",
            "HEARTBEAT": "rarely",
            "LAYER_ARRIVAL": "sometimes",
        },
    }


def test_valid_profile_passes() -> None:
    validate_profile(_valid_profile())


def test_profile_additional_properties_false_rejects_recent_tracks() -> None:
    """PROFILE-02 + P51 — the schema MUST reject any non-allowlisted field.

    This is the privacy gate: a builder bug that tries to write
    ``recent_tracks`` (a known anti-pattern from P51's "what goes wrong"
    section) fails fast here BEFORE the bytes hit disk.
    """
    bad = _valid_profile()
    bad["recent_tracks"] = ["Daft Punk - Around the World"]
    with pytest.raises(ProfileError, match="recent_tracks|additional"):
        validate_profile(bad)


def test_profile_rejects_library_titles_field() -> None:
    bad = _valid_profile()
    bad["library_titles"] = ["whatever"]
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_free_form_personality_field() -> None:
    bad = _valid_profile()
    bad["personality"] = "energetic warehouse rave"
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_unknown_genre() -> None:
    bad = _valid_profile()
    bad["preferred_genre"] = "psytrance"
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_unknown_mix_style_tag() -> None:
    bad = _valid_profile()
    bad["mix_style_tags"] = ["scratching"]  # not in allowlist
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_more_than_8_tags() -> None:
    bad = _valid_profile()
    bad["mix_style_tags"] = [
        "long_blends",
        "quick_cuts",
        "loops",
        "filter_sweeps",
        "loud_drops",
        "subtle_transitions",
        "vocal_pickups",
        "bass_riding",
        "tempo_jumps",  # 9th — violates maxItems
    ]
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_duplicate_tags() -> None:
    bad = _valid_profile()
    bad["mix_style_tags"] = ["long_blends", "long_blends"]
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_unknown_event_type_in_prefs() -> None:
    bad = _valid_profile()
    bad["event_type_response_preferences"]["UNKNOWN_EVENT"] = "always"
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_invalid_cadence_value() -> None:
    bad = _valid_profile()
    bad["event_type_response_preferences"]["PHASE"] = "very_often"
    with pytest.raises(ProfileError):
        validate_profile(bad)


def test_profile_rejects_duration_above_cap() -> None:
    bad = _valid_profile()
    bad["avg_session_duration"] = 9999  # 12h cap
    with pytest.raises(ProfileError):
        validate_profile(bad)
