# SPDX-License-Identifier: Apache-2.0
"""BENCH-03 — review-render scaffolds (flip in Plan 04 = the review surface).

``render_review(results, scores) -> str`` is a pure JSON→Markdown transform: it
ranks cells by auto-score, groups by study/dimension, and renders each cell's
prompt + output + auto-scores. The cardinal rule (Pitfall 5): the VERDICT
section is present but EMPTY — no code path writes a winner. Kaan's ear fills it.
An errored cell renders as ``ERRORED — parked``, never as fake output
(81-RESEARCH Security: the fabricated-cell-filling-a-gap cardinal sin).

Each assertion is ``xfail(strict=True)`` until Plan 04 lands ``vibemix.bench.review``.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(strict=True, reason="bench/review.render_review lands in Plan 04")
def test_verdict_section_present_but_empty() -> None:
    """The VERDICT section exists with the 'Kaan fills this' placeholder and NO
    winner/verdict line — the auto-rank is a sort, not a decision."""
    from vibemix.bench.review import render_review

    md = render_review(results=[], scores=[])
    assert "VERDICT" in md
    assert "Kaan fills this" in md
    # No code path synthesizes a winner.
    lowered = md.lower()
    assert "winner:" not in lowered
    assert "the winner is" not in lowered


@pytest.mark.xfail(strict=True, reason="bench/review render lands in Plan 04")
def test_errored_cell_renders_as_parked() -> None:
    """An errored cell renders as 'ERRORED — parked', never as fabricated output."""
    from vibemix.bench.cell import BenchResult
    from vibemix.bench.eval import score_cell
    from vibemix.bench.review import render_review

    errored = BenchResult(
        prompt="...",
        output="",
        dsp_snapshot=None,
        usage={},
        error="429 RESOURCE_EXHAUSTED",
    )
    md = render_review(results=[errored], scores=[score_cell({"output": "", "dsp_snapshot": None})])
    assert "ERRORED" in md and "parked" in md


@pytest.mark.xfail(strict=True, reason="bench/review ranking lands in Plan 04")
def test_render_ranks_and_groups() -> None:
    """The render produces Markdown that ranks cells by auto-score and groups
    by study/dimension (a non-empty, structured surface)."""
    from vibemix.bench.cell import BenchResult
    from vibemix.bench.eval import score_cell
    from vibemix.bench.review import render_review

    from tests.bench.conftest import _grounded_snapshot

    snap = _grounded_snapshot()
    r_hi = BenchResult(
        prompt="p1",
        output="that 128 bpm 303 line opened up [aud:bpm@0.0]",
        dsp_snapshot=snap,
        usage={},
        error=None,
    )
    r_lo = BenchResult(
        prompt="p2",
        output="As an AI, the track continues.",
        dsp_snapshot=snap,
        usage={},
        error=None,
    )
    results = [r_lo, r_hi]
    scores = [score_cell({"output": r.output, "dsp_snapshot": r.dsp_snapshot}) for r in results]
    md = render_review(results=results, scores=scores)
    assert md.strip() != ""
    # The high-groundedness cell's output appears in the surface.
    assert "303 line opened up" in md
