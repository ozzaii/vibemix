# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from vibemix.intel.move_grade import grade_transition, grade_transition_payload


def _scores(**overrides: float) -> dict[str, float]:
    base = {
        "semantic": 0.88,
        "harmonic": 0.88,
        "bpm": 0.9,
        "energy_shape": 0.86,
        "role": 0.9,
        "phrase_alignment": 0.9,
        "cue_operability": 0.9,
        "taste": 0.5,
        "novelty": 0.5,
        "risk_penalty": 0.0,
    }
    base.update(overrides)
    return base


def test_lit_aff_requires_high_score_confidence_and_no_risks() -> None:
    grade = grade_transition(
        score=0.91,
        confidence=0.9,
        components=_scores(),
        risk_flags=(),
    ).to_dict()

    assert grade["slug"] == "lit_aff"
    assert grade["label"] == "LIT AFF"
    assert grade["xp"] == 100
    assert grade["deserved"] is True
    assert grade["overdrive"] is True


def test_severe_risk_turns_a_weak_fit_negative() -> None:
    grade = grade_transition(
        score=0.61,
        confidence=0.74,
        components=_scores(harmonic=0.12, risk_penalty=0.5),
        risk_flags=("harmonic_clash",),
    ).to_dict()

    assert grade["slug"] == "negative"
    assert grade["label"] == "NEG"
    assert grade["reason"] == "key clash"
    assert grade["xp"] == 0


def test_mid_is_the_honest_fallback_when_it_works_but_does_not_click() -> None:
    grade = grade_transition(
        score=0.58,
        confidence=0.61,
        components=_scores(energy_shape=0.52, phrase_alignment=0.55, cue_operability=0.55),
        risk_flags=("timing_low_confidence",),
    ).to_dict()

    assert grade["slug"] == "mid"
    assert grade["reason"] == "timing needs care"
    assert grade["deserved"] is False


def test_auto_cue_review_stays_care_even_with_strong_scores() -> None:
    grade = grade_transition(
        score=0.86,
        confidence=0.82,
        components=_scores(risk_penalty=0.04),
        risk_flags=("auto_cue_review",),
    ).to_dict()

    assert grade["slug"] == "mid"
    assert grade["reason"] == "auto cue needs review"
    assert grade["deserved"] is False
    assert grade["xp"] == 8


def test_low_cue_confidence_uses_transition_scorer_flag_name() -> None:
    grade = grade_transition(
        score=0.76,
        confidence=0.72,
        components=_scores(cue_operability=0.63, risk_penalty=0.1),
        risk_flags=("low_cue_confidence",),
    ).to_dict()

    assert grade["slug"] == "mid"
    assert grade["reason"] == "cue confidence low"
    assert grade["deserved"] is False


def test_payload_grading_degrades_nonfinite_values() -> None:
    assert grade_transition_payload(None) is None
    grade = grade_transition_payload(
        {
            "score": float("nan"),
            "confidence": float("inf"),
            "scores": {"semantic": 0.8},
            "risk_flags": ["tempo_jump"],
        }
    )

    assert grade is not None
    assert grade["slug"] == "negative"
    assert grade["confidence"] == 0.0


def test_pill_vocabulary_json_matches_backend_grade_contract() -> None:
    """Pin the pill UI vocabulary to the backend grade contract."""
    contract_path = (
        Path(__file__).resolve().parents[2]
        / "tauri"
        / "ui"
        / "src"
        / "pill"
        / "move-grade-vocabulary.json"
    )
    pill_contract = json.loads(contract_path.read_text(encoding="utf-8"))

    cases = {
        "negative": grade_transition(
            score=0.61,
            confidence=0.74,
            components=_scores(harmonic=0.12, risk_penalty=0.5),
            risk_flags=("harmonic_clash",),
        ).to_dict(),
        "mid": grade_transition(
            score=0.58,
            confidence=0.61,
            components=_scores(energy_shape=0.52, phrase_alignment=0.55, cue_operability=0.55),
            risk_flags=("timing_low_confidence",),
        ).to_dict(),
        "clean": grade_transition(
            score=0.65,
            confidence=0.65,
            components=_scores(
                semantic=0.60,
                harmonic=0.72,
                bpm=0.72,
                energy_shape=0.64,
                role=0.72,
                phrase_alignment=0.72,
                cue_operability=0.72,
            ),
            risk_flags=(),
        ).to_dict(),
        "sexy": grade_transition(
            score=0.78,
            confidence=0.72,
            components=_scores(
                semantic=0.70,
                harmonic=0.70,
                bpm=0.70,
                energy_shape=0.70,
                role=0.70,
                phrase_alignment=0.70,
                cue_operability=0.70,
            ),
            risk_flags=(),
        ).to_dict(),
        "bomb": grade_transition(
            score=0.85,
            confidence=0.80,
            components=_scores(
                semantic=0.75,
                harmonic=0.75,
                bpm=0.75,
                energy_shape=0.75,
                role=0.75,
                phrase_alignment=0.75,
                cue_operability=0.75,
            ),
            risk_flags=(),
        ).to_dict(),
        "lit_aff": grade_transition(
            score=0.91,
            confidence=0.90,
            components=_scores(),
            risk_flags=(),
        ).to_dict(),
    }

    assert list(pill_contract) == ["negative", "mid", "clean", "sexy", "bomb", "lit_aff"]
    for slug, grade in cases.items():
        assert grade["slug"] == slug
        assert pill_contract[slug]["label"] == grade["label"]
        assert pill_contract[slug]["xp"] == grade["xp"]
        assert pill_contract[slug]["intensity"] == grade["intensity"]
        assert pill_contract[slug]["sentiment"] == grade["sentiment"]
        assert pill_contract[slug]["deserved"] == grade["deserved"]
        assert pill_contract[slug]["overdrive"] == grade["overdrive"]
