# SPDX-License-Identifier: Apache-2.0
"""CitationLinter — Plan 20-01 Task 1.

Pins the response-level (whole-utterance, binary) citation grounding contract
against the EvidenceRegistry snapshot. The 7 EBNF atom shapes
(ev / aud / midi / track / screen / mix / tend) each get their own case;
boundary tolerance + malformed atom + multi-citation + mode dispatch +
unknown-source + None-snapshot are all pinned here.
"""

from __future__ import annotations

import pytest

from vibemix.coach import (
    DEBRIEF_TOLERANCE_S,
    LIVE_TOLERANCE_S,
    CitationLinter,
    LintResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registry(*entries: tuple[str, str, tuple[float, ...] | None]) -> dict:
    """Build a frozen registry snapshot from (source, key, times) triples.

    For non-time-keyed atoms (track/screen/mix/tend) pass times=None — the
    snapshot stores an empty tuple as an "existence-only" marker (the linter
    only checks key presence for those atoms).
    """
    out: dict[str, dict[str, tuple[float, ...]]] = {}
    for source, key, times in entries:
        out.setdefault(source, {})[key] = tuple(times) if times is not None else ()
    return out


# ---------------------------------------------------------------------------
# (a) test_no_citations_returns_invalid
# ---------------------------------------------------------------------------


def test_no_citations_returns_invalid() -> None:
    """Empty / uncited text → LintResult(False, 0, (), 'no_citations').

    Live mode treats an uncited reply as slop — Pitfall 2 binary decision.
    """
    linter = CitationLinter()
    result = linter.check("just clean text, no atoms here", _registry(), mode="live")
    assert isinstance(result, LintResult)
    assert result.valid is False
    assert result.citations_found == 0
    assert result.missing == ()
    assert result.reason == "no_citations"


# ---------------------------------------------------------------------------
# (b) test_single_valid_ev_citation
# ---------------------------------------------------------------------------


def test_single_valid_ev_citation() -> None:
    """ev:KICK@45.2 cited; registry has ev:KICK@45.2 → valid."""
    snap = _registry(("ev", "KICK", (45.2,)))
    linter = CitationLinter()
    result = linter.check("that drop [ev:KICK@45.2]", snap, mode="live")
    assert result.valid is True
    assert result.citations_found == 1
    assert result.missing == ()
    assert result.reason == "valid"


# ---------------------------------------------------------------------------
# (c) test_single_invalid_ev_citation_outside_tolerance
# ---------------------------------------------------------------------------


def test_single_invalid_ev_citation_outside_tolerance() -> None:
    """Registry has ev:KICK@40.0; cite @45.2 → outside ±1.0s → invalid."""
    snap = _registry(("ev", "KICK", (40.0,)))
    linter = CitationLinter()
    result = linter.check("that drop [ev:KICK@45.2]", snap, mode="live")
    assert result.valid is False
    assert result.citations_found == 1
    assert ("ev", "KICK@45.2") in result.missing
    assert result.reason == "invalid_atoms"


# ---------------------------------------------------------------------------
# (d) test_boundary_tolerance_inclusive
# ---------------------------------------------------------------------------


def test_boundary_tolerance_inclusive() -> None:
    """At exactly ±LIVE_TOLERANCE_S the boundary is INCLUSIVE.

    Registry @45.0; cite @46.0 (exactly +1.0) → valid; cite @46.01 → invalid.
    """
    snap = _registry(("ev", "KICK", (45.0,)))
    linter = CitationLinter()

    on_boundary = linter.check("[ev:KICK@46.0]", snap, mode="live")
    assert on_boundary.valid is True, "±LIVE_TOLERANCE_S boundary must be inclusive"

    off_boundary = linter.check("[ev:KICK@46.01]", snap, mode="live")
    assert off_boundary.valid is False


# ---------------------------------------------------------------------------
# (e) test_malformed_ev_atom_no_at_sign
# ---------------------------------------------------------------------------


def test_malformed_ev_atom_no_at_sign() -> None:
    """Time-keyed atom missing '@' → MALFORMED → reason='malformed_atom'."""
    snap = _registry(("ev", "KICK", (45.0,)))
    linter = CitationLinter()
    result = linter.check("[ev:KICK]", snap, mode="live")
    assert result.valid is False
    assert result.citations_found == 1
    assert ("ev", "KICK") in result.missing
    assert result.reason == "malformed_atom"


# ---------------------------------------------------------------------------
# (f) test_malformed_ev_atom_non_numeric_t
# ---------------------------------------------------------------------------


def test_malformed_ev_atom_non_numeric_t() -> None:
    """Time-keyed atom with non-numeric @t → MALFORMED."""
    snap = _registry(("ev", "KICK", (45.0,)))
    linter = CitationLinter()
    result = linter.check("[ev:KICK@abc]", snap, mode="live")
    assert result.valid is False
    assert result.citations_found == 1
    assert ("ev", "KICK@abc") in result.missing
    assert result.reason == "malformed_atom"


# ---------------------------------------------------------------------------
# (g) test_track_atom_existence_only
# ---------------------------------------------------------------------------


def test_track_atom_existence_only() -> None:
    """track:<id> atom is existence-only — no @t parsing.

    Match on key presence in registry["track"]; no tolerance involved.
    """
    snap = _registry(("track", "Marlon Hoffstadt - Atlas", None))
    linter = CitationLinter()

    valid = linter.check("[track:Marlon Hoffstadt - Atlas]", snap, mode="live")
    assert valid.valid is True
    assert valid.reason == "valid"

    invalid = linter.check("[track:Some Other Track]", snap, mode="live")
    assert invalid.valid is False
    assert ("track", "Some Other Track") in invalid.missing
    assert invalid.reason == "invalid_atoms"


# ---------------------------------------------------------------------------
# (h) test_screen_mix_tend_existence_only
# ---------------------------------------------------------------------------


def test_screen_mix_tend_existence_only() -> None:
    """screen / mix / tend atoms are existence-only (no @t)."""
    snap = _registry(
        ("screen", "waveform_deck_a", None),
        ("mix", "audible_deck=A", None),
        ("tend", "user_likes_acid", None),
    )
    linter = CitationLinter()

    for source, key in (
        ("screen", "waveform_deck_a"),
        ("mix", "audible_deck=A"),
        ("tend", "user_likes_acid"),
    ):
        result = linter.check(f"[{source}:{key}]", snap, mode="live")
        assert result.valid is True, f"{source}:{key} should be valid"
        assert result.reason == "valid"


# ---------------------------------------------------------------------------
# (i) test_multi_citation_all_valid
# ---------------------------------------------------------------------------


def test_multi_citation_all_valid() -> None:
    """Comma-joined multi-citation, all atoms valid → valid."""
    snap = _registry(("ev", "K", (1.0,)), ("aud", "bpm", (1.0,)))
    linter = CitationLinter()
    result = linter.check("[ev:K@1.0,aud:bpm@1.0]", snap, mode="live")
    assert result.valid is True
    assert result.citations_found == 2
    assert result.missing == ()
    assert result.reason == "valid"


# ---------------------------------------------------------------------------
# (j) test_multi_citation_one_invalid
# ---------------------------------------------------------------------------


def test_multi_citation_one_invalid() -> None:
    """Multi-citation with ONE bad atom → invalid; missing has only the bad one."""
    snap = _registry(("ev", "K", (1.0,)))  # aud:bpm NOT in registry
    linter = CitationLinter()
    result = linter.check("[ev:K@1.0,aud:bpm@1.0]", snap, mode="live")
    assert result.valid is False
    assert result.citations_found == 2
    assert ("aud", "bpm@1.0") in result.missing
    assert ("ev", "K@1.0") not in result.missing
    assert result.reason == "invalid_atoms"


# ---------------------------------------------------------------------------
# (k) test_unknown_source_treated_as_no_citations
# ---------------------------------------------------------------------------


def test_unknown_source_treated_as_no_citations() -> None:
    """Unknown source — parse_citations regex won't match → 0 citations.

    The regex EVIDENCE_CITATION_RE whitelists the 7 sources; an atom like
    ``[xyz:foo]`` simply doesn't match. The linter sees zero citations.
    """
    linter = CitationLinter()
    result = linter.check("text [xyz:foo]", _registry(), mode="live")
    assert result.valid is False
    assert result.citations_found == 0
    assert result.reason == "no_citations"


# ---------------------------------------------------------------------------
# (l) test_mode_debrief_uses_2s_tolerance
# ---------------------------------------------------------------------------


def test_mode_debrief_uses_2s_tolerance() -> None:
    """mode='debrief' widens the tolerance band to ±2.0s."""
    snap = _registry(("ev", "KICK", (45.0,)))
    linter = CitationLinter()

    debrief_result = linter.check("[ev:KICK@46.5]", snap, mode="debrief")
    assert debrief_result.valid is True, "debrief mode should allow ±2.0s"
    assert DEBRIEF_TOLERANCE_S == 2.0  # locks the constant import + value

    live_result = linter.check("[ev:KICK@46.5]", snap, mode="live")
    assert live_result.valid is False, "live mode rejects @46.5 vs ±1.0s"
    assert LIVE_TOLERANCE_S == 1.0


# ---------------------------------------------------------------------------
# (m) test_mode_unknown_raises
# ---------------------------------------------------------------------------


def test_mode_unknown_raises() -> None:
    """Unknown mode → ValueError (fail loud)."""
    linter = CitationLinter()
    with pytest.raises(ValueError):
        linter.check("[ev:KICK@45.0]", _registry(), mode="paranormal")


# ---------------------------------------------------------------------------
# (n) test_registry_snapshot_none
# ---------------------------------------------------------------------------


def test_registry_snapshot_none() -> None:
    """registry_snapshot=None → no_citations regardless of text content.

    Defensive: no registry means nothing to ground against; refuse the reply.
    """
    linter = CitationLinter()
    result = linter.check("[ev:KICK@45.0]", None, mode="live")
    assert result.valid is False
    assert result.citations_found == 0
    assert result.missing == ()
    assert result.reason == "no_citations"


# ---------------------------------------------------------------------------
# Bonus locks — LintResult shape & immutability
# ---------------------------------------------------------------------------


def test_lint_result_is_frozen_dataclass() -> None:
    """LintResult must be frozen (dataclass(frozen=True)) for safe sharing."""
    result = LintResult(valid=True, citations_found=1, missing=(), reason="valid")
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        result.valid = False  # type: ignore[misc]
