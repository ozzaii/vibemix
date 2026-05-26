# SPDX-License-Identifier: Apache-2.0
"""BENCH-02 — the automated first-pass eval (pure, offline, RANK-ONLY).

Three deterministic scorers over a recorded :class:`~vibemix.bench.cell.BenchResult`:

* **groundedness** — REUSES :meth:`CitationLinter.check` (``mode="debrief"``,
  ±2.0s offline-appropriate tolerance) against the cell's OWN ``dsp_snapshot``.
  We do NOT re-implement the linter — it IS the product's anti-slop gate
  (Invariant #2), so reusing it keeps the bench honest to the SHIPPED behavior.
  A cell citing an atom present in its snapshot scores ``1.0`` (reason
  ``"valid"``); ``0.5`` for ``"no_citations"`` (un-cited but not fabricated);
  ``0.0`` for a fabricated/malformed atom absent from the snapshot
  (``"invalid_atoms"`` / ``"malformed_atom"``).
* **specificity** — a deterministic heuristic over
  :data:`~vibemix.prompts.negative_dict.NEGATIVE_PHRASES` (penalize slop) +
  concrete-measure signals (reward ``128 bpm`` / ``80 hz`` / named elements).
* **lens-fidelity** — per-lens vocabulary anchors (:data:`LENS_ANCHORS`):
  a hype-vocab line scores higher under ``lens="hype"`` than a flat line.

THE CARDINAL RULE (RESEARCH Pitfall 5, T-81-07): **the eval RANKS, it never
DECIDES.** There is no ``winner`` field, no ``verdict`` field, no function that
picks an architecture. :func:`rank_cells` is a SORT — Kaan's ear is the verdict
(BENCH-03, the HARD HUMAN GATE).

An errored cell (``error`` set — the 429 fail-safe) scores all-zero and is
flagged ``errored`` so it SINKS in the rank — never silently scored high,
never fabricated.

Pure + deterministic: no network, no file I/O, no API. Scores fixture cells
identically every run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vibemix.bench.matrix import LENS_ANCHORS
from vibemix.coach.citation_linter import CitationLinter
from vibemix.prompts.negative_dict import NEGATIVE_PHRASES

# A single shared stateless linter — construction takes no args and the class is
# safe to share (see CitationLinter docstring). Reusing the product's instance
# keeps groundedness identical to the live anti-slop gate.
_LINTER = CitationLinter()

# Concrete-measure signal: a number immediately followed by a DSP unit. Rewards
# "128 bpm" / "80 hz" / "-6 db" / "16 bar" / "30s" over vague prose. Word-bounded
# so "bars" or "second" don't false-match the bare unit.
_CONCRETE_MEASURE_RE: re.Pattern[str] = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:hz|khz|bpm|db|bar|bars|beat|beats|s)\b",
    re.IGNORECASE,
)

# Weights for the SORT-ONLY aggregate. Groundedness is weighted highest because
# it is the empirical heart (the no-audio cell's groundedness is the milestone
# question). These tune the RANK order; they NEVER constitute a verdict.
_W_GROUNDEDNESS = 0.5
_W_SPECIFICITY = 0.25
_W_LENS_FIDELITY = 0.25


def _text_of(result: object) -> str:
    """Pull the recorded reaction text from a BenchResult or a dict stand-in."""
    if isinstance(result, dict):
        return str(result.get("output") or "")
    return str(getattr(result, "output", "") or "")


def _snapshot_of(result: object) -> dict | None:
    """Pull the cell's OWN DSP-fact snapshot (the grounding the linter checks)."""
    if isinstance(result, dict):
        return result.get("dsp_snapshot")
    return getattr(result, "dsp_snapshot", None)


def _error_of(result: object) -> str | None:
    """Pull the fail-safe error field (None on a successful call)."""
    if isinstance(result, dict):
        return result.get("error")
    return getattr(result, "error", None)


def _cell_of(result: object) -> object | None:
    """Pull the cell off a BenchResult OR a JSON-reloaded dict stand-in.

    WR-04: ``results_to_json`` serializes the cell as a NESTED dict
    (``result["cell"]["lens"]``), so the dict path must reach into
    ``result["cell"]`` — reading a top-level ``result["lens"]`` always missed
    and every reloaded cell fell back to the default lens/grouping.
    """
    if isinstance(result, dict):
        return result.get("cell")
    return getattr(result, "cell", None)


def _axis(cell: object | None, name: str, default: str) -> str:
    """Read one axis off a BenchCell object OR its nested-dict stand-in."""
    if cell is None:
        return default
    if isinstance(cell, dict):
        return str(cell.get(name) or default)
    return str(getattr(cell, name, None) or default)


def _lens_of(result: object) -> str:
    """Pull the cell's lens axis (hype/critique/tutor); default hype.

    Handles both the live BenchResult and a JSON-reloaded nested-dict cell
    (WR-04), so a re-scored persisted run scores its REAL lens, not the fallback.
    """
    return _axis(_cell_of(result), "lens", "hype")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp into ``[lo, hi]`` — keeps every score a comparable [0,1] sort key."""
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class CellScore:
    """The three rank dimensions + a SORT-ONLY aggregate (never a verdict).

    Frozen value type (mirrors ``LintResult`` / ``BenchCell`` convention). There
    is deliberately NO ``winner`` / ``verdict`` / ``decision`` field — the score
    is a sort key that orders cells for Kaan to read strongest-first; the verdict
    is Kaan's ear (BENCH-03). ``errored`` flags a parked (429/failed) cell so it
    sinks in the rank.
    """

    groundedness: float
    specificity: float
    lens_fidelity: float
    errored: bool = False
    # A simple weighted mean — for SORTING only. NOT a decision, NOT a verdict.
    aggregate: float = 0.0


def groundedness(result: object) -> float:
    """Score how grounded the reaction is against its OWN DSP snapshot.

    Reuses :meth:`CitationLinter.check` VERBATIM (``mode="debrief"``, ±2.0s
    offline-appropriate tolerance) — the linter is the product's anti-slop gate
    (Invariant #2); do NOT re-implement atom parsing here.

    Returns ``1.0`` for ``reason == "valid"`` (every cited atom resolves),
    ``0.5`` for ``"no_citations"`` (un-cited — not slop, but ungrounded), and
    ``0.0`` for a fabricated/malformed atom absent from the snapshot
    (``"invalid_atoms"`` / ``"malformed_atom"``). An ERRORED cell scores ``0.0``.
    """
    if _error_of(result) is not None:
        return 0.0
    res = _LINTER.check(_text_of(result), _snapshot_of(result), mode="debrief")
    if res.reason == "valid":
        return 1.0
    if res.reason == "no_citations":
        return 0.5
    return 0.0


def specificity(text: str) -> float:
    """Deterministic concreteness vs generic-AI-slop heuristic over ``text``.

    Penalizes each :data:`NEGATIVE_PHRASES` ban-list hit; rewards concrete DSP
    measures ("128 bpm", "80 hz"). A line with a slop hit scores LOWER than the
    same line without; a line with a concrete measure scores HIGHER than a vague
    one. Clamped to ``[0, 1]`` — pure + repeatable, never an API judge.
    """
    low = (text or "").lower()
    slop_hits = sum(1 for p in NEGATIVE_PHRASES if p.lower() in low)
    concrete_hits = len(_CONCRETE_MEASURE_RE.findall(low))
    # Start from a neutral floor, reward concreteness, penalize slop. Each
    # concrete measure is worth more than one slop hit costs so a sharp line with
    # an incidental ban-word still beats vague slop, but pure slop sinks.
    score = 0.3 + 0.35 * concrete_hits - 0.4 * slop_hits
    return _clamp(score)


def lens_fidelity(text: str, lens: str) -> float:
    """Score how strongly ``text`` hits the per-lens vocabulary anchors.

    Deterministic: ``clamp(hits / 2.0, 0, 1)`` over :data:`LENS_ANCHORS` for the
    cell's lens (hype/critique/tutor). A hype-vocab line scores higher under
    ``lens="hype"`` than a flat, anchor-less line. An unknown lens has no anchors
    → ``0.0`` (never raises — the eval ranks, it does not gate).
    """
    anchors = LENS_ANCHORS.get((lens or "").lower().strip(), ())
    low = (text or "").lower()
    hits = sum(1 for a in anchors if a in low)
    return _clamp(hits / 2.0)


def score_cell(result: object) -> CellScore:
    """Score one recorded cell across all three dimensions — a RANK signal.

    Pure: no network, no file I/O. An errored cell (``error`` set — the 429
    fail-safe) scores all-zero with ``errored=True`` so it SINKS in the rank
    (never fabricated-high). Otherwise composes groundedness (reused linter) +
    specificity + lens-fidelity and derives a SORT-ONLY weighted-mean
    ``aggregate``. There is NO winner/verdict — Kaan's ear decides (BENCH-03).
    """
    if _error_of(result) is not None:
        return CellScore(0.0, 0.0, 0.0, errored=True, aggregate=0.0)

    g = groundedness(result)
    s = specificity(_text_of(result))
    lf = lens_fidelity(_text_of(result), _lens_of(result))
    aggregate = (
        _W_GROUNDEDNESS * g + _W_SPECIFICITY * s + _W_LENS_FIDELITY * lf
    )
    return CellScore(
        groundedness=g,
        specificity=s,
        lens_fidelity=lf,
        errored=False,
        aggregate=aggregate,
    )


def rank_cells(
    scored: list[tuple[object, CellScore]],
) -> list[tuple[object, CellScore]]:
    """SORT ``(result, score)`` pairs by aggregate, strongest first.

    This is a SORT, not a decision. It orders cells so Kaan reads the
    strongest-scoring first — it does NOT pick a winner, emit a verdict, or
    select an architecture/model. The winning-architecture call is Kaan's ear
    (BENCH-03, the HARD HUMAN GATE); this function never makes it (Pitfall 5,
    T-81-07).
    """
    return sorted(scored, key=lambda pair: pair[1].aggregate, reverse=True)
