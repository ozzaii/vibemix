# SPDX-License-Identifier: Apache-2.0
"""Phase 77 Plan 01 (Wave 0) — WIRE-04 failing scaffold: shared persona seam.

Both curator backends (gemini = ``library/agent.py``, codex =
``library/codex_curate.py``) hardcode their own ``_SYSTEM_INSTRUCTION`` /
``_SYSTEM_PROMPT`` voice and never import the live persona matrix. WIRE-04
makes ``prompts/matrix.py`` the single source of truth: a NEW
``build_curator_instruction(lens="tutor")`` composes the lens voice WITHOUT the
co-host runtime blocks (citation-grammar / TTS-tag DSL), and both backends
prepend it to their existing — verbatim-preserved — grounding RULES.

Three tiers:

  * SEAM EXISTS — ``prompts.matrix.build_curator_instruction`` is importable and
    emits the teacher/tutor persona vocabulary but NOT the co-host-only blocks
    (TTS tag DSL header + CITATION GRAMMAR header are ABSENT). xfail-strict
    until Plan 02 adds the function.
  * RULES PRESERVED — both curator system prompts STILL carry the verbatim
    "RULES (non-negotiable)" / "Never invent a track_id" grounding contract.
    GREEN now — LOCKS that Plan 02's voice swap does not drop the grounding.
  * VOICE-FROM-SEAM — the curator voice is SOURCED from the matrix seam
    (the system prompt contains the build_curator_instruction output).
    xfail-strict until Plan 02.

No network, no genai.Client, no API key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import vibemix.library.agent as agent_mod
import vibemix.library.codex_curate as codex_mod
from vibemix.prompts.matrix import MOOD_PERSONAS

# Stable substrings from the co-host-only blocks that MUST be ABSENT from the
# curator instruction (a text curator has no TTS expressivity, no live-event
# citation grammar). Drawn verbatim from matrix.py block headers.
_TTS_TAG_HEADER = "TTS AUDIO TAGS"
_CITATION_GRAMMAR_HEADER = "CITATION GRAMMAR"

# A stable fragment of the teacher persona vocabulary (the "tutor" lens maps
# onto the teacher mood per CONTEXT Q2: tutor→teacher).
_TEACHER_PERSONA_FRAGMENT = "framework-anchored"

# The verbatim grounding contract both backends MUST keep.
_RULES_HEADER = "RULES (non-negotiable)"
_NO_INVENT_CONTRACT = "Never invent a track_id"


# ---------------------------------------------------------------------------
# Tier 1 — SEAM EXISTS (xfail-strict until Plan 02 adds build_curator_instruction)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="WIRE-04 build_curator_instruction not yet added (Plan 02)",
    strict=True,
)
def test_build_curator_instruction_is_importable_and_tutor_voiced() -> None:
    """matrix.build_curator_instruction('tutor') emits the teacher persona voice."""
    from vibemix.prompts.matrix import build_curator_instruction

    out = build_curator_instruction("tutor")
    assert isinstance(out, str) and out.strip()
    # The tutor lens draws the teacher persona vocabulary.
    assert _TEACHER_PERSONA_FRAGMENT in out
    # Sanity: the teacher persona fragment really is the one we expect.
    assert _TEACHER_PERSONA_FRAGMENT in MOOD_PERSONAS["teacher"]


@pytest.mark.xfail(
    reason="WIRE-04 build_curator_instruction not yet added (Plan 02)",
    strict=True,
)
def test_curator_instruction_omits_cohost_only_blocks() -> None:
    """The curator instruction excludes the live co-host runtime blocks.

    A text curator must NOT carry the TTS-expressivity DSL or the live-event
    CITATION GRAMMAR — those are co-host-runtime-only. build_curator_instruction
    composes the lens voice WITHOUT them.
    """
    from vibemix.prompts.matrix import build_curator_instruction

    out = build_curator_instruction("tutor")
    assert _TTS_TAG_HEADER not in out, "curator instruction leaked the TTS tag DSL"
    assert _CITATION_GRAMMAR_HEADER not in out, (
        "curator instruction leaked the live-event CITATION GRAMMAR block"
    )


# ---------------------------------------------------------------------------
# Tier 2 — RULES PRESERVED (GREEN now — locks the grounding contract survives)
# ---------------------------------------------------------------------------


def test_gemini_curator_keeps_grounding_rules() -> None:
    """library/agent.py _SYSTEM_INSTRUCTION still carries the grounding RULES."""
    src = agent_mod._SYSTEM_INSTRUCTION
    assert _RULES_HEADER in src
    assert _NO_INVENT_CONTRACT in src
    # The interactive variant keeps its anti-invention contract too.
    assert "never invent a track" in agent_mod._INTERACTIVE_SYSTEM_INSTRUCTION


def test_codex_curator_keeps_grounding_rules() -> None:
    """library/codex_curate.py _SYSTEM_PROMPT still carries the grounding RULES."""
    src = codex_mod._SYSTEM_PROMPT
    assert _RULES_HEADER in src
    assert _NO_INVENT_CONTRACT in src
    # The codex final-JSON output schema contract is untouched.
    assert "track_ids" in codex_mod._OUTPUT_SCHEMA["properties"]


def test_curator_rules_survive_in_built_prompt() -> None:
    """codex build_prompt(theme) embeds the verbatim RULES (no silent drop)."""
    built = codex_mod.build_prompt("warehouse peak-time")
    assert _RULES_HEADER in built
    assert _NO_INVENT_CONTRACT in built
    assert "Theme: warehouse peak-time" in built


# ---------------------------------------------------------------------------
# Tier 3 — VOICE-FROM-SEAM (xfail-strict until Plan 02 wires the swap)
# ---------------------------------------------------------------------------


def _curator_source(mod_name: str) -> str:
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "vibemix"
        / "library"
        / mod_name
    )
    return src_path.read_text(encoding="utf-8")


@pytest.mark.xfail(
    reason="WIRE-04 voice-from-seam swap not yet wired (Plan 02)", strict=True
)
def test_gemini_curator_voice_sourced_from_matrix_seam() -> None:
    """library/agent.py sources its persona voice from build_curator_instruction."""
    src = _curator_source("agent.py")
    assert "build_curator_instruction" in src
    # The voice prefix is the curator instruction (composed at module import).
    from vibemix.prompts.matrix import build_curator_instruction

    voice = build_curator_instruction("tutor")
    assert voice.split("\n", 1)[0] in agent_mod._SYSTEM_INSTRUCTION


@pytest.mark.xfail(
    reason="WIRE-04 voice-from-seam swap not yet wired (Plan 02)", strict=True
)
def test_codex_curator_voice_sourced_from_matrix_seam() -> None:
    """library/codex_curate.py sources its persona voice from the matrix seam."""
    src = _curator_source("codex_curate.py")
    assert "build_curator_instruction" in src
    from vibemix.prompts.matrix import build_curator_instruction

    voice = build_curator_instruction("tutor")
    assert voice.split("\n", 1)[0] in codex_mod._SYSTEM_PROMPT
