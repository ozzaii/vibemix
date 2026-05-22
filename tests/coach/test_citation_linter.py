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

    NOTE: parse_citations EBNF regex rejects whitespace inside the body
    (the body charset is ``[^\\s,\\]]+`` per evidence_registry.py:79).
    The plan's narrative example "Marlon Hoffstadt - Atlas" is shorthand
    for the spaceless form Gemini actually emits — track IDs at the
    citation-grammar boundary are the slug form (no spaces).
    """
    snap = _registry(("track", "MarlonHoffstadt-Atlas", None))
    linter = CitationLinter()

    valid = linter.check("[track:MarlonHoffstadt-Atlas]", snap, mode="live")
    assert valid.valid is True
    assert valid.reason == "valid"

    invalid = linter.check("[track:SomeOtherTrack]", snap, mode="live")
    assert invalid.valid is False
    assert ("track", "SomeOtherTrack") in invalid.missing
    assert invalid.reason == "invalid_atoms"


# ---------------------------------------------------------------------------
# (g2) key: harmonic source — existence-only — DECK-03 (Phase 59)
# ---------------------------------------------------------------------------


def test_key_atom_existence_only_DECK03() -> None:
    """key:<deck>:<camelot> is existence-only — no @t parsing (mirrors track:).

    The deck poller registers `key:A:8A`; the linter validates by exact-body
    presence. `key` is NOT in _TIME_KEYED_SOURCES, so the existence-only
    branch (`body in snapshot["key"]`) handles it with no @timestamp.
    """
    snap = _registry(("key", "A:8A", None))
    linter = CitationLinter()

    valid = linter.check("[key:A:8A]", snap, mode="live")
    assert valid.valid is True
    assert valid.reason == "valid"


def test_key_atom_fabricated_camelot_stripped_DECK03() -> None:
    """A fabricated harmonic clash `[key:A:12B]` never written → STRIPPED.

    This is the headline anti-slop guarantee: only poller-written
    `<deck>:<camelot>` bodies validate. A hallucinated 12B body that was
    never observed is uncitable-by-construction — the whole turn is stripped
    (response-level binary). The poller registered A:8A, not A:12B.
    """
    snap = _registry(("key", "A:8A", None))
    linter = CitationLinter()

    result = linter.check("clashing keys [key:A:12B]", snap, mode="live")
    assert result.valid is False
    assert ("key", "A:12B") in result.missing
    assert result.reason == "invalid_atoms"


def test_key_source_not_time_keyed_DECK03() -> None:
    """`key` MUST stay OUT of _TIME_KEYED_SOURCES — existence-only, no @t.

    A bare `key:A:8A` (no @timestamp) validates by presence alone. If `key`
    leaked into the time-keyed set, the missing `@` would make it malformed.
    """
    from vibemix.coach.citation_linter import _TIME_KEYED_SOURCES

    assert "key" not in _TIME_KEYED_SOURCES

    # Prove the behavioral consequence: a bare (no @t) key atom is valid.
    snap = _registry(("key", "B:5A", None))
    linter = CitationLinter()
    result = linter.check("[key:B:5A]", snap, mode="live")
    assert result.valid is True
    assert result.reason == "valid"


# ---------------------------------------------------------------------------
# (g3) recall: past-session source — existence-only — RECALL-01 (Phase 65)
# ---------------------------------------------------------------------------


def test_recall_existence_only_valid() -> None:
    """A REGISTERED ``[recall:<record_id>]`` passes the existence-only branch.

    Phase 65 adds the dedicated ``recall`` source for past-session callbacks.
    Like ``key``/``track`` it is existence-only — NOT in _TIME_KEYED_SOURCES, so
    no ``@t`` parse. The agent registers each retrieved survivor's ``record_id``
    (``f"{session_id}:{seq}"`` — the inner ``:`` survives because parse_citations
    splits on the FIRST colon, exactly like ``key:A:8A``) BEFORE the LLM call;
    the linter then validates by exact-body presence in ``snapshot["recall"]``.

    RED until Plan 65-02: ``recall`` is not yet in EVIDENCE_SOURCES, so the
    parse_citations regex (driven off ``_SOURCE_ALT``) never matches
    ``[recall:…]`` → the linter sees 0 citations → ``no_citations`` (invalid).
    Once 65-02 lands sites 1+2, this body-presence check passes. That is the
    intended Wave-0 RED — the registered-recall-passes contract for 65-02.
    """
    record_id = "20260520-2200:7"
    snap = _registry(("recall", record_id, None))
    linter = CitationLinter()

    valid = linter.check(f"[recall:{record_id}]", snap, mode="live")
    assert valid.valid is True
    assert valid.reason == "valid"


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
