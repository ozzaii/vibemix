# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-01 seam test — P18 → P20.

Source: ``src/vibemix/state/evidence_registry.py`` (EvidenceRegistry)
Sink:   ``src/vibemix/coach/citation_linter.py`` (CitationLinter live-mode)

Exercises the REAL EvidenceRegistry → REAL CitationLinter chain (no
mocks of either surface). Verifies:

1. A response citing a real registry observation passes live-mode lint.
2. A response citing a fake/missing observation is blocked by the linter
   (``valid=False`` with ``reason='invalid_atoms'``).

This is the Phase 18 → Phase 20 grammar→enforce contract pinned end-to-
end.
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_real_citation_passes_live_linter() -> None:
    """Real registry observation + real linter → VALID."""
    from vibemix.coach.citation_linter import CitationLinter
    from vibemix.state.evidence_registry import EvidenceRegistry

    registry = EvidenceRegistry()
    # Write one real observation per source family the linter understands.
    registry.write("ev", "drop", t_session=12.0)  # time-keyed
    registry.write("track", "T-123", t_session=0.0)  # existence-only

    snapshot = registry.snapshot()
    linter = CitationLinter()

    # Cite the time-keyed atom AND the existence-only atom — both real.
    text = "Bringing the drop in [ev:drop@12.0] from [track:T-123]."

    result = linter.check(text, snapshot, mode="live")

    assert result.valid, f"linter rejected real citations: {result}"
    assert result.reason == "valid"
    assert result.citations_found == 2
    assert result.missing == ()


@pytest.mark.e2e
def test_fake_citation_blocked_by_live_linter() -> None:
    """Citing an observation the registry never recorded → INVALID."""
    from vibemix.coach.citation_linter import CitationLinter
    from vibemix.state.evidence_registry import EvidenceRegistry

    registry = EvidenceRegistry()
    registry.write("ev", "drop", t_session=12.0)

    snapshot = registry.snapshot()
    linter = CitationLinter()

    # Cite an event that never happened — the seam MUST block this.
    text = "Phantom event reaction [ev:phantom@99.9]."

    result = linter.check(text, snapshot, mode="live")

    assert not result.valid, f"linter let phantom citation through: {result}"
    assert result.reason == "invalid_atoms"
    assert ("ev", "phantom@99.9") in result.missing
