# SPDX-License-Identifier: Apache-2.0

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from livekit.agents import Agent

import vibemix.agent.dj_cohost as dj_mod
from vibemix.agent import DJCoHostAgent
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST
from vibemix.prompts.matrix import build_system_instruction
from vibemix.state import MusicState


class _FakeRecorder:
    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict[str, Any]]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:
        pass


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def _build_agent(
    mocker: Any,
    tmp_path: Path,
    *,
    learn_progress: LearnProgress | None = None,
    cache: Any = None,
) -> DJCoHostAgent:
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = MusicState()
    state.mood = "coach"
    return DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=_FakeRecorder(tmp_path),
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
        learn_progress=learn_progress,
        cache=cache,
    )


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
        include_listening_fallback=False,
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
        include_listening_fallback=False,
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
    )


def test_refresh_coaching_aim_updates_gen_cfg_and_cache(
    clean_prompt_env, mocker, tmp_path
) -> None:
    initial_progress = LearnProgress()
    _make_competent(initial_progress, "harmonic_mixing")
    cache = mocker.MagicMock()
    cache.invalidate = AsyncMock()
    agent = _build_agent(
        mocker,
        tmp_path,
        learn_progress=initial_progress,
        cache=cache,
    )

    assert "smoother harmonic blends" in agent._prompt_body
    assert agent._gen_cfg.system_instruction == agent._prompt_body

    updated_progress = LearnProgress()
    _make_competent(updated_progress, "eq_mixing")
    changed = asyncio.run(agent.refresh_coaching_aim(updated_progress))

    assert changed is True
    assert "cleaner EQ swaps" in agent._prompt_body
    assert "smoother harmonic blends" not in agent._prompt_body
    assert agent._gen_cfg.system_instruction == agent._prompt_body
    cache.set_system_instruction_body.assert_called_once_with(agent._prompt_body)
    cache.invalidate.assert_awaited_once()

    cache.set_system_instruction_body.reset_mock()
    cache.invalidate.reset_mock()

    unchanged = asyncio.run(agent.refresh_coaching_aim(updated_progress))

    assert unchanged is False
    cache.set_system_instruction_body.assert_not_called()
    cache.invalidate.assert_not_awaited()
