# SPDX-License-Identifier: Apache-2.0
"""Phase 27-05 — end-to-end track citation lifecycle test.

Proves that a registered RekordboxLibrary produces resolvable [track:<id>]
citations that pass the live-mode CitationLinter.
"""

from __future__ import annotations


def test_registered_track_resolves_via_evidence_registry_has(
    evidence_registry_with_library,
) -> None:
    """The registered track is reachable via EvidenceRegistry.has('track', <id>).

    Note: PLAN.md mentions ``lookup_citation`` but the actual EvidenceRegistry
    public API exposes ``has(source, key, t_target)`` and ``snapshot()`` —
    no ``lookup_citation`` method exists (Rule 1 deviation: tests use the
    real API).
    """
    # has() returns True when the track exists for the source-key pair at
    # any registered timestamp; t_target=0.0 + tol on linter side is the
    # canonical "library load" timestamp per register_library docstring.
    assert evidence_registry_with_library.has(
        "track", "test_track_001", t_target=0.0, tol=0.0
    )


def test_unregistered_track_does_not_resolve(evidence_registry_with_library) -> None:
    """Sanity check: a track ID that was never registered returns False."""
    assert not evidence_registry_with_library.has(
        "track", "nonexistent_track", t_target=0.0, tol=0.0
    )


def test_track_citation_passes_live_linter(evidence_registry_with_library) -> None:
    """Test 5: CitationLinter.check accepts a [track:test_track_001] citation.

    Snapshot from the registry is fed into CitationLinter.check() in 'live'
    mode — the existence-only validator path (citation_linter.py:204) returns
    True iff body is in snapshot['track'].
    """
    from vibemix.coach.citation_linter import CitationLinter

    linter = CitationLinter()
    snapshot = evidence_registry_with_library.snapshot()
    result = linter.check(
        "Yeah, the new track [track:test_track_001] is a banger",
        snapshot,
        mode="live",
    )
    assert result.valid is True, (
        f"Linter rejected a registered track citation: {result.reason} "
        f"missing={result.missing}"
    )


def test_unregistered_track_citation_fails_linter(
    evidence_registry_with_library,
) -> None:
    """Inverse of test_track_citation_passes_live_linter — unregistered fails."""
    from vibemix.coach.citation_linter import CitationLinter

    linter = CitationLinter()
    snapshot = evidence_registry_with_library.snapshot()
    result = linter.check(
        "Track [track:nonexistent_phantom] is a banger",
        snapshot,
        mode="live",
    )
    assert result.valid is False
    # invalid_atoms reason expected (not no_citations, not malformed).
    assert result.reason == "invalid_atoms"


def test_register_library_returns_count(synthetic_library) -> None:
    """register_library returns the number of tracks registered (per its docstring)."""
    from vibemix.state.evidence_registry import EvidenceRegistry

    reg = EvidenceRegistry()
    n = reg.register_library(synthetic_library)
    assert n == 1, f"expected 1 track registered; got {n}"
