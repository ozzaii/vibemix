# SPDX-License-Identifier: Apache-2.0
"""One Mind S6 — tests for the unified track→track relation primitive.

Pins the three properties that make ``TrackRelation`` safe to share:
  1. It NEVER diverges from ``intel.transition_scorer`` — the harmonic + tempo
     grades are reused, so they must match the set-builder byte-for-byte.
  2. It is honest about unknowns (unknown key/bpm → flags + None deltas, never a
     false "incompatible").
  3. ``why()`` renders the human transition phrase that the co-host will voice.
"""

from __future__ import annotations

import pytest

from vibemix.intel.transition_scorer import bpm_score, harmonic_score
from vibemix.library.track_relation import (
    HARMONIC_COMPATIBLE_FLOOR,
    TrackRelation,
    compute_relation,
)


def _rel(**kw) -> TrackRelation:
    base = dict(
        src_track_id="a",
        dst_track_id="b",
        cosine=0.9,
        src_camelot="8A",
        dst_camelot="9A",
        src_bpm=128.0,
        dst_bpm=133.0,
    )
    base.update(kw)
    return compute_relation(**base)


# --- 1. consistency with the single source of truth ------------------------


def test_s6_harmonic_matches_transition_scorer() -> None:
    for src, dst in [("8A", "9A"), ("8A", "8A"), ("8A", "8B"), ("8A", "2A"), ("1A", "7A")]:
        rel = _rel(src_camelot=src, dst_camelot=dst)
        assert (rel.harmonic, rel.harmonic_flags) == harmonic_score(src, dst)


def test_s6_tempo_matches_transition_scorer() -> None:
    for src, dst in [
        (128.0, 128.0),
        (128.0, 130.0),
        (128.0, 133.0),
        (128.0, 145.0),
        (87.0, 174.0),
    ]:
        rel = _rel(src_bpm=src, dst_bpm=dst)
        assert (rel.tempo, rel.tempo_flags) == bpm_score(src, dst)


def test_s6_cosine_passed_through_verbatim() -> None:
    rel = _rel(cosine=0.4242)
    assert rel.cosine == 0.4242


def test_s6_deterministic() -> None:
    assert _rel() == _rel()


# --- 2. honest-null on unknowns --------------------------------------------


def test_s6_unknown_key_flags_not_incompatible() -> None:
    rel = _rel(src_camelot=None, dst_camelot="9A")
    assert "key_unknown" in rel.harmonic_flags
    assert rel.harmonic_clash is False  # unknown is NOT a clash


def test_s6_unknown_bpm_yields_none_deltas() -> None:
    rel = _rel(src_bpm=None, dst_bpm=133.0)
    assert rel.bpm_delta_pct is None
    assert rel.bpm_delta_signed is None
    assert "bpm_unknown" in rel.tempo_flags


def test_s6_zero_bpm_treated_as_unknown() -> None:
    rel = _rel(src_bpm=0.0, dst_bpm=133.0)
    assert rel.bpm_delta_pct is None


# --- 3. derived policy helpers ---------------------------------------------


def test_s6_harmonic_compatible_neighbour() -> None:
    rel = _rel(src_camelot="8A", dst_camelot="9A")  # neighbour, score 0.88
    assert rel.harmonic_compatible is True


def test_s6_harmonic_clash_not_compatible() -> None:
    # Same-letter, far hour-distance with a real clash → score 0.12, flagged.
    rel = _rel(src_camelot="1A", dst_camelot="7A")
    if rel.harmonic_clash:
        assert rel.harmonic_compatible is False
    assert rel.harmonic < HARMONIC_COMPATIBLE_FLOOR


def test_s6_bpm_delta_signed() -> None:
    assert _rel(src_bpm=128.0, dst_bpm=133.0).bpm_delta_signed == 5.0
    assert _rel(src_bpm=133.0, dst_bpm=128.0).bpm_delta_signed == -5.0


def test_s6_bpm_delta_pct_uses_nearest_octave_fold() -> None:
    assert _rel(src_bpm=87.0, dst_bpm=174.0).bpm_delta_pct == pytest.approx(0.0)
    assert _rel(src_bpm=174.0, dst_bpm=87.0).bpm_delta_pct == pytest.approx(0.0)


# --- 4. why() — the live-voicing substrate ---------------------------------


def test_s6_why_full_phrase() -> None:
    assert (
        _rel(src_camelot="8A", dst_camelot="9A", src_bpm=128.0, dst_bpm=133.0).why()
        == "8A→9A, +5 BPM"
    )


def test_s6_why_same_key_no_arrow() -> None:
    rel = _rel(src_camelot="8A", dst_camelot="8A", src_bpm=128.0, dst_bpm=128.0)
    assert rel.why() == "8A, same BPM"


def test_s6_why_negative_bpm() -> None:
    assert _rel(src_bpm=133.0, dst_bpm=128.0).why().endswith("-5 BPM")


def test_s6_why_names_half_double_time() -> None:
    assert (
        _rel(src_camelot=None, dst_camelot=None, src_bpm=87.0, dst_bpm=174.0).why()
        == "double-time BPM"
    )
    assert (
        _rel(src_camelot=None, dst_camelot=None, src_bpm=174.0, dst_bpm=87.0).why()
        == "half-time BPM"
    )


def test_s6_why_empty_when_all_unknown() -> None:
    assert _rel(src_camelot=None, dst_camelot=None, src_bpm=None, dst_bpm=None).why() == ""


def test_s6_why_carries_no_dsl_or_citation_chars() -> None:
    why = _rel().why()
    assert "[" not in why and "]" not in why
