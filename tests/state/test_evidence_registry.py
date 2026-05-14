# SPDX-License-Identifier: Apache-2.0
"""Tests for ``vibemix.state.evidence_registry`` — Plan 18-01.

Covers the LOCKED v1.0 surface:
- ``EvidenceRegistry`` (round-trip + thread-safety + frozen snapshot + has-tolerance)
- ``EVIDENCE_CITATION_RE`` (the EBNF grammar regex)
- ``EVIDENCE_SOURCES`` (the frozenset of 7 source identifiers)

Each test name ends with the must-have / D-decision it satisfies.
v1.0 is prompt-only seeding — NO enforcement / stripping behavior here
(Phase 20 adds the linter; this suite locks the API contract Phase 20
will consume).
"""

from __future__ import annotations

import re
import threading

import pytest

from vibemix.state import (
    EVIDENCE_CITATION_RE,
    EVIDENCE_SOURCES,
    EvidenceRegistry,
    parse_citations,
)


# --------------------------------------------------------------------------- #
# Test 1 — round-trip — GROUND-01
# --------------------------------------------------------------------------- #
def test_evidence_01_round_trip_single_key_GROUND01() -> None:
    """write() then snapshot() yields the timestamp tuple in insertion order."""
    reg = EvidenceRegistry()
    reg.write(source="ev", key="KICK_SWAP", t_session=45.2)
    snap = reg.snapshot()
    assert snap["ev"]["KICK_SWAP"] == (45.2,)

    reg.write(source="ev", key="KICK_SWAP", t_session=46.1)
    snap2 = reg.snapshot()
    assert snap2["ev"]["KICK_SWAP"] == (45.2, 46.1)


# --------------------------------------------------------------------------- #
# Test 2 — multiple sources segregated — GROUND-01
# --------------------------------------------------------------------------- #
def test_evidence_02_sources_segregated_GROUND01() -> None:
    """Different sources do not cross-contaminate."""
    reg = EvidenceRegistry()
    reg.write(source="ev", key="KICK_SWAP", t_session=10.0)
    reg.write(source="aud", key="bpm", t_session=11.0)
    reg.write(source="midi", key="cue_a", t_session=12.0)

    snap = reg.snapshot()
    assert set(snap.keys()) == {"ev", "aud", "midi"}
    assert snap["ev"]["KICK_SWAP"] == (10.0,)
    assert snap["aud"]["bpm"] == (11.0,)
    assert snap["midi"]["cue_a"] == (12.0,)
    # No leakage across sources.
    assert "bpm" not in snap["ev"]
    assert "KICK_SWAP" not in snap["aud"]


# --------------------------------------------------------------------------- #
# Test 3 — thread-safety — D-LOCKED P12 mitigation
# --------------------------------------------------------------------------- #
def test_evidence_03_thread_safety_torn_writes_DLOCKED_P12() -> None:
    """8 threads × 100 writes to the same key → exactly 800 entries, no torn writes.

    Exercises the real GIL + threading.Lock contract — no mocks. This is
    the gate that closes Pitfall P12 (registry race).
    """
    reg = EvidenceRegistry()
    n_threads = 8
    writes_per_thread = 100

    def worker(thread_id: int) -> None:
        for i in range(writes_per_thread):
            reg.write(source="ev", key="KICK_SWAP", t_session=float(thread_id * 1000 + i))

    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snap = reg.snapshot()
    timestamps = snap["ev"]["KICK_SWAP"]
    assert len(timestamps) == n_threads * writes_per_thread, (
        f"expected {n_threads * writes_per_thread} timestamps after concurrent writes; "
        f"got {len(timestamps)} (torn writes / lost updates)"
    )


# --------------------------------------------------------------------------- #
# Test 4 — snapshot is frozen — D-LOCKED
# --------------------------------------------------------------------------- #
def test_evidence_04_snapshot_is_frozen_DLOCKED() -> None:
    """Mutating the snapshot dict must not affect the registry state."""
    reg = EvidenceRegistry()
    reg.write(source="ev", key="KICK_SWAP", t_session=1.0)
    reg.write(source="aud", key="bpm", t_session=2.0)

    snap = reg.snapshot()
    # Pop a top-level key from the snapshot.
    snap.pop("ev")
    # Inner is a tuple — already immutable; popping the outer dict must not
    # propagate back into the registry.
    snap2 = reg.snapshot()
    assert "ev" in snap2
    assert snap2["ev"]["KICK_SWAP"] == (1.0,)


# --------------------------------------------------------------------------- #
# Test 5 — has() within tolerance — GROUND-01 P20 hook
# --------------------------------------------------------------------------- #
def test_evidence_05_has_within_tolerance_GROUND01_P20() -> None:
    """has() returns True iff any observation lies within ±tol seconds of t_target.

    Boundary INCLUSIVE at exactly tol per Phase 20 §"per-mode tolerance bands".
    """
    reg = EvidenceRegistry()
    reg.write(source="ev", key="KICK_SWAP", t_session=10.0)
    # Within +0.5s.
    assert reg.has("ev", "KICK_SWAP", 10.5, tol=1.0) is True
    # At exactly +1.0s — boundary INCLUSIVE.
    assert reg.has("ev", "KICK_SWAP", 11.0, tol=1.0) is True
    # 1.5s past → outside the band.
    assert reg.has("ev", "KICK_SWAP", 11.5, tol=1.0) is False


# --------------------------------------------------------------------------- #
# Test 6 — has() returns False on missing source/key — GROUND-01
# --------------------------------------------------------------------------- #
def test_evidence_06_has_missing_returns_false_GROUND01() -> None:
    """Missing source or key must NOT raise KeyError; return False."""
    reg = EvidenceRegistry()
    # Empty registry.
    assert reg.has("ev", "KICK_SWAP", 10.0, tol=1.0) is False
    reg.write(source="ev", key="KICK_SWAP", t_session=10.0)
    # Source exists, key absent.
    assert reg.has("ev", "BREAKDOWN_KICK_KILL", 10.0, tol=1.0) is False
    # Source absent.
    assert reg.has("aud", "bpm", 10.0, tol=1.0) is False


# --------------------------------------------------------------------------- #
# Test 7 — EBNF regex single citation — GROUND-02
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "citation",
    [
        "[ev:KICK_SWAP@45.2]",
        "[aud:bpm@45.2]",
        "[midi:cue_a@12.7]",
        "[track:abc-123]",
        "[screen:waveform_deck_a]",
        "[mix:audible_deck=A]",
        "[tend:user_likes_acid]",
    ],
)
def test_evidence_07_regex_matches_all_seven_forms_GROUND02(citation: str) -> None:
    """EVIDENCE_CITATION_RE matches each of the 7 EBNF source forms."""
    assert EVIDENCE_CITATION_RE.fullmatch(citation) is not None, (
        f"expected EVIDENCE_CITATION_RE to match {citation!r}"
    )


# --------------------------------------------------------------------------- #
# Test 8 — EBNF regex multi-citation — GROUND-02
# --------------------------------------------------------------------------- #
def test_evidence_08_regex_multi_citation_GROUND02() -> None:
    """Comma-separated multi-citation form matches and yields 2 sub-matches."""
    text = "[ev:KICK_SWAP@45.2,aud:bpm@45.0]"
    m = EVIDENCE_CITATION_RE.fullmatch(text)
    assert m is not None, f"expected fullmatch on multi-citation {text!r}"

    # Inner-form sub-match: walk the source-tagged segments.
    inner_re = re.compile(r"(ev|aud|midi|track|screen|mix|tend):[^\s,\]]+")
    parts = inner_re.findall(text)
    assert len(parts) == 2
    assert parts == ["ev", "aud"]


# --------------------------------------------------------------------------- #
# Test 9 — EBNF regex rejects whitespace — GROUND-02 D-LOCKED
# --------------------------------------------------------------------------- #
def test_evidence_09_regex_rejects_whitespace_GROUND02_DLOCKED() -> None:
    """Whitespace inside brackets is invalid per CONTEXT.md §EBNF Grammar."""
    assert EVIDENCE_CITATION_RE.fullmatch("[ev:foo bar]") is None
    assert EVIDENCE_CITATION_RE.fullmatch("[ev: foo]") is None


# --------------------------------------------------------------------------- #
# Test 10 — EBNF regex rejects empty — GROUND-02 D-LOCKED
# --------------------------------------------------------------------------- #
def test_evidence_10_regex_rejects_empty_GROUND02_DLOCKED() -> None:
    """Empty `[]` is invalid; P20 will strip."""
    assert EVIDENCE_CITATION_RE.fullmatch("[]") is None


# --------------------------------------------------------------------------- #
# Test 11 — EVIDENCE_SOURCES constant — GROUND-02
# --------------------------------------------------------------------------- #
def test_evidence_11_sources_constant_locked_GROUND02() -> None:
    """EVIDENCE_SOURCES is a frozenset of exactly the 7 CONTEXT.md sources."""
    assert isinstance(EVIDENCE_SOURCES, frozenset)
    assert EVIDENCE_SOURCES == frozenset(
        {"ev", "aud", "midi", "track", "screen", "mix", "tend"}
    )


# --------------------------------------------------------------------------- #
# Test 12 — registry-grammar coherence — GROUND-01 + GROUND-02
# --------------------------------------------------------------------------- #
def test_evidence_12_registry_grammar_coherence_GROUND01_GROUND02() -> None:
    """Every EVIDENCE_SOURCES key is matchable AND writable.

    Locks the contract between the regex and the registry's accepted
    source vocabulary so Phase 20's linter can trust both pieces.
    """
    reg = EvidenceRegistry()
    for source in EVIDENCE_SOURCES:
        citation = f"[{source}:test_key@10.0]"
        assert EVIDENCE_CITATION_RE.fullmatch(citation) is not None, (
            f"EVIDENCE_CITATION_RE failed to match valid synthetic citation {citation!r}"
        )
        reg.write(source=source, key="test_key", t_session=10.0)

    snap = reg.snapshot()
    # Every source landed in the registry under "test_key".
    for source in EVIDENCE_SOURCES:
        assert snap[source]["test_key"] == (10.0,)


# --------------------------------------------------------------------------- #
# Test 13 — multi-citation findall yields per-source pairs — GROUND-02
# --------------------------------------------------------------------------- #
def test_evidence_13_parse_citations_multi_form_GROUND02() -> None:
    """parse_citations splits each multi-citation atom on the first colon.

    The helper is the parser the Phase 20 linter and Plan 18-04 telemetry
    will reuse; landing it here in v1.0 locks the API contract.
    """
    text = "[ev:KICK_SWAP@45.2,aud:bpm@45.0,midi:cue_a@45.1]"
    out = parse_citations(text)
    assert out == [
        ("ev", "KICK_SWAP@45.2"),
        ("aud", "bpm@45.0"),
        ("midi", "cue_a@45.1"),
    ]

    # Single-citation form also yields a one-element list.
    single = parse_citations("preface [track:abc-123] suffix")
    assert single == [("track", "abc-123")]

    # No citations → empty list, not error.
    assert parse_citations("plain text with no brackets") == []
