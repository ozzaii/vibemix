# SPDX-License-Identifier: Apache-2.0
"""Deterministic debrief-drill -> Learn referral mapping."""

from __future__ import annotations

from vibemix.debrief.learn_referral import learn_referral_for_drill


def _drill(text: str) -> dict[str, str]:
    return {
        "situation": "Post-session drill",
        "behavior": f"{text} [ev:MIX_MOVE@01:00]",
        "impact": "The blend lost clarity [aud:LOW_END@01:02]",
        "action_recommended": "Practice the exact move next time [ev:MIX_MOVE@01:00]",
        "citation": "[ev:MIX_MOVE@01:00]",
    }


def test_refers_beatmatch_drift_to_owned_deck_lesson():
    referral = learn_referral_for_drill(
        _drill("The kicks drifted apart during the beatmatch")
    )

    assert referral is not None
    assert referral.lesson_id == "L2.01"
    assert referral.title == "beatmatching by ear"
    assert referral.skill_id == "beatmatching"
    assert referral.cta == "Practice beatmatching by ear"


def test_refers_harmonic_clash_to_camelot_lesson():
    referral = learn_referral_for_drill(_drill("There was a key clash in the blend"))

    assert referral is not None
    assert referral.lesson_id == "L2.11"
    assert referral.skill_label == "harmonic mixing"


def test_refers_low_end_collision_before_generic_eq():
    referral = learn_referral_for_drill(
        _drill("Both basslines stayed up and made low-end mud")
    )

    assert referral is not None
    assert referral.lesson_id == "L2.05"
    assert referral.title == "bassline swap"


def test_refers_train_wreck_to_diagnosis_lesson():
    referral = learn_referral_for_drill(_drill("The handoff became a train wreck"))

    assert referral is not None
    assert referral.lesson_id == "L2.13"
    assert referral.title == "diagnosing a train wreck"


def test_returns_none_for_generic_non_technique_feedback():
    referral = learn_referral_for_drill(
        _drill("The room liked the second track and the energy felt warmer")
    )

    assert referral is None
