# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from vibemix.intel.musical_ontology import (
    VALID_ROLES,
    normalize_genre,
    normalize_role,
    risk_penalty,
    role_pair_risks,
    role_pair_score,
)


def test_role_vocabulary_contains_canonical_section_roles() -> None:
    assert {
        "intro",
        "groove",
        "build",
        "breakdown",
        "drop",
        "outro",
        "bridge",
        "unknown",
    } <= VALID_ROLES


def test_normalize_role_degrades_to_unknown() -> None:
    assert normalize_role(" Drop ") == "drop"
    assert normalize_role("verse") == "unknown"
    assert normalize_role(None) == "unknown"


def test_role_pair_score_uses_base_matrix() -> None:
    assert role_pair_score("outro", "intro", None) == pytest.approx(0.95)
    assert role_pair_score("unknown", "intro", None) == pytest.approx(0.35)


def test_role_pair_score_uses_genre_modifier() -> None:
    neutral = role_pair_score("outro", "groove", None)
    techno = role_pair_score("outro", "groove", "techno")

    assert techno > neutral


def test_normalize_genre_aliases_common_profiles() -> None:
    assert normalize_genre("tech house") == "house"
    assert normalize_genre("hard-tek") == "hard_tek"
    assert normalize_genre("DnB") == "dnb"


def test_role_pair_risks_are_structured() -> None:
    assert "drop_stack_fatigue" in role_pair_risks("drop", "drop")
    assert "role_unknown" in role_pair_risks("verse", "intro")


def test_risk_penalty_caps_at_intel_floor() -> None:
    flags = {
        "harmonic_clash",
        "tempo_jump",
        "off_phrase",
        "timing_low_confidence",
    }

    assert risk_penalty(flags) == pytest.approx(0.55)
