# SPDX-License-Identifier: Apache-2.0
"""LIVE-04 live/debrief citation consistency.

One grammar (EVIDENCE_CITATION_RE), one registry, two tolerance bands: the
citation strip is consistent across live (±1.0s, LIVE_TOLERANCE_S) and debrief
(±2.0s, DEBRIEF_TOLERANCE_S). This pins three properties with REAL primitives
(no mocks, no network):

1. STRIP CONSISTENCY — the SAME orphan is stripped in BOTH modes (valid False,
   reason 'invalid_atoms'). A hallucinated citation never reaches the ear nor
   the post-session debrief.
2. ACCEPT CONSISTENCY — a grounded citation that resolves at ±1.0s also
   resolves at ±2.0s. Debrief never strips what live accepts on the same data.
3. INTENTIONAL WIDER BAND — a citation 1.5s off is INVALID in live (±1.0s) but
   VALID in debrief (±2.0s), documenting the wider debrief band is deliberate
   and that inclusion is monotone (live ⊆ debrief).

NO source is modified — citation_linter.py + constants.py are the airtight
grounding gate per 55-RESEARCH Q0; this file ADDS regressions only.
"""

from __future__ import annotations

import pytest

from vibemix.coach.citation_linter import CitationLinter
from vibemix.coach.constants import DEBRIEF_TOLERANCE_S, LIVE_TOLERANCE_S
from vibemix.state.evidence_registry import EvidenceRegistry


def _registry_with_phase_at(t: float = 120.0) -> EvidenceRegistry:
    """A small REAL registry with one PHASE observation."""
    reg = EvidenceRegistry()
    reg.write("ev", "PHASE", t)
    return reg


# =========================================================================== #
# Constants pin                                                                #
# =========================================================================== #


def test_tolerance_constants_are_one_and_two() -> None:
    """The two bands are the locked floats: live ±1.0s, debrief ±2.0s."""
    assert LIVE_TOLERANCE_S == 1.0
    assert DEBRIEF_TOLERANCE_S == 2.0


# =========================================================================== #
# (1) Strip consistency — same orphan stripped in BOTH bands                   #
# =========================================================================== #


def test_orphan_stripped_in_both_live_and_debrief() -> None:
    """A citation NOT in the registry ([ev:GHOST@500.0]) is stripped in BOTH
    modes — one grammar, one registry, two bands, same orphan verdict.

    The wider debrief band does not rescue a fabricated citation: GHOST is not
    a registered key at all, so no tolerance widening can make it resolve.
    """
    reg = _registry_with_phase_at(120.0)
    snap = reg.snapshot()
    linter = CitationLinter()

    orphan = "Ghost moment [ev:GHOST@500.0]"

    live = linter.check(orphan, snap, mode="live")
    debrief = linter.check(orphan, snap, mode="debrief")

    assert live.valid is False
    assert live.reason == "invalid_atoms"
    assert debrief.valid is False
    assert debrief.reason == "invalid_atoms"


# =========================================================================== #
# (2) Accept consistency — grounded at ±1.0s accepted in BOTH bands            #
# =========================================================================== #


def test_grounded_within_live_band_accepted_in_both() -> None:
    """A citation 0.5s off the observation resolves within ±1.0s, so it is
    valid in live AND debrief — debrief never strips what live accepts on the
    same data (inclusion-monotonicity: live ⊆ debrief)."""
    reg = _registry_with_phase_at(120.0)
    snap = reg.snapshot()
    linter = CitationLinter()

    grounded = "Phase landed clean [ev:PHASE@120.5]"  # 0.5s off → within ±1.0s

    live = linter.check(grounded, snap, mode="live")
    debrief = linter.check(grounded, snap, mode="debrief")

    assert live.valid is True
    assert live.reason == "valid"
    assert debrief.valid is True
    assert debrief.reason == "valid"


# =========================================================================== #
# (3) The wider debrief band is intentional                                    #
# =========================================================================== #


def test_citation_in_debrief_only_band_is_live_invalid_debrief_valid() -> None:
    """A citation 1.5s off the observation: INVALID in live (±1.0s) but VALID
    in debrief (±2.0s). Documents the wider debrief band is deliberate and
    that live's accept set is a strict subset of debrief's on the same data."""
    reg = _registry_with_phase_at(120.0)
    snap = reg.snapshot()
    linter = CitationLinter()

    drifted = "Phase shift [ev:PHASE@121.5]"  # 1.5s off → outside ±1.0, in ±2.0

    live = linter.check(drifted, snap, mode="live")
    debrief = linter.check(drifted, snap, mode="debrief")

    assert live.valid is False, "1.5s off is outside the live ±1.0s band"
    assert live.reason == "invalid_atoms"
    assert debrief.valid is True, "1.5s off is inside the debrief ±2.0s band"
    assert debrief.reason == "valid"


# =========================================================================== #
# (4) Fail-loud on unknown mode                                                #
# =========================================================================== #


def test_unknown_mode_raises_value_error() -> None:
    """An unknown mode raises ValueError — fail loud, no silent default band."""
    reg = _registry_with_phase_at(120.0)
    linter = CitationLinter()
    with pytest.raises(ValueError):
        linter.check("[ev:PHASE@120.0]", reg.snapshot(), mode="bogus")
