# SPDX-License-Identifier: Apache-2.0
"""Phase 44 Plan 44-03 Task 1 — DJCoHostAgent citation-strip emit path.

LAUNCH-02: live UI surfaces a `[<verb> @ <mm:ss>]` chip per AI reaction,
sourced from the existing EvidenceRegistry citations parsed off the
reaction text. The backend builds the structured chip-strip payload and
attaches it to the per-reaction WS broadcast.

Contract (per 44-03-PLAN.md `must_haves`):

    citation_strip: list[dict]
    each entry: {"event_id": str, "verb": str, "timestamp_s": float}
    cap at 3 chips per reaction (UI cleanliness)
    empty list (NOT None) when registry has no match — keep type stable

Fixtures cover the three meaningful shapes:

    (a) reaction text with 2 grounded citations → 2 chips
    (b) reaction text with 5 grounded citations → 3 chips (cap enforced)
    (c) reaction text with 0 citations          → 0 chips (empty list)

Determinism: the helper under test (`_build_citation_strip`) is sync,
pure (registry-snapshot in / list out), and never touches asyncio or
ipc_bus — these tests assert the data shape, not the publish wiring.
The publish wiring is exercised end-to-end via the existing overlay
publish coverage pattern (see tests/agent/test_overlay_publish.py).
"""

from __future__ import annotations

import re

import pytest

from vibemix.agent.dj_cohost import _build_citation_strip
from vibemix.state import EvidenceRegistry


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def registry_with_grounded_events() -> EvidenceRegistry:
    """A registry pre-loaded with 5 `ev` observations across realistic
    DJ-session timestamps. Lets the cap-at-3 + verb-derivation paths run
    against a populated source-dict instead of an empty stub."""
    reg = EvidenceRegistry()
    # Seed 5 event fires at increasing session-relative times — body shape
    # `KEY@t.t` mirrors the EvidenceRegistry grammar contract (parse_citations
    # returns `(source, "KEY@t.t")` for each atom). The helper derives the
    # 2-3 word verb from the KEY portion (KICK_SWAP → "kick swap").
    reg.write("ev", "KICK_SWAP@45.2", 45.2)
    reg.write("ev", "LAYER_DROP@90.0", 90.0)
    reg.write("ev", "HIGH_PASS@153.6", 153.6)
    reg.write("ev", "FILTER_RIDE@200.5", 200.5)
    reg.write("ev", "BREAKDOWN@260.0", 260.0)
    return reg


# --------------------------------------------------------------------------
# (a) 2 citations → 2 chips
# --------------------------------------------------------------------------


def test_two_citations_yields_two_chips(
    registry_with_grounded_events: EvidenceRegistry,
) -> None:
    """Reaction text carries 2 `[ev:KEY@t]` atoms — both present in the
    registry. Output: 2 chips, in the order they appear in the text."""
    reaction_text = (
        "Sick kick swap [ev:KICK_SWAP@45.2] right before the layer drop "
        "[ev:LAYER_DROP@90.0] — keep that energy."
    )
    strip = _build_citation_strip(
        reaction_text=reaction_text,
        registry=registry_with_grounded_events,
    )

    assert len(strip) == 2

    # First chip — KICK_SWAP at 45.2s.
    assert strip[0]["event_id"] == "ev:KICK_SWAP@45.2"
    assert strip[0]["timestamp_s"] == pytest.approx(45.2, abs=0.01)
    # Verb is 2-3 words, lowercase, space-joined: "kick swap"
    assert strip[0]["verb"] == "kick swap"

    # Second chip — LAYER_DROP at 90.0s.
    assert strip[1]["event_id"] == "ev:LAYER_DROP@90.0"
    assert strip[1]["timestamp_s"] == pytest.approx(90.0, abs=0.01)
    assert strip[1]["verb"] == "layer drop"


# --------------------------------------------------------------------------
# (b) 5 citations → 3 chips (cap)
# --------------------------------------------------------------------------


def test_five_citations_capped_at_three_chips(
    registry_with_grounded_events: EvidenceRegistry,
) -> None:
    """5 citations in the reaction → output capped at 3 (UI cleanliness).
    Cap preserves order: first 3 atoms in the text win."""
    reaction_text = (
        "[ev:KICK_SWAP@45.2] [ev:LAYER_DROP@90.0] [ev:HIGH_PASS@153.6] "
        "[ev:FILTER_RIDE@200.5] [ev:BREAKDOWN@260.0]"
    )
    strip = _build_citation_strip(
        reaction_text=reaction_text,
        registry=registry_with_grounded_events,
    )

    assert len(strip) == 3  # capped
    # First 3 in text order survive the cap.
    assert strip[0]["event_id"] == "ev:KICK_SWAP@45.2"
    assert strip[1]["event_id"] == "ev:LAYER_DROP@90.0"
    assert strip[2]["event_id"] == "ev:HIGH_PASS@153.6"
    # FILTER_RIDE + BREAKDOWN dropped (cap behavior, not a bug — the UI
    # would feel crowded with >3 chips per reaction).
    for chip in strip:
        assert chip["event_id"] != "ev:FILTER_RIDE@200.5"
        assert chip["event_id"] != "ev:BREAKDOWN@260.0"


# --------------------------------------------------------------------------
# (c) Zero citations → empty list (NOT None)
# --------------------------------------------------------------------------


def test_no_citations_yields_empty_list(
    registry_with_grounded_events: EvidenceRegistry,
) -> None:
    """Reaction text with no citations → empty list. Critical: empty list,
    NOT None — keeps the WS payload type stable so the TS contract on
    `citation_strip: CitationChip[]` does not need a null-narrowing branch
    at every consumer."""
    reaction_text = "nice transition — really clean"
    strip = _build_citation_strip(
        reaction_text=reaction_text,
        registry=registry_with_grounded_events,
    )

    assert strip == []
    assert strip is not None  # explicit — keep type stable


def test_empty_registry_yields_empty_list() -> None:
    """Even when reaction has citation atoms, an empty registry → no chips.
    The helper must NOT fabricate timestamps from the citation body — it
    looks up the registry. If the lookup fails, the chip is dropped (no
    truthy garbage — closes 'invented timestamps' hallucination class)."""
    reg = EvidenceRegistry()  # empty registry
    reaction_text = "nice [ev:KICK_SWAP@45.2] move"
    strip = _build_citation_strip(reaction_text=reaction_text, registry=reg)
    assert strip == []


# --------------------------------------------------------------------------
# Verb format contract — pinned because the chip text relies on this shape
# --------------------------------------------------------------------------


def test_verb_format_is_two_to_three_lowercase_words(
    registry_with_grounded_events: EvidenceRegistry,
) -> None:
    """Verb derivation contract — locked here so the UI chip format
    `[<verb> @ <mm:ss>]` stays terse + readable.

    Rule: strip the `@<t>` suffix off the body, split the KEY on `_`,
    lowercase, join with single space. Cap at 3 words (trim trailing
    pieces so multi-word keys don't blow out chip width).
    """
    text = "[ev:KICK_SWAP@45.2] [ev:LAYER_DROP@90.0]"
    strip = _build_citation_strip(
        reaction_text=text,
        registry=registry_with_grounded_events,
    )
    pat = re.compile(r"^[a-z]+( [a-z]+){0,2}$")  # 1-3 lowercase words
    for chip in strip:
        assert pat.match(chip["verb"]), (
            f"verb {chip['verb']!r} violates the locked format "
            "(1-3 lowercase words joined by single spaces)"
        )
