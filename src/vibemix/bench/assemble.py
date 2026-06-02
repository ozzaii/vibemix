# SPDX-License-Identifier: Apache-2.0
"""build_cell_prompt — THE HEART: compose ONE prompt per cell from REAL seams.

This module is THIN COMPOSITION over the shipped Phase 77-80 product builders.
It NEVER re-authors prompt text (RESEARCH Pitfall 1) — it calls
``build_lens_instruction`` / ``AICoach.build_prompt`` / ``build_parts_description``
in the verified order and resolves the model via ``model_router.resolve`` (NO
literal — RESEARCH Pitfall 4, ``test_no_model_literal.py`` enforces).

Composition order (81-PATTERNS "assemble.py — THE HEART", lines 108-122):

    system = build_lens_instruction(lens, skill, include_citation_grammar=structured, ...)
             + (TASTE_RUBRIC if taste == "with_rubric" else "")
    ev = Event(type="HEARTBEAT", state=fixture_state_for(contexting, grounding))
    user_body = AICoach.build_prompt(ev, registry_snapshot=(snap if structured else None))
    parts_suffix = build_parts_description(audio_s, False, False, secondary_ear=cell.secondary_ear)
    contents = [system + user_body + parts_suffix] + ([audio_part] if cell.uses_audio else [])
    model, tier = model_router.resolve(cell.model_path)

The ``dsp_only`` (no-audio) cell appends NO audio Part but a fully-populated
evidence body — the milestone's empirical heart.
"""

from __future__ import annotations

from vibemix.bench.cell import BenchCell
from vibemix.bench.fixtures import fixture_state_for
from vibemix.bench.matrix import TASTE_RUBRIC
from vibemix.llm import model_router
from vibemix.prompts.matrix import (
    build_lens_instruction,
    build_parts_description,
)
from vibemix.state.event import Event
from vibemix.state.prompt_builder import AICoach

__all__ = ["build_cell_prompt"]


def build_cell_prompt(
    cell: BenchCell,
    *,
    audio_seconds: float = 80.0,
) -> tuple[str, list, str, object]:
    """Compose ``(system, contents, model, tier)`` for one bench cell.

    The ``contents`` list is the assembled prompt body string, optionally
    followed by an audio-Part PLACEHOLDER position — the runner
    (:mod:`vibemix.bench.run`) attaches the real ``types.Part`` bytes for
    audio-grounding cells. This function stays pure (no file I/O), so it is
    offline-green for the assemble tests; only the runner touches the disk.

    Args:
        cell: the 6-D matrix point.
        audio_seconds: the live-mix audio length rendered into the parts
            suffix (default 80.0 — the embed/excerpt length).

    Returns:
        ``(system, contents, model_id, tier)``. ``model_id`` + ``tier`` come
        from ``model_router.resolve(cell.model_path)`` — never a literal.
    """
    structured = cell.structured

    # --- lens axis (the system instruction) + the prompting flags ---------- #
    # `structured` engages the full anti-slop stack (citation grammar + tag DSL
    # + listening fallback = the live defaults). `generic` is the no-structure
    # control: the bare DJ voice with all the anti-slop scaffolding suppressed.
    system = build_lens_instruction(
        cell.lens,
        cell.skill,
        include_citation_grammar=structured,
        include_listening_fallback=structured,
        include_tag_dsl=structured,
    )
    # --- taste axis (the one authored fragment — a FIXED placeholder) ------ #
    if cell.taste == "with_rubric":
        system = system + TASTE_RUBRIC

    # --- contexting + grounding axes (the evidence packet body) ------------ #
    state, snap = fixture_state_for(cell.contexting, cell.grounding)
    ev = Event(type="HEARTBEAT", state=state)
    # structured → pass the grounded snapshot (the evidence-corpus footer +
    # citation priming fires); generic → None (the no-structure control).
    user_body = AICoach.build_prompt(
        ev,
        registry_snapshot=(snap if structured else None),
    )

    # --- grounding-framing axis (the audio-Part suffix) -------------------- #
    # secondary_ear framing only on the audio+dsp grounding cells (Phase-80).
    parts_suffix = build_parts_description(
        audio_seconds,
        False,  # has_mic_part — bench cells never attach a mic Part
        False,  # has_lookahead_part — bench cells never attach a lookahead Part
        secondary_ear=cell.secondary_ear,
    )

    # The assembled text body. The runner appends the real audio Part bytes for
    # audio-grounding cells; the dsp_only (no-audio) cell stays text-only.
    contents: list = [system + user_body + parts_suffix]

    # --- model axis (router alias → id; NEVER a literal) ------------------- #
    model, tier = model_router.resolve(cell.model_path)

    return system, contents, model, tier
