# SPDX-License-Identifier: Apache-2.0
"""The moat lands: a cited owned-deck Beatmatch Judge verdict makes beatmatching
Mastered-creditable — the v11.0 signal ``skill_recognizer`` was explicitly waiting for.

Until the Judge shipped, beatmatching was the sole honest-uncreditable skill: no
tempo/phase signal existed, so any credit would be proxy-slop (Finding #1, the
``_HONEST_UNCREDITABLE_V11`` guard literally says *"Stays uncreditable until the
deferred beatmatch_phase Judge signal ships."*). The owned-deck Judge
(``learn/beatmatch_judge.py``) is that signal: because the learning module OWNS
both decks it knows each deck's exact beat phase, so a ``BEATMATCH_GRADED`` event
carrying a LOCKED grade (tempo matched AND phase locked, not abstaining) is a
genuine, measured beatmatch demonstration — not an inference.

Crediting stays gated exactly like the harmonic keystone (``test_judge_credits_
harmonic.py``): the grade must be cited (MAST-03), Competent first (MAST-01), and
actually LOCKED — a trainwreck / drift / tempo-off / abstain is NOT a
demonstration (it proves the opposite), so it credits nothing.
"""
from __future__ import annotations

from types import SimpleNamespace

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState
from vibemix.learn.beatmatch_judge import grade_beatmatch, grade_to_event_extra
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_recognizer import recognize
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree

_NOW = "2026-05-31T12:00:00Z"
_T = 64.2  # session-relative citation t (the live caller supplies this)


def _cited(_s: str, _k: str, _t: float) -> bool:
    return True


def _uncited(_s: str, _k: str, _t: float) -> bool:
    return False


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lid in spec.lesson_ids:
        progress.lessons[lid] = {
            "completed": True, "completed_at": "2026-05-30T00:00:00Z", "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)
    assert SkillTree().compute(progress)[skill_id].competent is True


def _grade_event(
    *, abstain: bool = False, tempo_matched: bool = True,
    phase_locked: bool = True, verdict: str = "locked",
):
    """A synthetic BEATMATCH_GRADED event carrying the Judge's load-bearing fields."""
    return SimpleNamespace(
        type="BEATMATCH_GRADED",
        extra={
            "abstain": abstain, "tempo_matched": tempo_matched,
            "phase_locked": phase_locked, "verdict": verdict,
        },
    )


def _count(progress: LearnProgress, skill_id: str) -> int:
    return int(progress.skills.get(skill_id, {}).get("live_proof_count", 0) or 0)


def test_cited_locked_grade_credits_beatmatching() -> None:
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    credited = recognize(
        _grade_event(), citation_check=_cited, progress=progress, now=_NOW, event_t=_T
    )
    assert "beatmatching" in credited
    assert _count(progress, "beatmatching") == 1


def test_trainwreck_grade_does_not_credit() -> None:
    # tempo matched but phase way out — a trainwreck is not a demonstration.
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    ev = _grade_event(tempo_matched=True, phase_locked=False, verdict="trainwreck")
    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW, event_t=_T)
    assert credited == []
    assert _count(progress, "beatmatching") == 0


def test_drifting_grade_does_not_credit() -> None:
    # tempo matched, phase within the trainwreck band but NOT locked — not mastery.
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    ev = _grade_event(tempo_matched=True, phase_locked=False, verdict="drifting")
    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW, event_t=_T)
    assert credited == []


def test_tempo_off_grade_does_not_credit() -> None:
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    ev = _grade_event(tempo_matched=False, phase_locked=False, verdict="tempo_off")
    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW, event_t=_T)
    assert credited == []


def test_abstain_grade_does_not_credit() -> None:
    # A stopped deck -> abstain -> nothing to demonstrate.
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    ev = _grade_event(abstain=True, tempo_matched=False, phase_locked=False, verdict="abstain")
    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW, event_t=_T)
    assert credited == []


def test_uncited_locked_grade_grants_zero_credit() -> None:
    # MAST-03: even a perfect locked grade, un-cited, moves no bar.
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    credited = recognize(
        _grade_event(), citation_check=_uncited, progress=progress, now=_NOW, event_t=_T
    )
    assert credited == []
    assert _count(progress, "beatmatching") == 0


def test_locked_grade_requires_competent_first() -> None:
    # MAST-01: a not-yet-Competent beatmatching ignores even a cited locked grade.
    progress = LearnProgress()  # no lessons, no gate -> the skill is still locked
    credited = recognize(
        _grade_event(), citation_check=_cited, progress=progress, now=_NOW, event_t=_T
    )
    assert credited == []
    assert _count(progress, "beatmatching") == 0


def test_real_judge_grade_credits_end_to_end() -> None:
    # The full chain the live practice loop runs: owned-deck grade ->
    # canonical event extra -> recognizer credit. Identical phase-aligned decks
    # at rate 1.0 grade "locked".
    sr = 44100
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=sr)
    state = DeckState(a_frame=0.0, b_frame=0.0, rate_a=1.0, rate_b=1.0, xfader=0.5)
    grade = grade_beatmatch(grid, grid, state)
    assert grade.verdict == "locked"

    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    ev = SimpleNamespace(type="BEATMATCH_GRADED", extra=grade_to_event_extra(grade))
    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW, event_t=_T)
    assert credited == ["beatmatching"]
    assert _count(progress, "beatmatching") == 1


def test_real_trainwreck_grade_credits_nothing_end_to_end() -> None:
    # Deck B a quarter-beat out of phase grades "trainwreck" -> no credit, even
    # though the tempo matches. The owned-deck ground truth refuses the slop.
    sr = 44100
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=sr)
    beat_len = 60.0 * sr / 128.0
    state = DeckState(
        a_frame=0.0, b_frame=beat_len * 0.25, rate_a=1.0, rate_b=1.0, xfader=0.5
    )
    grade = grade_beatmatch(grid, grid, state)
    assert grade.verdict == "trainwreck"

    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    ev = SimpleNamespace(type="BEATMATCH_GRADED", extra=grade_to_event_extra(grade))
    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW, event_t=_T)
    assert credited == []
