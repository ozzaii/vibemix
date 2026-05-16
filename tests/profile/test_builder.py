# SPDX-License-Identifier: Apache-2.0
"""Profile builder tests — Phase 32-01.

Covers:
- PROFILE-01: builder API + cold start defaults.
- PROFILE-02 + P51: 2048-byte cap; no-track-titles privacy grep.
- PROFILE-05: consent=False short-circuit.
- PROFILE-06: ≥2-citation rule per tendency field.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import pytest

from vibemix.profile import (
    MAX_PROFILE_BYTES,
    ProfileError,
    build_profile,
    serialize_profile,
)


@dataclass
class _FakeState:
    bpm: float = 0.0
    session_t: float = 0.0


@dataclass
class _FakeEvent:
    state: _FakeState


def _make_event(bpm: float = 0.0, session_t: float = 0.0) -> _FakeEvent:
    return _FakeEvent(state=_FakeState(bpm=bpm, session_t=session_t))


# ----------------------------------------------------------------------------
# PROFILE-05 — consent default-OFF
# ----------------------------------------------------------------------------


def test_consent_off_returns_none() -> None:
    """PROFILE-05: builder MUST return None when consent is False."""
    result = build_profile(None, [], {}, consent=False)
    assert result is None


def test_consent_default_is_false() -> None:
    """The default value of the consent kwarg is False — caller must opt-in."""
    result = build_profile(None, [_make_event(bpm=128)], {"event": {"PHASE": (1, 2)}})
    assert result is None


# ----------------------------------------------------------------------------
# PROFILE-01 — cold start
# ----------------------------------------------------------------------------


def test_cold_start_with_consent_returns_valid_profile() -> None:
    result = build_profile(None, [], {}, consent=True)
    assert result is not None
    # Cold-start defaults — must satisfy schema (validated via serialize).
    raw = serialize_profile(result)
    assert raw  # bytes returned
    assert result["preferred_genre"] == "unknown"
    assert result["tempo_preference_bin"] == "128-138"
    assert result["mix_style_tags"] == []
    assert result["avg_session_duration"] == 0.0


# ----------------------------------------------------------------------------
# PROFILE-02 + P51 — 2KB cap + privacy
# ----------------------------------------------------------------------------


def test_profile_size_cap_2048_bytes() -> None:
    """Healthy profile is well under the 2048-byte cap."""
    result = build_profile(None, [_make_event(bpm=130, session_t=3600)], {
        "event": {ev: (1, 2, 3) for ev in (
            "TRACK_CHANGE", "PHASE", "KAAN_SPOKE", "MIX_MOVE",
            "DISTORTION_CLIMB", "ACID_LINE_ENTRY", "HEARTBEAT", "LAYER_ARRIVAL",
        )},
        "genre": {"techno": (1, 2, 3)},
        "mix_style": {"long_blends": (1, 2), "filter_sweeps": (1, 2)},
    }, consent=True)
    assert result is not None
    raw = serialize_profile(result)
    assert len(raw) <= MAX_PROFILE_BYTES


def test_serialize_rejects_oversize_profile() -> None:
    """A profile that somehow exceeds 2048 bytes raises ProfileError."""
    bad = {
        "preferred_genre": "techno",
        "avg_session_duration": 72.0,
        # 8 tags is the schema cap; doesn't blow past 2KB on its own — but
        # we can stretch event_type_response_preferences with all 8 keys
        # set to "sometimes" + the largest other values to push close to
        # the cap. To deterministically trip the cap, we monkeypatch the
        # constant to a value smaller than the natural footprint.
        "mix_style_tags": [
            "long_blends", "quick_cuts", "loops", "filter_sweeps",
            "loud_drops", "subtle_transitions", "vocal_pickups", "bass_riding",
        ],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {
            "TRACK_CHANGE": "sometimes",
            "PHASE": "sometimes",
            "KAAN_SPOKE": "sometimes",
            "MIX_MOVE": "sometimes",
            "DISTORTION_CLIMB": "sometimes",
            "ACID_LINE_ENTRY": "sometimes",
            "HEARTBEAT": "sometimes",
            "LAYER_ARRIVAL": "sometimes",
        },
    }
    # Patch the cap below the natural footprint so the cap-violation path
    # is exercised without needing a contrived schema-breaking profile.
    from vibemix.profile import builder as _builder

    orig_cap = _builder.MAX_PROFILE_BYTES
    try:
        _builder.MAX_PROFILE_BYTES = 50  # impossibly small
        with pytest.raises(ProfileError, match="cap"):
            _builder.serialize_profile(bad)
    finally:
        _builder.MAX_PROFILE_BYTES = orig_cap


def test_no_track_titles_in_profile_serialized_bytes() -> None:
    """P51 privacy: NO string in the serialized profile should look like a
    track title.

    We synthesize a profile from evidence that COULD contain title-like keys
    (e.g., evidence_snapshot["track"]["Daft Punk - Around the World"]) and
    verify the title never escapes into the profile bytes — the builder only
    reads from the ALLOWLISTED sources (event, genre, mix_style), so a
    track-key in evidence_snapshot must NOT influence the profile output.
    """
    evidence = {
        "track": {  # NOT consumed by the builder — privacy boundary
            "Daft Punk - Around the World": (1.0, 2.0, 3.0),
            "Surgeon - Untitled Promo 02 (DO NOT SHARE)": (4.0,),
        },
        "event": {"TRACK_CHANGE": (1, 2)},
    }
    result = build_profile(None, [], evidence, consent=True)
    raw = serialize_profile(result)
    # Title-like pattern: "Word(s) - Word(s)"
    pattern = re.compile(rb"[A-Z][A-Za-z]+\s*-\s*[A-Z]")
    assert not pattern.search(raw), f"track-title-like text leaked: {raw!r}"
    # Direct substring check for the exact synthetic titles.
    assert b"Daft Punk" not in raw
    assert b"Surgeon" not in raw
    assert b"DO NOT SHARE" not in raw


def test_no_track_titles_when_unknown_evidence_source_present() -> None:
    """Defense-in-depth: even malformed extra evidence sources cannot smuggle
    title-like text into the profile."""
    evidence = {
        "library_titles": {  # made-up source name
            "Adam Beyer - Greyhound": (1.0, 2.0),
        },
    }
    result = build_profile(None, [], evidence, consent=True)
    raw = serialize_profile(result)
    assert b"Adam Beyer" not in raw
    assert b"Greyhound" not in raw


# ----------------------------------------------------------------------------
# PROFILE-06 — ≥2-citation rule
# ----------------------------------------------------------------------------


def test_tendency_requires_2_citations_response_prefs_default_to_prior() -> None:
    """PROFILE-06: <2 citations → retain prior cadence."""
    prior = {
        "preferred_genre": "techno",
        "avg_session_duration": 60.0,
        "mix_style_tags": [],
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
    # Evidence with only 1 citation for PHASE.
    evidence = {"event": {"PHASE": (42.0,)}}
    result = build_profile(prior, [], evidence, consent=True)
    assert result is not None
    # PHASE had only 1 citation → retains prior value.
    assert result["event_type_response_preferences"]["PHASE"] == "sometimes"


def test_tendency_3_citations_promotes_to_sometimes() -> None:
    evidence = {"event": {"PHASE": (1.0, 2.0, 3.0)}}
    result = build_profile(None, [], evidence, consent=True)
    assert result is not None
    assert result["event_type_response_preferences"]["PHASE"] == "sometimes"


def test_tendency_6_citations_promotes_to_always() -> None:
    evidence = {"event": {"PHASE": tuple(float(i) for i in range(6))}}
    result = build_profile(None, [], evidence, consent=True)
    assert result is not None
    assert result["event_type_response_preferences"]["PHASE"] == "always"


def test_genre_below_2_citations_retains_prior() -> None:
    prior = {"preferred_genre": "house"}
    evidence = {"genre": {"techno": (1.0,)}}  # only 1 citation
    result = build_profile(prior, [], evidence, consent=True)
    assert result is not None
    assert result["preferred_genre"] == "house"


def test_genre_above_threshold_updates() -> None:
    evidence = {"genre": {"hard_tek": (1.0, 2.0, 3.0)}}
    result = build_profile(None, [], evidence, consent=True)
    assert result is not None
    assert result["preferred_genre"] == "hard_tek"


def test_tempo_below_2_observations_retains_prior() -> None:
    prior = {"tempo_preference_bin": "120-128"}
    result = build_profile(prior, [_make_event(bpm=145)], {}, consent=True)
    assert result is not None
    # Only 1 BPM observation → retain prior.
    assert result["tempo_preference_bin"] == "120-128"


def test_tempo_above_threshold_updates_to_modal_bin() -> None:
    events = [_make_event(bpm=145) for _ in range(5)] + [_make_event(bpm=130)]
    result = build_profile(None, [], {}, consent=True)
    assert result is not None
    # Empty events → cold-start default 128-138.
    assert result["tempo_preference_bin"] == "128-138"
    result2 = build_profile(None, events, {}, consent=True)
    assert result2 is not None
    assert result2["tempo_preference_bin"] == "138-150"


# ----------------------------------------------------------------------------
# Backward-compat with existing prior profile shapes
# ----------------------------------------------------------------------------


def test_serialize_roundtrip() -> None:
    result = build_profile(None, [_make_event(bpm=130), _make_event(bpm=132)], {
        "event": {ev: (1, 2, 3) for ev in (
            "TRACK_CHANGE", "PHASE", "KAAN_SPOKE", "MIX_MOVE",
            "DISTORTION_CLIMB", "ACID_LINE_ENTRY", "HEARTBEAT", "LAYER_ARRIVAL",
        )},
    }, consent=True)
    raw = serialize_profile(result)
    parsed = json.loads(raw.decode("utf-8"))
    assert parsed == result
