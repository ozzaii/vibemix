# SPDX-License-Identifier: Apache-2.0
"""Phase 93 — Invariant #2 binding: fabricated [exemplar:bogus] strips the whole turn.

Mirrors the v6 test_fabricated_recall_strips_turn pattern at
tests/agent/test_dj_cohost_linter.py:250-330.

REQ-ID: EXEMPLAR-05 (citation grounding via 4-site mirror).
Flipped GREEN by Plan 93-05 — the atomic 4-site mirror commit landed
``exemplar`` in ``_SOURCE_ALT`` so ``parse_citations`` now extracts
``[exemplar:<id>]`` atoms and the linter gates them via the existing
existence check.
"""
from __future__ import annotations

from vibemix.state.evidence_registry import EvidenceRegistry, parse_citations


def test_fabricated_exemplar_id_not_in_registry_means_unmatched() -> None:
    """A fabricated [exemplar:bogus] resolves to no registry observation.

    The runtime contract: ExemplarFinder.find() calls
    registry.write("exemplar", track_id, t_session) for every track it
    recommends; the LLM only sees track_ids it has been TOLD about via
    the lesson prompt; a track_id the LLM invents → registry.has() returns
    False → the CitationLinter strips the whole turn.

    This test verifies the lower half of that contract: an unregistered
    [exemplar:<id>] is NOT marked as grounded by the registry. The linter's
    "strip whole turn on any unresolved cite" behavior is already tested
    in tests/coach/test_citation_linter.py — when sites 1+2 land, the
    linter automatically gates [exemplar:] atoms because parse_citations
    now matches them and the existence check runs.
    """
    reg = EvidenceRegistry()
    # Register one real exemplar
    reg.write("exemplar", "library:track_real", 10.0)

    # Real cite resolves
    assert reg.has("exemplar", "library:track_real", 10.0, tol=2.0)

    # Fabricated cite does NOT
    assert not reg.has("exemplar", "library:track_bogus", 10.0, tol=2.0)


def test_parse_citations_extracts_exemplar_atom() -> None:
    """Sanity: parse_citations() returns the exemplar atom for the linter."""
    text = "the lows hit hard [exemplar:library:Marlon-Atlas] right there"
    parsed = parse_citations(text)
    assert ("exemplar", "library:Marlon-Atlas") in parsed


def test_parse_citations_extracts_exemplar_in_multi_atom() -> None:
    """[ev:KICK_SWAP@45.2,exemplar:library:foo] — multi-citation form."""
    text = "[ev:KICK_SWAP@45.2,exemplar:library:foo]"
    parsed = parse_citations(text)
    assert ("ev", "KICK_SWAP@45.2") in parsed
    assert ("exemplar", "library:foo") in parsed
