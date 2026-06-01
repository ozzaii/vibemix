# SPDX-License-Identifier: Apache-2.0
"""Tests for the Judge voice-line renderer — the engine half of "voice the Judge".

`intel/judge_voice.py::verdict_evidence_line` turns a ``TransitionVerdict`` into the
compact, grounded evidence line the live prompt feeds the LLM, so the co-host
narrates what the Judge MEASURED (compatible keys / a key clash / clean low end /
bass mud) instead of the stale TrackRelation blend it carries today. Pure: no I/O,
no model, no registry — same import-light discipline as the rest of ``intel/``.

Contract under test:
  * abstained verdict -> ``None`` (abstain-first; nothing was measured to voice —
    Invariant #3, trust the audio / never invent).
  * judged verdict   -> a line that (a) carries the grounded ``[judge:transition@t]``
    citation atom, (b) reflects the measured components (compatible vs clash, clean
    low-end vs mud), (c) SURVIVES the production slop filter (``prompts/filter.py``)
    untouched — else the Judge's own grade could be the phrase that silences the turn.
"""
from __future__ import annotations

from vibemix.intel.judge_voice import verdict_evidence_line
from vibemix.intel.transition_judge import TransitionVerdict
from vibemix.prompts.filter import filter_for_slop

# Exactly the id ``transition_judge_runtime.judge_and_record`` grounds for a judged
# verdict: ``f"{JUDGE_CITATION_SOURCE}:{key}"`` -> ``judge:transition@<t>``.
_CITATION = "judge:transition@128.4"


def _judged(
    components: dict[str, float], *, score: float, risk_flags: tuple[str, ...] = ()
) -> TransitionVerdict:
    return TransitionVerdict(
        verdict_state="judged",
        score=score,
        confidence=1.0,
        components=components,
        risk_flags=risk_flags,
    )


def test_abstained_verdict_yields_no_line() -> None:
    """The honest-null path: an abstain has nothing measured to voice."""
    verdict = TransitionVerdict(
        verdict_state="abstained",
        score=None,
        confidence=0.0,
        abstain_reason="routing_disabled",
    )
    assert verdict_evidence_line(verdict, citation_id=_CITATION) is None


def test_judged_clean_blend_carries_citation_and_reads_clean() -> None:
    """harmonic compatible (0.75) + one bass killed (1.0) -> a clean-reading line
    anchored by the grounded citation atom, never voiced as a clash."""
    verdict = _judged({"harmonic": 0.75, "bass_collision": 1.0}, score=0.875)
    line = verdict_evidence_line(verdict, citation_id=_CITATION)
    assert line is not None
    assert f"[{_CITATION}]" in line  # grounded, resolvable, survives the strip
    assert "clash" not in line.lower()  # a measured-clean blend never reads as a clash
    assert "clean" in line.lower() or "compatible" in line.lower()


def test_judged_clash_blend_reflects_the_measured_clash() -> None:
    """harmonic clash (0.0) + both basslines up (0.0) -> the clash + low-end mud are
    voiced, so the LLM narrates the real grade, not the stale relation."""
    verdict = _judged(
        {"harmonic": 0.0, "bass_collision": 0.0},
        score=0.0,
        risk_flags=("harmonic_clash", "bass_collision"),
    )
    line = verdict_evidence_line(verdict, citation_id=_CITATION)
    assert line is not None
    assert f"[{_CITATION}]" in line
    assert "clash" in line.lower()
    assert "mud" in line.lower() or "bass" in line.lower()


def test_judged_score_is_reflected_in_the_line() -> None:
    """The measured blend score rides the evidence line (anchor for the LLM)."""
    line = verdict_evidence_line(
        _judged({"harmonic": 0.75, "bass_collision": 1.0}, score=0.875),
        citation_id=_CITATION,
    )
    assert line is not None
    assert "0.88" in line  # round(0.875, 2)


def test_judged_line_survives_the_slop_filter() -> None:
    """The voiced evidence line must not itself trip ``prompts/filter.py`` — else the
    Judge's own grade would silence the turn. Asserted against the PRODUCTION filter;
    the filter is deliberately NOT coupled into the pure module."""
    for components, score, flags in (
        ({"harmonic": 0.75, "bass_collision": 1.0}, 0.875, ()),
        (
            {"harmonic": 0.0, "bass_collision": 0.0},
            0.0,
            ("harmonic_clash", "bass_collision"),
        ),
        ({"harmonic": 0.0, "bass_collision": 1.0}, 0.5, ("harmonic_clash",)),
        ({"harmonic": 0.75, "bass_collision": 0.0}, 0.375, ("bass_collision",)),
    ):
        line = verdict_evidence_line(
            _judged(components, score=score, risk_flags=flags), citation_id=_CITATION
        )
        assert line is not None
        filtered, matches = filter_for_slop(line)
        assert matches == [], f"slop filter tripped on {line!r}: {matches}"
        assert filtered == line  # passes through unchanged
