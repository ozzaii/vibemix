# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-01 seam test — P25 → P28.

Source: ``src/vibemix/library/rekordbox.py`` (RekordboxLibrary / TrackEntry)
Sink:   ``src/vibemix/state/evidence_registry.py:register_library``
        (P48 final-mile wiring — Phase 27 closed the orphan)

Exercises the REAL Rekordbox-library → register_library → linter chain
end-to-end with the production classes. No mocks of the seam under test.

Verifies the integration anchor that closes Pitfall P48 — the
``register_library`` orphan loop the v2.0 audit flagged. After registry
load, ``[track:<id>]`` citations against real library track IDs MUST
pass the Phase 20 CitationLinter live-mode gate.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _make_track_entry(tid: str):
    from vibemix.library.rekordbox import TrackEntry

    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=138.0,
        key="A min",
        duration_s=240.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.mark.e2e
def test_rekordbox_library_registers_into_evidence_and_clears_linter() -> None:
    """Full P48 chain: library → register → snapshot → linter PASS."""
    from vibemix.coach.citation_linter import CitationLinter
    from vibemix.state.evidence_registry import EvidenceRegistry

    # 1. Simulate a real library (duck-typed — register_library accepts any
    #    object with a ``tracks`` dict per the registry contract docstring).
    fake_lib = MagicMock()
    fake_lib.tracks = {
        f"t{i:03d}": _make_track_entry(f"t{i:03d}") for i in range(5)
    }

    # 2. REAL EvidenceRegistry surface (P48 final-mile wiring).
    registry = EvidenceRegistry()
    n = registry.register_library(fake_lib)
    assert n == 5, "register_library should emit one observation per track"

    # 3. Snapshot the registry — the surface the linter reads.
    snapshot = registry.snapshot()
    assert "track" in snapshot, "register_library must populate the 'track' source"
    assert "t000" in snapshot["track"]

    # 4. REAL CitationLinter — cite a real track id.
    linter = CitationLinter()
    text = "Solid pick [track:t000]."
    result = linter.check(text, snapshot, mode="live")

    assert result.valid, f"linter rejected real library citation: {result}"
    assert result.reason == "valid"


@pytest.mark.e2e
def test_unregistered_track_id_blocked_by_linter() -> None:
    """Citing a track id NOT in the registered library MUST fail."""
    from vibemix.coach.citation_linter import CitationLinter
    from vibemix.state.evidence_registry import EvidenceRegistry

    fake_lib = MagicMock()
    fake_lib.tracks = {"t000": _make_track_entry("t000")}

    registry = EvidenceRegistry()
    registry.register_library(fake_lib)

    snapshot = registry.snapshot()
    linter = CitationLinter()
    text = "Ghost track [track:t999]."  # not in library
    result = linter.check(text, snapshot, mode="live")

    assert not result.valid
    assert result.reason == "invalid_atoms"
    assert ("track", "t999") in result.missing
