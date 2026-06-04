# SPDX-License-Identifier: Apache-2.0
"""Control-practice receipt tests."""
from __future__ import annotations

from vibemix.learn.control_practice import (
    CONTROL_PRACTICE_GRADED_EVENT,
    classify_control_skill,
    grade_matched_control_practice,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST
from vibemix.state.evidence_registry import EvidenceRegistry

_NOW = "2026-06-04T12:00:00Z"


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-04T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def test_classify_control_skill_keeps_hotcue_with_cue_grader() -> None:
    assert classify_control_skill("eq_low") == "eq_mixing"
    assert classify_control_skill("filter:B") == "eq_mixing"
    assert classify_control_skill("master_vol") == "deck_control"
    assert classify_control_skill("xfader") == "deck_control"
    assert classify_control_skill("hotcue") is None


def test_matched_eq_control_writes_receipt_and_credits_competent_skill() -> None:
    progress = LearnProgress()
    _make_competent(progress, "eq_mixing")
    registry = EvidenceRegistry()

    result = grade_matched_control_practice(
        expected={"type": "cc", "control": "eq_low", "deck": "A"},
        midi={"type": "cc", "control": "eq_low", "deck": "A", "source": "mouse"},
        evidence_registry=registry,
        t_session=22.5,
        progress=progress,
        now=_NOW,
        lesson_id="L2.04",
    )

    assert result.event is not None
    assert result.event.type == CONTROL_PRACTICE_GRADED_EVENT
    assert result.skill_id == "eq_mixing"
    assert result.credited == ("eq_mixing",)
    assert registry.has("ev", CONTROL_PRACTICE_GRADED_EVENT, 22.5, tol=1.0)
    assert progress.skills["eq_mixing"]["live_proof_count"] == 1


def test_mismatched_or_unclassified_control_writes_no_receipt() -> None:
    progress = LearnProgress()
    _make_competent(progress, "deck_control")
    registry = EvidenceRegistry()

    mismatched = grade_matched_control_practice(
        expected={"type": "cc", "control": "master_vol"},
        midi={"type": "cc", "control": "xfader"},
        evidence_registry=registry,
        t_session=10.0,
        progress=progress,
        now=_NOW,
        lesson_id="L1.09",
    )
    hotcue = grade_matched_control_practice(
        expected=None,
        midi={"type": "button", "control": "hotcue", "deck": "B"},
        evidence_registry=registry,
        t_session=11.0,
        progress=progress,
        now=_NOW,
        lesson_id="L2.10",
    )

    assert mismatched.event is None
    assert hotcue.event is None
    assert not registry.has("ev", CONTROL_PRACTICE_GRADED_EVENT, 10.0, tol=1.0)
    assert not registry.has("ev", CONTROL_PRACTICE_GRADED_EVENT, 11.0, tol=1.0)
    assert progress.skills.get("deck_control", {}).get("live_proof_count", 0) == 0
