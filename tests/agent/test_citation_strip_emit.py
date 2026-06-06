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
from vibemix.ui_bus import SessionCohostReaction

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
# key: deck-harmonic chip — DECK-03 (Phase 59)
# --------------------------------------------------------------------------


def test_key_citation_yields_chip_with_registry_timestamp_DECK03() -> None:
    """A grounded `[key:A:8A]` citation yields a chip.

    Anti-hallucination contract: the chip ``timestamp_s`` is sourced from the
    registry observation (the poller wrote A:8A at a session time), NOT parsed
    from the citation body (the body has no @t — it is `<deck>:<camelot>`).
    The full deck:camelot detail rides in ``event_id`` for the deep-link; the
    verb is the fixed letters-only "key" label.
    """
    reg = EvidenceRegistry()
    # The deck poller registers the EXACT body `A:8A` at a session-relative time.
    reg.write("key", "A:8A", 128.5)

    strip = _build_citation_strip(
        reaction_text="locked in harmonically [key:A:8A], ride it",
        registry=reg,
    )

    assert len(strip) == 1
    assert strip[0]["event_id"] == "key:A:8A"
    # timestamp comes from the registry (128.5), NOT the citation body.
    assert strip[0]["timestamp_s"] == pytest.approx(128.5, abs=0.01)
    assert strip[0]["verb"] == "key"


def test_fabricated_key_citation_yields_no_chip_DECK03() -> None:
    """A fabricated `[key:A:12B]` (never registered) → NO chip.

    Mirrors the empty-registry contract — the strip never fabricates a chip
    for a harmonic claim the poller did not observe. The poller wrote A:8A;
    the LLM's invented A:12B clash resolves to nothing → dropped.
    """
    reg = EvidenceRegistry()
    reg.write("key", "A:8A", 60.0)

    strip = _build_citation_strip(
        reaction_text="big clash [key:A:12B] watch out",
        registry=reg,
    )
    assert strip == []


def test_next_suggestion_mix_citation_chip_uses_schema_safe_label() -> None:
    """A grounded next-suggestion cite keeps the opaque id out of the chip label."""
    reg = EvidenceRegistry()
    reg.write("mix", "next_suggestion=folder:6837ec1665d7bb44", 0.0)

    strip = _build_citation_strip(
        reaction_text=(
            "This heavy low end shifted us darker. "
            "[mix:next_suggestion=folder:6837ec1665d7bb44]"
        ),
        registry=reg,
    )

    assert strip == [
        {
            "event_id": "mix:next_suggestion=folder:6837ec1665d7bb44",
            "verb": "next suggestion",
            "timestamp_s": 0.0,
        }
    ]
    assert len(strip[0]["verb"]) <= 32
    assert SessionCohostReaction.make(
        text="This heavy low end shifted us darker. ",
        event_id="TRACK_CHANGE",
        citation_strip=strip,
    ).to_dict()["payload"]["citation_strip"] == strip


# --------------------------------------------------------------------------
# recall: past-session callback chip — COPILOT-01 (Phase 66)
# --------------------------------------------------------------------------
# These tests clone the `key` precedent above (test_key_citation_* /
# test_fabricated_key_*) token-for-token, swapping the source/body/verb:
#   - source "key"    → "recall"
#   - body   "A:8A"   → "20260520-2200:7"  (session_id:seq, opaque)
#   - verb   "key"    → "recall"            (fixed letters-only label)
#
# RED contract (Wave 0, RED-first): today the allow-list at
# src/vibemix/agent/dj_cohost.py:215 is ("ev","mix","midi","key") —
# `recall` is excluded. The `continue` skips both tests' chip path, so
# `strip == []` for BOTH the grounded and the fabricated cases. The
# fabricated test trivially passes today (empty strip is the expected
# shape); the grounded test FAILS for the right structural reason
# (allow-list missing `recall` → no chip emitted even when the registry
# has the survivor). Plan 02 flips both: grounded yields a chip; fabricated
# stays empty (registry lookup misses → `continue` per existing logic).
#
# Anti-hallucination invariant: the chip ``timestamp_s`` comes from the
# registry write (current turn's t_session per Pitfall 3 in 66-RESEARCH.md),
# NEVER a past Record's `.ts`. The "the coach made a recall move just now"
# semantic is locked at CONTEXT.md Area 3 Q3.


def test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01() -> None:
    """A grounded `[recall:<session_id>:<seq>]` citation yields a chip.

    Anti-hallucination contract: the chip ``timestamp_s`` is sourced from the
    registry observation (the recall registration loop at dj_cohost.py:771
    writes the CURRENT turn's set_seconds — when the callback FIRED), NOT
    parsed from the citation body (the body has no @t — it is the opaque
    ``<session_id>:<seq>`` shape). The full record_id rides in ``event_id``
    for the deep-link; the verb is the fixed letters-only "recall" label
    (mirroring the `key` precedent — opaque body → fixed verb).

    RED reason (today): the allow-list at dj_cohost.py:215 excludes "recall"
    so the `continue` at :216 skips the chip path entirely → strip == [].
    Plan 02 Task 1 adds "recall" to the tuple and the test flips GREEN.
    """
    reg = EvidenceRegistry()
    # The agent's recall registration loop writes (source, record_id,
    # t_session). For the chip-strip test we register the exact body
    # `20260520-2200:7` at the current turn's session-relative time.
    reg.write("recall", "20260520-2200:7", 128.5)

    strip = _build_citation_strip(
        reaction_text="great call, [recall:20260520-2200:7]",
        registry=reg,
    )

    assert len(strip) == 1
    assert strip[0]["event_id"] == "recall:20260520-2200:7"
    # timestamp comes from the registry write (128.5), NOT a past Record's .ts.
    # Pitfall 3 in 66-RESEARCH.md: "the chip surface is 'the coach made a
    # recall move just now'; the past moment is the *evidence*, not the
    # visible event" — so timestamp_s must equal the REGISTRY write t.
    assert strip[0]["timestamp_s"] == pytest.approx(128.5, abs=0.01)
    # Fixed letters-only "recall" verb — mirrors the `key` precedent for
    # opaque/structured bodies. Stays inside the locked verb format
    # `^[a-z]+( [a-z]+){0,2}$` pinned by test_verb_format_is_two_to_three_lowercase_words.
    assert strip[0]["verb"] == "recall"


def test_fabricated_recall_yields_no_chip_COPILOT01() -> None:
    """A fabricated `[recall:<unregistered>]` → NO chip.

    GREEN today via the allow-list exclusion path: dj_cohost.py:215 excludes
    "recall" so the `continue` skips the body BEFORE the registry lookup ever
    runs — strip == [] regardless of registry state. GREEN after Plan 02 via
    the registry-existence check (allow-list lets "recall" through; the
    snapshot lookup for the fabricated id returns None; the existing
    `if not timestamps: continue` at :220 drops the chip). Same final state,
    different enforcement path. Pinning the contract regardless of which
    path enforces it (the fabricated-id never surfaces as a chip).

    In practice this turn-shape is already covered upstream by the
    CitationLinter (fabricated [recall:<id>] strips the WHOLE turn — Phase
    65 anti-poisoning gate). This test pins the local strip-builder's
    behavior in isolation, complementing the linter test in
    tests/agent/test_dj_cohost_linter.py.
    """
    reg = EvidenceRegistry()
    reg.write("recall", "20260520-2200:7", 60.0)

    strip = _build_citation_strip(
        reaction_text="remember [recall:20260520-2200:9] when you killed it",
        registry=reg,
    )
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
