# SPDX-License-Identifier: Apache-2.0
"""Voice the Judge grade — render a ``TransitionVerdict`` as a grounded evidence line.

The Judge decides; this turns its decision into the compact, factual evidence line
the live prompt feeds the LLM, so the co-host narrates what was MEASURED (compatible
keys vs a key clash, clean low end vs both basslines up / low-end mud) anchored by
the grounded ``[judge:transition@t]`` citation atom — instead of the stale
TrackRelation blend it carries today.

Data flow: ``transition_judge_runtime.judge_and_record`` grounds a verdict (writes a
resolvable ``judge:transition@<t>`` citation) and hands BOTH the verdict and that
exact citation id here; ``verdict_evidence_line`` returns one terse line for the
prompt to rephrase — NOT the final spoken words, just the receipt.

Abstain-first (Invariant #3, trust the audio / never invent): a non-judged verdict
returns ``None`` — nothing was measured, so there is nothing to voice. A judged
verdict reads ONLY components that are present (defensive for future signals), with
exact ``<= 0.0`` thresholds against the two endpoints the Judge emits.

The line is built to survive ``prompts/filter.py`` untouched — every word is checked
against ``NEGATIVE_PHRASES`` so the Judge's own grade can never be the phrase that
silences the turn. Pure: no I/O, no model client, no registry import beyond the
``TransitionVerdict`` type — same import-light discipline as the rest of ``intel/``.
"""
from __future__ import annotations

from vibemix.intel.transition_judge import TransitionVerdict

__all__ = ["verdict_evidence_line"]


def verdict_evidence_line(
    verdict: TransitionVerdict, *, citation_id: str
) -> str | None:
    """Render a judged verdict as a grounded evidence line, or ``None`` on abstain.

    ``citation_id`` is the exact id ``judge_and_record`` grounds (e.g.
    ``judge:transition@128.4``); it is wrapped in square brackets so the voiced
    atom resolves in ``EvidenceRegistry`` and survives the citation strip.

    Returns ``None`` when ``verdict_state != "judged"`` (nothing measured to voice),
    else one compact line: the bracketed citation atom, the measured components in
    plain words, and the blend score to 2 decimals when present.
    """
    if verdict.verdict_state != "judged":
        return None

    clauses: list[str] = []

    harmonic = verdict.components.get("harmonic")
    if harmonic is not None:
        # 0.0 = Camelot clash; the compatible prior is the only other endpoint.
        clauses.append("key clash" if harmonic <= 0.0 else "compatible keys")

    bass = verdict.components.get("bass_collision")
    if bass is not None:
        # 0.0 = both basslines up (low-end mud); 1.0 = one bass ducked (clean low end).
        clauses.append(
            "both basslines up, low-end mud" if bass <= 0.0 else "clean low end, one bass ducked"
        )

    body = "; ".join(clauses)
    line = f"[{citation_id}] Judge graded the transition: {body}"
    if verdict.score is not None:
        line += f" (blend score {verdict.score:.2f}/1)"
    return line
