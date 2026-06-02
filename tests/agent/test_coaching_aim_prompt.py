# SPDX-License-Identifier: Apache-2.0

import pytest

import vibemix.agent.dj_cohost as dj_mod
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST
from vibemix.prompts.matrix import build_system_instruction


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


@pytest.fixture()
def clean_prompt_env(tmp_path, monkeypatch):
    import vibemix.runtime.config_store as cs_mod

    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    monkeypatch.setenv("VIBEMIX_MOOD", "coach")
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    cs_mod.save_config(cs_mod.ConfigStore())


def test_resolve_prompt_cell_threads_learn_aim_without_disk_load(clean_prompt_env) -> None:
    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")

    out = dj_mod._resolve_prompt_cell(learn_progress=progress)

    assert "LIVE COACHING AIM" in out
    assert "smoother harmonic blends" in out
    assert out == build_system_instruction(
        "intermediate",
        "coach",
        "coach",
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
        coaching_aim_skill="harmonic_mixing",
    )


def test_resolve_prompt_cell_without_progress_stays_current_shape(clean_prompt_env) -> None:
    out = dj_mod._resolve_prompt_cell()

    assert "LIVE COACHING AIM" not in out
    assert out == build_system_instruction(
        "intermediate",
        "coach",
        "coach",
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
    )
