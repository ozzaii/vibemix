# SPDX-License-Identifier: Apache-2.0
"""DJ-COHOST-MATRIX dispatch — VIBEMIX_SKILL_LEVEL + VIBEMIX_MODE env vars
select the right cell from the prompt matrix.

Defaults (no env vars set) → ``("intermediate", "hype")`` = HYPE_INTERMEDIATE
= byte-identical to v4 SYSTEM_INSTRUCTION (backward compat invariant).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.prompts.matrix import (
    COACH_BEGINNER,
    COACH_INTERMEDIATE,
    COACH_PRO,
    HYPE_BEGINNER,
    HYPE_INTERMEDIATE,
    HYPE_PRO,
    MOOD_PERSONAS,
)


def _coach_rendered(template: str, mood: str = "hype-man") -> str:
    """Apply the Phase 13-05 mood-persona substitution to a COACH_* template.

    The default mood ('hype-man') is what _resolve_prompt_cell picks when
    VIBEMIX_MOOD is unset (which matches the env state of the Phase 10
    dispatch tests below — they never set VIBEMIX_MOOD).
    """
    return template.replace("{mood_persona}", MOOD_PERSONAS[mood])
from vibemix.state import MusicState

# ---------- shared minimal stubs (mirror tests/agent/test_dj_cohost.py) ----


class _FakeRecorder:
    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:
        pass


def _build_state() -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.audible_track = "Daft Punk - Around the World"
    s.audible_track_confidence = 0.8
    s.phase = "peak"
    s.rms = 0.05
    s.bpm = 128.0
    return s


def _instructions_kw_for_env(mocker, tmp_path: Path) -> str:
    """Construct a DJCoHostAgent and return the ``instructions`` arg passed
    to the parent ``Agent.__init__`` — that's the prompt cell the env vars
    selected."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    return Agent.__init__.call_args.kwargs["instructions"]


# ---------- env-var fixture: clear before, restore after ------------------


@pytest.fixture
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure VIBEMIX_SKILL_LEVEL and VIBEMIX_MODE are unset for the test."""
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)
    monkeypatch.delenv("VIBEMIX_MODE", raising=False)
    yield


# ---------- defaults (no env vars) ----------------------------------------


def test_dispatch_01_defaults_to_intermediate_hype(mocker, tmp_path, _clean_env) -> None:
    """Unset env vars → HYPE_INTERMEDIATE (= v4 SYSTEM_INSTRUCTION = backward
    compat with Phase 4)."""
    instructions = _instructions_kw_for_env(mocker, tmp_path)
    assert instructions == HYPE_INTERMEDIATE


def test_dispatch_02_default_equals_persona_system_instruction(
    mocker, tmp_path, _clean_env
) -> None:
    """Default also equals vibemix.agent.persona.SYSTEM_INSTRUCTION (the
    re-export). Pins backward-compat invariant for callers reading SYSTEM_INSTRUCTION."""
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    instructions = _instructions_kw_for_env(mocker, tmp_path)
    assert instructions == SYSTEM_INSTRUCTION
    assert instructions == HYPE_INTERMEDIATE  # transitive


# ---------- explicit env-var dispatch ------------------------------------


@pytest.mark.parametrize(
    "skill,mode,expected_cell",
    [
        ("beginner", "hype", HYPE_BEGINNER),
        ("intermediate", "hype", HYPE_INTERMEDIATE),
        ("pro", "hype", HYPE_PRO),
        # COACH_* templates carry a {mood_persona} placeholder (Phase 13-05).
        # The default mood ('hype-man') is substituted at dispatch time.
        ("beginner", "coach", _coach_rendered(COACH_BEGINNER)),
        ("intermediate", "coach", _coach_rendered(COACH_INTERMEDIATE)),
        ("pro", "coach", _coach_rendered(COACH_PRO)),
    ],
)
def test_dispatch_03_each_cell_selectable_via_env(
    mocker, tmp_path, monkeypatch, skill, mode, expected_cell
) -> None:
    """Setting VIBEMIX_SKILL_LEVEL + VIBEMIX_MODE selects the right cell."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", skill)
    monkeypatch.setenv("VIBEMIX_MODE", mode)
    instructions = _instructions_kw_for_env(mocker, tmp_path)
    assert instructions == expected_cell


def test_dispatch_04_pro_coach_via_env(mocker, tmp_path, monkeypatch) -> None:
    """Spot-check: VIBEMIX_SKILL_LEVEL=pro + VIBEMIX_MODE=coach → COACH_PRO."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "pro")
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    instructions = _instructions_kw_for_env(mocker, tmp_path)
    # Phase 13-05: COACH templates are rendered with the mood persona; the
    # default mood ('hype-man') is picked when VIBEMIX_MOOD is unset.
    assert instructions == _coach_rendered(COACH_PRO)
    assert "phrase ended on the 3" in instructions  # COACH_PRO anchor


def test_dispatch_05_case_insensitive_via_env(mocker, tmp_path, monkeypatch) -> None:
    """Env vars are case-insensitive (VIBEMIX_MODE=COACH should still resolve)."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "PRO")
    monkeypatch.setenv("VIBEMIX_MODE", "COACH")
    instructions = _instructions_kw_for_env(mocker, tmp_path)
    assert instructions == _coach_rendered(COACH_PRO)


# ---------- gen_cfg.system_instruction also picks up the dispatch ---------


def test_dispatch_06_gen_cfg_system_instruction_matches_dispatch(
    mocker, tmp_path, monkeypatch
) -> None:
    """The internal _gen_cfg.system_instruction (used in google.genai calls)
    also reflects the env-var dispatch — not just the LiveKit-side
    ``instructions`` arg."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "beginner")
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    agent = DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    # Phase 13-05: mood-persona substitution applies to COACH cells.
    assert agent._gen_cfg.system_instruction == _coach_rendered(COACH_BEGINNER)


# ---------- invalid env values fail loudly --------------------------------


def test_dispatch_07_invalid_skill_raises(mocker, tmp_path, monkeypatch) -> None:
    """Invalid VIBEMIX_SKILL_LEVEL → ValueError (not silent fallback)."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "expert")
    monkeypatch.setenv("VIBEMIX_MODE", "hype")
    mocker.patch.object(Agent, "__init__", return_value=None)
    with pytest.raises(ValueError):
        DJCoHostAgent(
            genai_client=mocker.MagicMock(),
            clean_audio_buf=mocker.MagicMock(),
            screen_buf=mocker.MagicMock(),
            state=_build_state(),
            recorder=_FakeRecorder(tmp_path),
            llm_inst=mocker.MagicMock(),
            tts_inst=mocker.MagicMock(),
        )


def test_dispatch_08_invalid_mode_raises(mocker, tmp_path, monkeypatch) -> None:
    """Invalid VIBEMIX_MODE → ValueError."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "intermediate")
    monkeypatch.setenv("VIBEMIX_MODE", "critic")
    mocker.patch.object(Agent, "__init__", return_value=None)
    with pytest.raises(ValueError):
        DJCoHostAgent(
            genai_client=mocker.MagicMock(),
            clean_audio_buf=mocker.MagicMock(),
            screen_buf=mocker.MagicMock(),
            state=_build_state(),
            recorder=_FakeRecorder(tmp_path),
            llm_inst=mocker.MagicMock(),
            tts_inst=mocker.MagicMock(),
        )


# ---------- CLAUDE.md privacy check: env vars don't get logged ------------


def test_dispatch_09_env_var_values_not_logged_to_recorder(mocker, tmp_path, monkeypatch) -> None:
    """Sanity: VIBEMIX_SKILL_LEVEL / VIBEMIX_MODE are not echoed into
    recorder events (they're config, not session state)."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "pro")
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    mocker.patch.object(Agent, "__init__", return_value=None)
    recorder = _FakeRecorder(tmp_path)
    DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=_build_state(),
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    # No init-time event log of skill/mode — those are agent config, not turn events.
    for kind, _kw in recorder.events:
        assert "VIBEMIX_SKILL_LEVEL" not in kind
        assert "VIBEMIX_MODE" not in kind


# ---------- ensure module-level VIBEMIX_* env reads are isolated ----------


def test_dispatch_10_re_reading_env_per_instantiation(mocker, tmp_path, monkeypatch):
    """Each DJCoHostAgent() instantiation re-reads env vars (no caching)."""
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "pro")
    monkeypatch.setenv("VIBEMIX_MODE", "hype")
    inst1 = _instructions_kw_for_env(mocker, tmp_path)
    assert inst1 == HYPE_PRO

    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "beginner")
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    inst2 = _instructions_kw_for_env(mocker, tmp_path)
    assert inst2 == _coach_rendered(COACH_BEGINNER)
