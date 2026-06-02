# SPDX-License-Identifier: Apache-2.0
"""The keystone: a cited Judge verdict makes harmonic_mixing Mastered-creditable.

Until v11.0 the Judge, harmonic_mixing had no clean citable production event.
The Vibe Judge supplies one: a
``transition_judged`` event whose verdict carries a COMPATIBLE harmonic component
(the DJ mixed in key) is a genuine harmonic-mixing demonstration. Crediting is
still gated three ways: the move must be cited (MAST-03), Competent first
(MAST-01), and the keys actually compatible (a clash is NOT a demonstration).

The transition Judge still never credits beatmatching: it measures no tempo/phase
signal. Beatmatching has its own owned-deck ``BEATMATCH_GRADED`` producer, so
crediting it off bass-collision would be the exact proxy-slop the product refuses.
"""
from __future__ import annotations

from types import SimpleNamespace

from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_recognizer import recognize
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree

_NOW = "2026-05-30T12:00:00Z"
_T = 128.4


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


def _judge_event(harmonic: float):
    return SimpleNamespace(
        type="transition_judged", extra={"components": {"harmonic": harmonic}}
    )


def _count(progress: LearnProgress, skill_id: str) -> int:
    return int(progress.skills.get(skill_id, {}).get("live_proof_count", 0) or 0)


def test_cited_compatible_verdict_credits_harmonic_mixing():
    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")
    credited = recognize(
        _judge_event(0.75), citation_check=_cited, progress=progress, now=_NOW, event_t=_T
    )
    assert "harmonic_mixing" in credited
    assert _count(progress, "harmonic_mixing") == 1


def test_clash_verdict_does_not_credit_harmonic_mixing():
    # A measured CLASH (0.0) proves the DJ did NOT mix in key — no credit.
    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")
    credited = recognize(
        _judge_event(0.0), citation_check=_cited, progress=progress, now=_NOW, event_t=_T
    )
    assert credited == []
    assert _count(progress, "harmonic_mixing") == 0


def test_uncited_verdict_grants_zero_credit():
    # MAST-03: even a compatible verdict, un-cited, credits nothing.
    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")
    credited = recognize(
        _judge_event(0.75), citation_check=_uncited, progress=progress, now=_NOW, event_t=_T
    )
    assert credited == []


def test_judge_never_credits_beatmatching():
    # No tempo/phase signal exists in this Judge; beatmatching credits only via
    # the owned-deck BEATMATCH_GRADED producer.
    progress = LearnProgress()
    _make_competent(progress, "beatmatching")
    credited = recognize(
        _judge_event(0.75), citation_check=_cited, progress=progress, now=_NOW, event_t=_T
    )
    assert "beatmatching" not in credited
    assert _count(progress, "beatmatching") == 0
