# SPDX-License-Identifier: Apache-2.0
"""Owned-deck beatmatch practice producer tests."""

from __future__ import annotations

import numpy as np

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState, MiniDeck
from vibemix.learn.practice_loop import (
    BEATMATCH_GRADED_EVENT,
    grade_minideck_beatmatch_attempt,
    grade_owned_beatmatch_attempt,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree
from vibemix.state.evidence_registry import EvidenceRegistry

_NOW = "2026-06-02T12:00:00Z"
_T = 42.4
_SR = 44100


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


def test_locked_owned_deck_grade_emits_cited_event_and_credits_beatmatching() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    grid = _grid()

    result = grade_owned_beatmatch_attempt(
        grid,
        grid,
        DeckState(a_frame=0.0, b_frame=0.0, rate_a=1.0, rate_b=1.0, xfader=0.5),
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "locked"
    assert result.event is not None
    assert result.event.type == BEATMATCH_GRADED_EVENT
    assert result.event.extra["tempo_matched"] is True
    assert result.event.extra["phase_locked"] is True
    assert result.event.extra["abstain"] is False
    assert registry.has("ev", BEATMATCH_GRADED_EVENT, _T, tol=1.0)
    assert result.credited == ("beatmatching",)
    assert _count(progress, "beatmatching") == 1


def test_locked_grade_writes_receipt_but_competent_gate_still_blocks_credit() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    grid = _grid()

    result = grade_owned_beatmatch_attempt(
        grid,
        grid,
        DeckState(a_frame=0.0, b_frame=0.0, rate_a=1.0, rate_b=1.0, xfader=0.5),
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.event is not None
    assert registry.has("ev", BEATMATCH_GRADED_EVENT, _T, tol=1.0)
    assert result.credited == ()
    assert _count(progress, "beatmatching") == 0


def test_trainwreck_grade_emits_no_creditable_event_or_receipt() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    grid = _grid()
    beat_len = grid.beat_len_frames

    result = grade_owned_beatmatch_attempt(
        grid,
        grid,
        DeckState(a_frame=0.0, b_frame=beat_len * 0.25, rate_a=1.0, rate_b=1.0, xfader=0.5),
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "trainwreck"
    assert result.event is None
    assert result.credited == ()
    assert not registry.has("ev", BEATMATCH_GRADED_EVENT, _T, tol=1.0)
    assert _count(progress, "beatmatching") == 0


def test_tempo_off_grade_emits_no_creditable_event_or_receipt() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    grid = _grid()

    result = grade_owned_beatmatch_attempt(
        grid,
        grid,
        DeckState(a_frame=0.0, b_frame=0.0, rate_a=1.0, rate_b=1.2, xfader=0.5),
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "tempo_off"
    assert result.event is None
    assert result.credited == ()
    assert not registry.has("ev", BEATMATCH_GRADED_EVENT, _T, tol=1.0)


def test_abstain_grade_emits_no_creditable_event_or_receipt() -> None:
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    grid = _grid()

    result = grade_owned_beatmatch_attempt(
        grid,
        grid,
        DeckState(a_frame=0.0, b_frame=0.0, rate_a=1.0, rate_b=0.0, xfader=0.5),
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.abstain is True
    assert result.event is None
    assert result.credited == ()
    assert not registry.has("ev", BEATMATCH_GRADED_EVENT, _T, tol=1.0)


def test_minideck_wrapper_uses_owned_deck_state() -> None:
    src = np.zeros((256, 2), dtype=np.float32)
    deck = MiniDeck(src, src, rate_a=1.0, rate_b=1.0, xfader=0.5)
    registry = EvidenceRegistry()
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    grid = _grid()

    result = grade_minideck_beatmatch_attempt(
        deck,
        grid,
        grid,
        evidence_registry=registry,
        t_session=_T,
        progress=progress,
        now=_NOW,
    )

    assert result.grade.verdict == "locked"
    assert result.event is not None
    assert result.credited == ("beatmatching",)
