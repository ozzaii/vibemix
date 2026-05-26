# SPDX-License-Identifier: Apache-2.0
"""BENCH-03 — the KAAN-ACTION review surface (a pure JSON→Markdown renderer).

``render_review(results, scores) -> str`` lays the recorded bench cells out for
**Kaan's ear** (the Phase-16 hard human gate): it ranks cells by their auto-score
(strongest first, via :func:`vibemix.bench.eval.rank_cells`), groups them by the
grounding dimension (the architecture axis — the milestone question), and renders
each cell's 6-D coordinates + the three auto-scores + the assembled prompt + the
recorded output.

THE CARDINAL RULE (81-RESEARCH Pitfall 5 / T-81-09): **the auto-rank is a SORT,
not a decision.** The VERDICT section is rendered literally EMPTY — a
``> _Kaan fills this in …_`` placeholder. NO code path in this module writes a
winner, picks an architecture, or synthesizes a verdict. The acceptance grep-gate
enforces it (no winner-assigning line exists in code). Kaan's ear decides.

An ERRORED cell (the 429 / auth / network fail-safe — ``result.error`` set)
renders as ``**ERRORED — parked:** {error}``, NEVER as fabricated output
(81-RESEARCH Security: the fabricated-cell-filling-a-gap cardinal sin / T-81-10).

The render is PURE + DETERMINISTIC (81-PATTERNS "bench/review.py", precedent
``runtime/soak.py``): same inputs → byte-identical Markdown; no clock, no
randomness, no file I/O — the CALLER writes the artifact. Track filenames /
absolute paths in prompts + outputs are path-scrubbed via the Telegram-bridge
``strip_leaks`` (T-81-11 — the review surface emits scores + prompts + outputs,
never a key or a personal path).
"""

from __future__ import annotations

from vibemix.bench.eval import CellScore, rank_cells
from vibemix.library.telegram_bridge import strip_leaks

# The EXACT verdict block — the literally-empty hard human gate. NO code path
# writes anything below the placeholder. Kept as a module constant so the grep
# gate sees a fixed, decision-free string (Pitfall 5 / T-81-09).
_VERDICT_HEADING = "## VERDICT (Kaan fills this)"
_VERDICT_PLACEHOLDER = "> _Kaan fills this in — the auto-rank is a sort, not a decision._"

# Group label for cells with no recorded 6-D coordinate (parked fixtures / a
# result built without a cell). The live runner always populates ``cell``.
_UNGROUPED = "(uncategorized)"

# Truncate an over-long assembled prompt so the surface stays readable; the full
# prompt lives in the JSON artifact. Output is never truncated — Kaan judges it.
_PROMPT_MAX = 600


def _scrub(text: str) -> str:
    """Path-scrub a prompt/output fragment (T-81-11) — no personal paths leak."""
    return strip_leaks(text or "")


def _truncate(text: str, limit: int) -> str:
    """Deterministic, char-bounded truncation with an explicit elision marker."""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …[truncated]"


def _group_key(score: CellScore, result: object) -> str:
    """The dimension a cell is grouped under — its grounding (architecture) axis.

    Grounding is the milestone's empirical axis (dsp_only / audio+dsp / …), so
    grouping by it lets Kaan read 'which architecture clicks' at a glance. A
    result with no recorded cell falls under ``_UNGROUPED``.
    """
    cell = getattr(result, "cell", None)
    if isinstance(result, dict):
        cell = result.get("cell", cell)
    grounding = getattr(cell, "grounding", None)
    return str(grounding) if grounding else _UNGROUPED


def _coordinates_line(result: object) -> str | None:
    """Render the cell's 6-D coordinates, or ``None`` when no cell was recorded."""
    cell = getattr(result, "cell", None)
    if isinstance(result, dict):
        cell = result.get("cell", cell)
    if cell is None:
        return None
    parts = [
        f"model=`{getattr(cell, 'model_path', '?')}`",
        f"grounding=`{getattr(cell, 'grounding', '?')}`",
        f"prompting=`{getattr(cell, 'prompting', '?')}`",
        f"contexting=`{getattr(cell, 'contexting', '?')}`",
        f"lens=`{getattr(cell, 'lens', '?')}`",
        f"taste=`{getattr(cell, 'taste', '?')}`",
    ]
    track = getattr(cell, "track", None)
    if track:
        parts.append(f"track=`{_scrub(str(track))}`")
    return " · ".join(parts)


def _output_of(result: object) -> str:
    """Pull the recorded reaction text (BenchResult or dict stand-in)."""
    if isinstance(result, dict):
        return str(result.get("output") or "")
    return str(getattr(result, "output", "") or "")


def _error_of(result: object) -> str | None:
    """Pull the fail-safe error field (None on a successful call)."""
    if isinstance(result, dict):
        return result.get("error")
    return getattr(result, "error", None)


def _prompt_of(result: object) -> str:
    """Pull the assembled prompt (BenchResult or dict stand-in)."""
    if isinstance(result, dict):
        return str(result.get("prompt") or "")
    return str(getattr(result, "prompt", "") or "")


def _render_cell(result: object, score: CellScore, rank: int) -> list[str]:
    """Render one cell block: rank · coordinates · scores · prompt · output|parked."""
    lines: list[str] = []
    lines.append(f"### Cell #{rank}")
    coords = _coordinates_line(result)
    if coords is not None:
        lines.append(f"- **Coordinates:** {coords}")
    # The three auto-scores + the SORT-ONLY aggregate. Labelled as a rank signal,
    # NEVER a verdict (the heading below + the empty VERDICT enforce the split).
    lines.append(
        "- **Auto-scores (rank signal, not a verdict):** "
        f"groundedness={score.groundedness:.2f} · "
        f"specificity={score.specificity:.2f} · "
        f"lens_fidelity={score.lens_fidelity:.2f} · "
        f"aggregate={score.aggregate:.3f}"
    )
    prompt = _scrub(_truncate(_prompt_of(result), _PROMPT_MAX))
    if prompt:
        lines.append("")
        lines.append("**Prompt:**")
        lines.append("")
        lines.append("```")
        lines.append(prompt)
        lines.append("```")

    error = _error_of(result)
    lines.append("")
    if error is not None:
        # The cardinal-sin guard: an errored cell is PARKED, never fabricated
        # (T-81-10). We render the error verbatim (scrubbed), no output line.
        lines.append(f"**ERRORED — parked:** {_scrub(str(error))}")
    else:
        lines.append("**Output:**")
        lines.append("")
        lines.append(f"> {_scrub(_output_of(result))}")
    lines.append("")
    return lines


def render_review(
    results: list[object],
    scores: list[CellScore] | dict[object, CellScore],
) -> str:
    """Render the ranked KAAN-ACTION review surface as Markdown.

    Pairs each ``result`` with its ``score`` (positionally when ``scores`` is a
    list — the order ``score_cell`` was called in — else by lookup when a dict),
    SORTS strongest-first via :func:`rank_cells`, groups by the grounding
    (architecture) dimension, and renders every cell's coordinates + auto-scores
    + prompt + output. ERRORED cells render as ``ERRORED — parked``.

    The VERDICT section is rendered EMPTY — no code path here writes a winner
    (Pitfall 5 / T-81-09). PURE + deterministic: same inputs → byte-identical
    Markdown, no clock / randomness / I/O (the caller writes the artifact).
    """
    # Pair results with their scores. A list is positional (the common path —
    # ``[score_cell(r) for r in results]``); a dict is keyed by result.
    if isinstance(scores, dict):
        pairs = [(r, scores[r]) for r in results]
    else:
        pairs = list(zip(results, scores))

    cell_count = len(pairs)
    errored_count = sum(1 for r, _ in pairs if _error_of(r) is not None)

    out: list[str] = []
    out.append("# BENCH — Review Surface (KAAN-ACTION)")
    out.append("")
    out.append(
        "_Auto-ranked cells for Kaan's ear. The auto-score is a SORT, not a "
        "decision — the verdict below is empty and stays empty until Kaan fills "
        "it (Phase-16 rule, the hard human gate)._"
    )
    out.append("")
    out.append(
        f"- **Cells:** {cell_count}  ·  **Errored (parked):** {errored_count}"
    )
    out.append("")

    # Group by grounding dimension, deterministic group order (sorted label).
    groups: dict[str, list[tuple[object, CellScore]]] = {}
    for result, score in pairs:
        groups.setdefault(_group_key(score, result), []).append((result, score))

    for group_label in sorted(groups):
        out.append(f"## Dimension: grounding = `{group_label}`")
        out.append("")
        # rank_cells SORTS by aggregate (strongest first) — it does NOT decide.
        ranked = rank_cells(groups[group_label])
        for idx, (result, score) in enumerate(ranked, start=1):
            out.extend(_render_cell(result, score, idx))

    # THE HARD HUMAN GATE — the literally-empty verdict. Nothing is written here
    # by code; Kaan fills it after reading the ranked surface (BENCH-03).
    out.append(_VERDICT_HEADING)
    out.append(_VERDICT_PLACEHOLDER)
    out.append("")

    return "\n".join(out)
