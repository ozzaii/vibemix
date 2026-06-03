# SPDX-License-Identifier: Apache-2.0
"""Phase 79 Plan 01 (Wave 0) — LENS Nyquist safety net.

The lens layer (LENS-01 = the shared lens→cell map + ``build_lens_instruction``;
LENS-02 = the one selection that flows to BOTH the live co-host and the curator)
is installed BEFORE any ``src/`` change. Every acceptance criterion gets a
failing ``xfail(strict=True)`` test that flips to a real pass when its
implementation plan lands (Plan 02 = LENS-01, Plan 03 = LENS-02). A silent
early-pass (an xfail that quietly starts passing) becomes an ``xpassed`` → HARD
failure under ``strict=True``, so we cannot ship a half-wired lens.

The ONE genuinely-real-green test here is ``test_v4_golden_anchor_present`` — it
documents that today's untouched ``build_system_instruction("intermediate",
"hype")`` byte-identity anchor exists and must never regress. The default-lens
byte-identity *equality* test is xfail-strict (it asserts against
``build_lens_instruction`` which does not exist until Plan 02) and flips green
the moment Plan 02 lands.

Anti-slop note (CLAUDE invariant #2): the ack-bank was RETIRED 2026-05-19 —
un-cited output now STRIPS to ``<silence/>``. The three-lenses-through-the-gate
proof asserts the strip *decision* is lens-independent; it never references an
ack-bank.

No network, no genai.Client, no API key — pure prompt-shape + strip-decision
assertions (mirrors the no-network discipline of
``tests/library/test_curator_persona_seam.py``).
"""

from __future__ import annotations

import pytest

from vibemix.coach.citation_linter import CitationLinter
from vibemix.prompts.matrix import MOOD_PERSONAS, build_system_instruction
from vibemix.state.evidence_registry import EvidenceRegistry, parse_citations

# Coach-mode persona substrings drawn verbatim from MOOD_PERSONAS (matrix.py:51).
# These are substituted into the COACH cell only (the {mood_persona} slot), so
# they identify the critique/tutor lenses — NOT the hype default, which is the
# v4 HYPE_INTERMEDIATE constant that predates MOOD_PERSONAS and carries no
# persona substitution. Sanity-pinned below so a persona-text edit fails here.
_COACH_FRAGMENT = "post-mortem-anchored"
_TEACHER_FRAGMENT = "framework-anchored"

# The hype default's stable opening — the decided Sven identity body. This is
# the HYPE_INTERMEDIATE cell (no {mood_persona} slot), so we grep its own text,
# not a MOOD_PERSONAS fragment.
_HYPE_DEFAULT_FRAGMENT = "You're Sven"

# LENS-01 (Plan 02) + LENS-02 (Plan 03) have landed — all lens scaffolds are now
# real-green; no remaining xfail-strict gates in this file.


# ---------------------------------------------------------------------------
# REAL GREEN — the v4 byte-identity anchor that must never regress
# ---------------------------------------------------------------------------


def test_v4_golden_anchor_present() -> None:
    """The default co-host cell exists today and carries the decided Sven identity.

    This is the byte-identity anchor: ``build_lens_instruction("hype",
    "intermediate")`` (Plan 02) must resolve to THIS exact prompt. Documenting
    it as a real-green pin means a regression in the untouched builder fails
    HERE, before the lens layer is even wired.
    """
    out = build_system_instruction("intermediate", "hype")
    assert isinstance(out, str) and out.strip()
    # The hype default carries its own opening, not a MOOD_PERSONAS slot.
    assert _HYPE_DEFAULT_FRAGMENT in out
    # Sanity: the coach-mode persona fragments really are the ones we grep for
    # in the critique/tutor lens-shape test below.
    assert _COACH_FRAGMENT in MOOD_PERSONAS["coach"]
    assert _TEACHER_FRAGMENT in MOOD_PERSONAS["teacher"]


# ---------------------------------------------------------------------------
# LENS-01 — shared lens→cell map (xfail-strict until Plan 02)
# ---------------------------------------------------------------------------


def test_lens_map_covers_three_canonical_lenses() -> None:
    """LENS_TO_MODE_MOOD maps all 3 canonical lenses to valid (mode, mood) cells."""
    from vibemix.prompts.matrix import LENS_TO_MODE_MOOD

    assert set(LENS_TO_MODE_MOOD.keys()) == {"hype", "critique", "tutor"}
    for lens, cell in LENS_TO_MODE_MOOD.items():
        assert isinstance(cell, tuple) and len(cell) == 2, (
            f"lens {lens!r} must map to a (mode, mood) tuple"
        )
        mode, mood = cell
        assert mode in {"hype", "coach"}, f"lens {lens!r} mode {mode!r} not a real mode"
        assert mood in MOOD_PERSONAS, f"lens {lens!r} mood {mood!r} not a real persona"


def test_lens_prompt_shape_per_lens() -> None:
    """Each lens yields a DISTINCT grounded prompt over the same builder.

    hype → hype-man persona markers; critique → coach-cell markers; tutor →
    teacher persona markers. Asserts the lens is a real cell selector, not a
    cosmetic label.
    """
    from vibemix.prompts.matrix import build_lens_instruction

    hype = build_lens_instruction("hype")
    critique = build_lens_instruction("critique")
    tutor = build_lens_instruction("tutor")

    # hype = the HYPE_INTERMEDIATE cell (its own opening, no persona slot);
    # critique = coach cell w/ coach persona; tutor = coach cell w/ teacher persona.
    assert _HYPE_DEFAULT_FRAGMENT in hype
    assert _COACH_FRAGMENT in critique
    assert _TEACHER_FRAGMENT in tutor
    # Three distinct grounded prompts — no two lenses collapse to the same text.
    assert len({hype, critique, tutor}) == 3


def test_unknown_lens_raises_value_error() -> None:
    """build_lens_instruction fails loud on an unknown lens (mirrors mood/skill)."""
    from vibemix.prompts.matrix import build_lens_instruction

    with pytest.raises(ValueError):
        build_lens_instruction("bogus")


def test_default_lens_byte_identical_to_cohost_default() -> None:
    """The default (hype) lens cold path equals today's co-host default byte-for-byte.

    Flips green in Plan 02 when ``build_lens_instruction`` lands: the hype lens
    must resolve to the exact ``build_system_instruction("intermediate",
    "hype")`` prompt — the v4 golden contract.
    """
    from vibemix.prompts.matrix import build_lens_instruction

    assert build_lens_instruction("hype", "intermediate") == build_system_instruction(
        "intermediate", "hype"
    )


def test_three_lenses_pass_the_same_gate() -> None:
    """The citation-grounding strip DECISION is lens-independent (invariant #2).

    Build a system instruction under each of the 3 lenses, then run a fixed
    CITED reply (cites a known track id) and a fixed UN-CITED reply (cites an
    absent id) through ``parse_citations`` + ``CitationLinter.check``. Assert
    ``LintResult.valid`` is identical across all three lenses for the cited
    case (all valid) AND for the un-cited case (all invalid → strips to
    ``<silence/>``). The linter validates atoms against the EvidenceRegistry
    snapshot only — it NEVER reads the prompt cell, so the lens cannot change
    the strip decision.
    """
    from vibemix.prompts.matrix import build_lens_instruction

    registry = EvidenceRegistry()
    registry.write("track", "deadmau5-strobe", 0.0)
    snapshot = registry.snapshot()

    cited = "Clean blend right there [track:deadmau5-strobe]"
    uncited = "Clean blend right there [track:phantom-track]"

    # Sanity: the fixtures parse to exactly one atom each (lens-independent).
    assert parse_citations(cited) == [("track", "deadmau5-strobe")]
    assert parse_citations(uncited) == [("track", "phantom-track")]

    linter = CitationLinter()
    cited_decisions = []
    uncited_decisions = []
    for lens in ("hype", "critique", "tutor"):
        # The lens drives ONLY the prompt cell — built here to prove it has no
        # bearing on the gate. The instruction itself is never passed to check().
        _ = build_lens_instruction(lens)
        cited_decisions.append(linter.check(cited, snapshot, mode="live").valid)
        uncited_decisions.append(linter.check(uncited, snapshot, mode="live").valid)

    # Cited reply → valid under every lens. Un-cited reply → strips under every
    # lens. The decision is identical across lenses (registry membership only).
    assert cited_decisions == [True, True, True]
    assert uncited_decisions == [False, False, False]


# ---------------------------------------------------------------------------
# LENS-02 — one selection flows to BOTH builders (xfail-strict until Plan 03)
# ---------------------------------------------------------------------------


def test_shared_selection_flows_to_both_builders(tmp_path, monkeypatch) -> None:
    """A single shared lens selection drives BOTH the co-host AND the curator.

    Set ``ConfigStore.extra["lens"]="critique"`` (persisted to a tmp path) and
    assert the shared-read helper Plan 03 adds resolves "critique" for both
    surfaces. The import path points at the TARGET seam Plan 03 builds, so this
    is xfail-strict until then.
    """
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    # Patch the resolver so the round-trip is hermetic (monkeypatch auto-undoes).
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)

    store = cs_mod.ConfigStore()
    store.extra["lens"] = "critique"
    cs_mod.save_config(store)

    # Plan 03 adds a single shared-read helper consumed by both builders.
    from vibemix.runtime.settings import read_shared_lens

    assert read_shared_lens(store) == "critique"
