# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-06 — Gemini structured-output drill generation.

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
from typing import Any, Protocol

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover — pydantic should be installed
    raise

from vibemix.coach.constants import DEBRIEF_TOLERANCE_S
from vibemix.llm.model_router import resolve
from vibemix.runtime.ai_observability import append_global_ai_message
from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE

__all__ = [
    "DEBRIEF_DRILLS_MODEL",
    "Drill",
    "Drills",
    "DrillsGenerationError",
    "generate_drills",
]

logger = logging.getLogger(__name__)

# Plan 41-01: shares the debrief router path with tldr.
DEBRIEF_DRILLS_MODEL = resolve("debrief")[0]

# How tight the citation→snapshot lookup is. Phase 20 ``mode="debrief"``
# tolerance is ±2.0s. Bound to the single source of truth in
# ``coach/constants.py`` so the live linter band and the debrief drills
# resolver can never silently diverge (IN-01 / LIVE-04 citation integrity).
_CITATION_RESOLVE_TOL_S = DEBRIEF_TOLERANCE_S


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

    Accepts the EvidenceRegistry EBNF source identifiers. Returns ``None`` if
    the tag is malformed.
    """
    parsed = _parse_citation_atom(tag)
    if parsed is None:
        return None
    source, body = parsed
    if "@" not in body:
        return (source, body, None)
    key, t_str = body.rsplit("@", 1)
    t = _parse_timestamp(t_str)
    if t is None:
        return None
    return (source, key, t)


def _parse_citation_atom(tag: str) -> tuple[str, str] | None:
    """Return the first ``(source, body)`` atom from a citation tag."""
    m = EVIDENCE_CITATION_RE.search(tag)
    if not m:
        return None
    inner = m.group(0)[1:-1]  # strip [ ]
    # Take only the first atom if the tag is a multi-citation form.
    atom = inner.split(",", 1)[0]
    if ":" not in atom:
        return None
    source, body = atom.split(":", 1)
    return (source, body)


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
    if ts and target_t is None:
        return True
    if ts and any(abs(t - target_t) <= tol for t in ts):
        return True

    # Some narration-time sources deliberately carry ``@`` inside the key itself
    # (for example ``[judge:transition@128.4]`` and cue anchors like
    # ``[cue:drop@180.0]``). The live linter treats those as existence-only.
    # Fall back to the full body so debrief citations do not become decorative.
    atom = _parse_citation_atom(citation)
    if atom is None:
        return False
    _, raw_body = atom
    raw_ts = source_map.get(raw_body)
    return bool(raw_ts)


# ---------------------------------------------------------------------------
# Prompt + Gemini call
# ---------------------------------------------------------------------------


_EXISTENCE_KEY_ALLOWLIST_SOURCES = frozenset(
    {"track", "screen", "key", "recall", "exemplar", "cue", "judge"}
)


def _allowlist_for(evidence_snapshot: dict[str, dict[str, list[float]]]) -> str:
    """Render `[source:key@t]` candidates for the prompt."""
    out: list[str] = []
    for source, keys in sorted(evidence_snapshot.items()):
        for key, ts in sorted(keys.items()):
            if not ts:
                continue
            if source in _EXISTENCE_KEY_ALLOWLIST_SOURCES:
                out.append(f"[{source}:{key}]")
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
        "[midi:<id>] / [screen:<id>] / [key:<id>]. Citations MUST be "
        "from the allowlist below — citations referencing events that "
        "are not in the allowlist will be rejected.\n\n"
        f"Chapter summaries:\n{chapters_block}\n\n"
        f"Cited critique (use verbatim or paraphrase, keep tags):\n"
        f"{cited_critique}\n\n"
        f"Available citation allowlist:\n{allowlist}\n"
    )


def _record_drills_ai_message(
    *,
    text: str,
    model: str,
    stop_reason: str,
    prompt: str,
    response: str,
    attempt: int,
    extra: dict[str, Any] | None = None,
) -> None:
    try:
        append_global_ai_message(
            engine="gemini",
            surface="debrief_drills",
            direction="assistant",
            text=text,
            provider="gemini",
            model=model,
            stop_reason=stop_reason,
            prompt_chars=len(prompt),
            response_chars=len(response),
            extra={"attempt": attempt, **(extra or {})},
            prompt=prompt,
            response=response,
        )
    except Exception:  # pragma: no cover - observability must not break debrief
        pass


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
        except Exception as e:
            last_error = f"Gemini call failed: {type(e).__name__}: {e}"
            _record_drills_ai_message(
                text="",
                model=model,
                stop_reason=f"error:{type(e).__name__}",
                prompt=prompt,
                response=f"<error {last_error}>",
                attempt=attempt + 1,
                extra={"error": last_error},
            )
            logger.warning(
                "[debrief] drills attempt %d/%d: %s",
                attempt + 1,
                max_retries + 1,
                last_error,
            )
            continue

        # Parse — accept .parsed (newer SDK) or .text (fallback).
        parsed = getattr(response, "parsed", None)
        response_text = getattr(response, "text", "")
        if isinstance(parsed, Drills):
            drills = parsed
            response_text = response_text or drills.model_dump_json()
        else:
            try:
                drills = Drills.model_validate_json(response_text)
            except Exception as e:
                last_error = f"Pydantic validate failed: {e}"
                _record_drills_ai_message(
                    text="",
                    model=model,
                    stop_reason="parse_failed",
                    prompt=prompt,
                    response=str(response_text or ""),
                    attempt=attempt + 1,
                    extra={"error": last_error},
                )
                logger.warning("[debrief] %s", last_error)
                continue

        # Validate every drill's citation resolves against the snapshot
        # AND each of the 3 advice fields carries ≥ 1 citation
        # (Plan 29-07 strict mode — DEBRIEF-07).
        invalid: list[int] = []
        for i, d in enumerate(drills.drills):
            if not _citation_resolves(d.citation, evidence_snapshot):
                invalid.append(i)
                continue
            # Per-field citation presence check.
            for field_value in (d.behavior, d.impact, d.action_recommended):
                if not EVIDENCE_CITATION_RE.search(field_value):
                    invalid.append(i)
                    break
        if not invalid:
            drills_json = drills.model_dump_json()
            _record_drills_ai_message(
                text=drills_json,
                model=model,
                stop_reason="model_done",
                prompt=prompt,
                response=drills_json,
                attempt=attempt + 1,
                extra={"drill_count": len(drills.drills)},
            )
            return drills

        last_error = (
            f"{len(invalid)}/{len(drills.drills)} drills have unresolvable "
            f"citations (indices {invalid})"
        )
        _record_drills_ai_message(
            text=drills.model_dump_json(),
            model=model,
            stop_reason="invalid_citations",
            prompt=prompt,
            response=response_text or drills.model_dump_json(),
            attempt=attempt + 1,
            extra={"invalid_indices": invalid, "error": last_error},
        )
        logger.info(
            "[debrief] drills retry %d: %s", attempt + 1, last_error
        )

    raise DrillsGenerationError(
        reason="drills_generation_failed",
        message=f"After {max_retries + 1} attempts: {last_error}",
    )
