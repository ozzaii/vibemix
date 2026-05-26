# SPDX-License-Identifier: Apache-2.0
"""BENCH-02 — automated first-pass eval scaffolds (flip in Plan 03).

Three pure, deterministic scorers over a recorded cell:

* **groundedness** — REUSES ``CitationLinter.check(..., mode="debrief")`` against
  the cell's OWN dsp_snapshot (do NOT re-implement — the linter IS the product's
  anti-slop gate, Invariant #2). A cell citing an atom present in its snapshot
  scores high; a fabricated atom absent from the snapshot scores 0.
* **specificity** — penalizes ``NEGATIVE_PHRASES`` hits, rewards concrete
  measures (``128 bpm``). Deterministic.
* **lens-fidelity** — a hype-vocab line scores higher under ``lens="hype"`` than
  a flat line. Deterministic.

The auto-score RANKS; it does NOT decide (Pitfall 5 — Kaan's ear is the verdict).
Each assertion is ``xfail(strict=True)`` until Plan 03 lands ``vibemix.bench.eval``.
The grounded/fabricated contract is pre-verified against the REAL linter in
conftest's snapshot builders, so these flip to real-green when the scorers ship.
"""

from __future__ import annotations

import pytest

from tests.bench.conftest import _grounded_snapshot


def _result(output: str, snapshot):
    """A minimal recorded-cell stand-in for the scorers (Plan 03 supplies the
    real BenchResult ctor; this dict mirrors its scored fields)."""
    return {"output": output, "dsp_snapshot": snapshot}


@pytest.mark.xfail(strict=True, reason="bench/eval.groundedness lands in Plan 03")
def test_groundedness() -> None:
    """A cell citing an atom PRESENT in its snapshot scores high; a fabricated
    [aud:...] absent from the snapshot scores 0 — via CitationLinter (debrief)."""
    from vibemix.bench.eval import groundedness

    snap = _grounded_snapshot()  # carries aud/bpm@0.0 + aud/sub@0.0
    grounded = groundedness(_result("that 303 line opened up [aud:bpm@0.0]", snap))
    fabricated = groundedness(_result("phantom drop hit [aud:bpm@99.0]", snap))
    assert grounded > fabricated
    assert grounded >= 1.0
    assert fabricated == 0.0


@pytest.mark.xfail(strict=True, reason="bench/eval.specificity lands in Plan 03")
def test_specificity() -> None:
    """Specificity penalizes a NEGATIVE_PHRASES hit and rewards a concrete
    measure (128 bpm) — deterministic, no API."""
    from vibemix.bench.eval import specificity

    sloppy = specificity("As an AI, I'm here to help with your music.")
    concrete = specificity("that 128 bpm kick is hammering the sub")
    assert concrete > sloppy


@pytest.mark.xfail(strict=True, reason="bench/eval.lens_fidelity lands in Plan 03")
def test_lens_fidelity() -> None:
    """Lens-fidelity scores a hype-vocab line higher under lens='hype' than a
    flat, vocabulary-less line."""
    from vibemix.bench.eval import lens_fidelity

    hype_line = lens_fidelity("that drop is sick, the energy is cooking", "hype")
    flat_line = lens_fidelity("the track continues at a steady tempo", "hype")
    assert hype_line > flat_line


@pytest.mark.xfail(strict=True, reason="bench/eval.score_cell lands in Plan 03")
def test_score_cell_ranks_not_decides() -> None:
    """score_cell returns a CellScore with the three dimensions — a RANKING
    signal, never a verdict (no 'winner'/'decision' field)."""
    from vibemix.bench.eval import score_cell

    snap = _grounded_snapshot()
    score = score_cell(_result("that 128 bpm 303 line opened up [aud:bpm@0.0]", snap))
    # All three dimensions present.
    assert hasattr(score, "groundedness")
    assert hasattr(score, "specificity")
    assert hasattr(score, "lens_fidelity")
    # The score is a sort key, not a decision — no winner field.
    assert not hasattr(score, "winner")
    assert not hasattr(score, "verdict")
