# SPDX-License-Identifier: Apache-2.0
"""Codex curator persona seam tests.

The product Viber curator uses ``library.codex_curate``. These tests pin the
matrix-sourced voice and grounding rules without keeping the retired Gemini
``library.agent`` harness alive.
"""

from __future__ import annotations

from pathlib import Path

import vibemix.library.codex_curate as codex_mod
from vibemix.prompts.matrix import MOOD_PERSONAS

_TTS_TAG_HEADER = "TTS AUDIO TAGS"
_CITATION_GRAMMAR_HEADER = "CITATION GRAMMAR"
_TEACHER_PERSONA_FRAGMENT = "framework-anchored"
_RULES_HEADER = "RULES (non-negotiable)"
_NO_INVENT_CONTRACT = "Never invent a track_id"


def test_build_curator_instruction_is_importable_and_tutor_voiced() -> None:
    from vibemix.prompts.matrix import build_curator_instruction

    out = build_curator_instruction("tutor")
    assert isinstance(out, str) and out.strip()
    assert _TEACHER_PERSONA_FRAGMENT in out
    assert _TEACHER_PERSONA_FRAGMENT in MOOD_PERSONAS["teacher"]


def test_curator_instruction_omits_cohost_only_blocks() -> None:
    from vibemix.prompts.matrix import build_curator_instruction

    out = build_curator_instruction("tutor")
    assert _TTS_TAG_HEADER not in out
    assert _CITATION_GRAMMAR_HEADER not in out


def test_codex_curator_keeps_grounding_rules() -> None:
    src = codex_mod._SYSTEM_PROMPT
    assert _RULES_HEADER in src
    assert _NO_INVENT_CONTRACT in src
    assert "track_ids" in codex_mod._OUTPUT_SCHEMA["properties"]


def test_curator_rules_survive_in_built_prompt() -> None:
    built = codex_mod.build_prompt("warehouse peak-time")
    assert _RULES_HEADER in built
    assert _NO_INVENT_CONTRACT in built
    assert "Theme: warehouse peak-time" in built


def test_codex_curator_voice_sourced_from_matrix_seam() -> None:
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "vibemix"
        / "library"
        / "codex_curate.py"
    )
    src = src_path.read_text(encoding="utf-8")
    assert "build_curator_instruction" in src

    from vibemix.prompts.matrix import build_curator_instruction

    voice = build_curator_instruction("tutor")
    assert voice.split("\n", 1)[0] in codex_mod._SYSTEM_PROMPT


def _reset_seam_caches() -> None:
    codex_mod._SYSTEM_PROMPT_CACHE = None
    codex_mod._SYSTEM_PROMPT_LENS = None


def test_curator_seam_reads_shared_lens(tmp_path, monkeypatch) -> None:
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    store.extra["lens"] = "hype"
    cs_mod.save_config(store)

    _reset_seam_caches()
    try:
        voice = codex_mod._system_prompt()
        assert "party-anchored" in voice
        assert "party-anchored" in MOOD_PERSONAS["hype-man"]
    finally:
        _reset_seam_caches()


def test_curator_seam_defaults_to_tutor_when_lens_unset(tmp_path, monkeypatch) -> None:
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    assert "lens" not in store.extra
    cs_mod.save_config(store)

    _reset_seam_caches()
    try:
        voice = codex_mod._system_prompt()
        assert _TEACHER_PERSONA_FRAGMENT in voice
    finally:
        _reset_seam_caches()
