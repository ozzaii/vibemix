# SPDX-License-Identifier: Apache-2.0
"""BENCH-01 — cell-assembly tests (REAL-GREEN — flipped in Plan 02).

The Wave-0 scaffolds (``xfail(strict=True)``) flipped to real passes when
Plan 02 landed ``vibemix.bench.{cell,assemble,matrix,fixtures}``.

The assembler's job (81-RESEARCH §Dimension→Seam Map, 81-PATTERNS "assemble.py"):
compose ONE prompt per ``BenchCell`` by calling the REAL product seams
(``build_lens_instruction`` / ``AICoach.build_prompt`` / ``build_parts_description``
/ ``model_router.resolve``) — never re-author prompt text (Pitfall 1). The model
comes from the router, never a literal (Pitfall 4).
"""

from __future__ import annotations

from vibemix.prompts.matrix import build_lens_instruction
from vibemix.llm import model_router


def test_hype_cell_reuses_lens_seam() -> None:
    """A hype cell's system instruction reuses build_lens_instruction('hype', ...)
    output — the bench measures the REAL product voice, not a baked literal."""
    from vibemix.bench.assemble import build_cell_prompt
    from vibemix.bench.cell import BenchCell

    cell = BenchCell(
        model_path="library_auto_tag",
        grounding="audio+dsp",
        prompting="structured",
        contexting="snapshot",
        lens="hype",
        taste="without_rubric",
    )
    system, contents, model, tier = build_cell_prompt(cell)
    expected_voice = build_lens_instruction("hype", "intermediate")
    # The real lens voice is woven into the cell's system instruction.
    assert expected_voice[:80] in system


def test_no_audio_cell() -> None:
    """THE empirical heart — the dsp_only cell sends ZERO audio Parts yet a
    NON-EMPTY evidence body. If Gemini grounds a sharp reaction on the DSP
    snapshot alone, the intelligence resided in the EAR, not the raw ear."""
    from vibemix.bench.assemble import build_cell_prompt
    from vibemix.bench.cell import BenchCell

    cell = BenchCell(
        model_path="library_auto_tag",
        grounding="dsp_only",
        prompting="structured",
        contexting="snapshot",
        lens="hype",
        taste="without_rubric",
    )
    system, contents, model, tier = build_cell_prompt(cell)
    # No audio Part appended for the no-audio cell.
    audio_parts = [
        p for p in contents
        if not isinstance(p, str) and getattr(p, "inline_data", None) is not None
    ]
    assert audio_parts == []
    # ...but the evidence body is populated (the structured DSP grounding).
    body = "".join(p for p in contents if isinstance(p, str))
    assert body.strip() != ""
    assert "hearing" in body or "groove" in body or "bpm" in body.lower()


def test_structured_passes_snapshot_generic_passes_none() -> None:
    """The prompting axis: a structured cell passes a registry_snapshot to the
    coach (full anti-slop stack); a generic cell passes None (the no-structure
    control). Distinct, non-empty assembled prompts."""
    from vibemix.bench.assemble import build_cell_prompt
    from vibemix.bench.cell import BenchCell

    common = dict(
        model_path="library_auto_tag",
        grounding="dsp_only",
        contexting="snapshot",
        lens="hype",
        taste="without_rubric",
    )
    structured = build_cell_prompt(BenchCell(prompting="structured", **common))
    generic = build_cell_prompt(BenchCell(prompting="generic", **common))
    sys_struct = structured[0]
    sys_generic = generic[0]
    # The structured prompt carries the citation grammar; the generic control
    # does not — they are NOT byte-identical.
    assert sys_struct != sys_generic


def test_model_from_router_not_literal() -> None:
    """The model axis resolves through model_router.resolve — NEVER a literal.
    The resolved id must equal the router's id for the cell's alias (asserted
    via the router, so no Gemini literal lives in this test)."""
    from vibemix.bench.assemble import build_cell_prompt
    from vibemix.bench.cell import BenchCell

    cell = BenchCell(
        model_path="library_auto_tag",
        grounding="dsp_only",
        prompting="structured",
        contexting="snapshot",
        lens="hype",
        taste="without_rubric",
    )
    _system, _contents, model, tier = build_cell_prompt(cell)
    expected_model, expected_tier = model_router.resolve("library_auto_tag")
    assert model == expected_model
    assert tier == expected_tier
