# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-06 — Gemini 3 Pro structured-output drill generation.

Exactly 3 SBI/STAR-AR :class:`Drill` objects per session. Each drill
has 5 string fields (situation / behavior / impact / action_recommended
/ citation) and the ``citation`` MUST resolve against the
:class:`EvidenceRegistry` snapshot at ±2.0s tolerance (Phase 20 debrief
mode tolerance band).

Pydantic is used here as a Gemini ``response_schema`` carrier — this is
allowed in :mod:`vibemix.debrief` because it's a leaf module that
serializes back to plain dicts before crossing any IPC boundary. The
``no-pydantic-in-ui_bus`` lint stays clean.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Protocol

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover — pydantic should be installed
    raise

from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE

__all__ = [
    "DEBRIEF_DRILLS_MODEL",
    "Drill",
    "Drills",
    "DrillsGenerationError",
    "generate_drills",
]

logger = logging.getLogger(__name__)

DEBRIEF_DRILLS_MODEL = "gemini-3-pro-preview"

# How tight the citation→snapshot lookup is. Phase 20 ``mode="debrief"``
# tolerance is ±2.0s.
_CITATION_RESOLVE_TOL_S = 2.0


class Drill(BaseModel):
    """One SBI/STAR-AR drill row."""

    situation: str = Field(min_length=1)
    behavior: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    action_recommended: str = Field(min_length=1)
    citation: str = Field(min_length=1)


class Drills(BaseModel):
    """Exactly 3 drills — DEBRIEF-06 invariant."""

    drills: list[Drill] = Field(min_length=3, max_length=3)


class DrillsGenerationError(Exception):
    """Raised after retries when valid drills cannot be produced."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


class _GeminiClient(Protocol):
    models: Any


# ---------------------------------------------------------------------------
# Citation resolution against the snapshot
# ---------------------------------------------------------------------------


def _parse_citation_tag(tag: str) -> tuple[str, str, float | None] | None:
    """``[ev:DROP_HIT@01:23]`` → ``("ev", "DROP_HIT", 83.0)``.

    Accepts the 7 EBNF source identifiers. Returns ``None`` if the tag
    is malformed.
    """
    m = EVIDENCE_CITATION_RE.search(tag)
    if not m:
        return None
    inner = m.group(0)[1:-1]  # strip [ ]
    # Take only the first atom if the tag is a multi-citation form.
    atom = inner.split(",", 1)[0]
    if ":" not in atom:
        return None
    source, body = atom.split(":", 1)
    t: float | None = None
    if "@" in body:
        key, t_str = body.rsplit("@", 1)
        t = _parse_timestamp(t_str)
    else:
        key = body
    return (source, key, t)


def _parse_timestamp(t_str: str) -> float | None:
    """``"01:23"`` → 83.0; ``"83.5"`` → 83.5; on bad input returns None."""
    try:
        if ":" in t_str:
            mins, secs = t_str.split(":", 1)
            return float(mins) * 60.0 + float(secs)
        return float(t_str)
    except (ValueError, TypeError):
        return None


def _citation_resolves(
    citation: str,
    evidence_snapshot: dict[str, dict[str, list[float]]],
    *,
    tol: float = _CITATION_RESOLVE_TOL_S,
) -> bool:
    """Return True if ``citation`` resolves against the snapshot.

    The snapshot shape is ``{source: {key: [t_session, ...]}}`` —
    matches :meth:`EvidenceRegistry.snapshot`. We look up by
    ``(source, key)`` and check that ANY of the recorded timestamps
    is within ``tol`` of the citation's ``@t`` (if present). When
    the citation has no ``@t``, a non-empty timestamp list is enough.
    """
    parsed = _parse_citation_tag(citation)
    if parsed is None:
        return False
    source, key, target_t = parsed
    source_map = evidence_snapshot.get(source) or {}
    ts = source_map.get(key)
    if not ts:
        return False
    if target_t is None:
        return True
    return any(abs(t - target_t) <= tol for t in ts)


# ---------------------------------------------------------------------------
# Prompt + Gemini call
# ---------------------------------------------------------------------------


def _allowlist_for(evidence_snapshot: dict[str, dict[str, list[float]]]) -> str:
    """Render `[source:key@t]` candidates for the prompt."""
    out: list[str] = []
    for source, keys in sorted(evidence_snapshot.items()):
        for key, ts in sorted(keys.items()):
            if not ts:
                continue
            t = ts[0]
            mins = int(t) // 60
            secs = int(t) % 60
            out.append(f"[{source}:{key}@{mins:02d}:{secs:02d}]")
    return "\n".join(out)


def _build_drills_prompt(
    cited_critique: str,
    chapter_summaries: list[str],
    evidence_snapshot: dict[str, dict[str, list[float]]],
) -> str:
    chapters_block = "\n".join(f"- {s}" for s in chapter_summaries)
    allowlist = _allowlist_for(evidence_snapshot)
    return (
        "You are the vibemix post-session coach. Generate EXACTLY 3 SBI/"
        "STAR-AR drills the DJ should rehearse next session.\n\n"
        "Each drill must have these 5 fields:\n"
        "  situation: descriptive context\n"
        "  behavior: what the DJ did, citing evidence\n"
        "  impact: what happened audibly, citing evidence\n"
        "  action_recommended: actionable next-time advice, citing\n"
        "  citation: ONE canonical [source:key@time] tag from the\n"
        "    allowlist below for the citation chip\n\n"
        "HARD RULE: every behavior, impact, and action_recommended field "
        "MUST contain at least one citation in the form "
        "[ev:<id>@<t>] / [track:<id>] / [mix:<id>] / [aud:<id>] / "
        "[midi:<id>] / [screen:<id>] / [tend:<id>]. Citations MUST be "
        "from the allowlist below — citations referencing events that "
        "are not in the allowlist will be rejected.\n\n"
        f"Chapter summaries:\n{chapters_block}\n\n"
        f"Cited critique (use verbatim or paraphrase, keep tags):\n"
        f"{cited_critique}\n\n"
        f"Available citation allowlist:\n{allowlist}\n"
    )


def generate_drills(
    client: _GeminiClient,
    cited_critique: str,
    chapter_summaries: list[str],
    evidence_snapshot: dict[str, dict[str, list[float]]],
    *,
    model: str = DEBRIEF_DRILLS_MODEL,
    max_retries: int = 2,
) -> Drills:
    """Generate exactly 3 cited drills against the EvidenceRegistry snapshot.

    Retries up to ``max_retries`` times if any drill's citation fails to
    resolve. After exhausting retries, raises
    :class:`DrillsGenerationError(reason="drills_generation_failed")`.
    """
    prompt = _build_drills_prompt(
        cited_critique, chapter_summaries, evidence_snapshot
    )

    last_error: str = ""
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Drills,
                },
            )
        except Exception as e:  # noqa: BLE001
            last_error = f"Gemini call failed: {type(e).__name__}: {e}"
            logger.warning(
                "[debrief] drills attempt %d/%d: %s",
                attempt + 1,
                max_retries + 1,
                last_error,
            )
            continue

        # Parse — accept .parsed (newer SDK) or .text (fallback).
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, Drills):
            drills = parsed
        else:
            text = getattr(response, "text", "")
            try:
                drills = Drills.model_validate_json(text)
            except Exception as e:  # noqa: BLE001
                last_error = f"Pydantic validate failed: {e}"
                logger.warning("[debrief] %s", last_error)
                continue

        # Validate every drill's citation resolves against the snapshot.
        invalid = [
            i for i, d in enumerate(drills.drills)
            if not _citation_resolves(d.citation, evidence_snapshot)
        ]
        if not invalid:
            return drills

        last_error = (
            f"{len(invalid)}/{len(drills.drills)} drills have unresolvable "
            f"citations (indices {invalid})"
        )
        logger.info(
            "[debrief] drills retry %d: %s", attempt + 1, last_error
        )

    raise DrillsGenerationError(
        reason="drills_generation_failed",
        message=f"After {max_retries + 1} attempts: {last_error}",
    )
