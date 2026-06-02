# SPDX-License-Identifier: Apache-2.0
"""Owned-deck cue placement practice producer tests."""

from __future__ import annotations

from vibemix.audio.grid import BeatGrid
from vibemix.learn.cue_practice import (
    CUE_PLACEMENT_GRADED_EVENT,
    grade_owned_cue_placement_attempt,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree
from vibemix.state.evidence_registry import EvidenceRegistry

_NOW = "2026-06-02T12:00:00Z"
_T = 56.2
_SR = 48000


def _grid(bpm: float = 128.0) -> BeatGrid:
    return BeatGrid(anchor_frame=0.0, bpm=bpm, sample_rate=_SR)


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)
    assert SkillTree().compute(progress)[skill_id].competent is True


def _count(progress: LearnProgress, skill_id: str) -> int:
    return int(progress.skills.get(skill_id, {}).get("live_proof_count", 0) or 0)


def test_drop_locked_cue_writes_cited_event_and_credits_phrasing() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "phrasing_performance")
    grid = _grid()
    target = grid.beat_at(32)

    result = grade_owned_cue_placement_attempt(
        grid,
        target,
        target_frame=target,
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "drop_locked"
    assert result.event is not None
    assert result.event.type == CUE_PLACEMENT_GRADED_EVENT
    assert result.event.extra["beat_aligned"] is True
    assert result.event.extra["target_aligned"] is True
    assert registry.has("ev", CUE_PLACEMENT_GRADED_EVENT, _T, tol=1.0)
    assert result.credited == ("phrasing_performance",)
    assert _count(progress, "phrasing_performance") == 1
    assert _count(progress, "beatmatching") == 0


def test_beat_locked_cue_without_target_still_proves_phrasing() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "phrasing_performance")
    grid = _grid()

    result = grade_owned_cue_placement_attempt(
        grid,
        grid.beat_at(8),
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "beat_locked"
    assert result.event is not None
    assert result.credited == ("phrasing_performance",)
    assert registry.has("ev", CUE_PLACEMENT_GRADED_EVENT, _T, tol=1.0)


def test_wrong_drop_writes_no_creditable_event_or_receipt() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "phrasing_performance")
    grid = _grid()
    target = grid.beat_at(16)

    result = grade_owned_cue_placement_attempt(
        grid,
        grid.beat_at(17),
        target_frame=target,
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "wrong_drop"
    assert result.event is None
    assert result.credited == ()
    assert not registry.has("ev", CUE_PLACEMENT_GRADED_EVENT, _T, tol=1.0)
    assert _count(progress, "phrasing_performance") == 0


def test_offbeat_cue_writes_no_creditable_event_or_receipt() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "phrasing_performance")
    grid = _grid()

    result = grade_owned_cue_placement_attempt(
        grid,
        grid.beat_at(4) + 0.2 * grid.beat_len_frames,
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "off_beat"
    assert result.event is None
    assert result.credited == ()
    assert not registry.has("ev", CUE_PLACEMENT_GRADED_EVENT, _T, tol=1.0)
