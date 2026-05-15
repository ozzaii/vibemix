# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent profile= kwarg tests — Phase 32-03 / PROFILE-04 + P53.

Verifies:
- profile= is accepted as a kwargs-only argument (the `*` separator gate).
- profile= None is byte-identical to omitting the argument (P53 backward compat).
- profile is stored as self._profile but NEVER referenced inside llm_node
  (AST gate — duplicated from tests/profile/test_profile_not_in_per_turn_prompt
  but exercised here at the constructor seam).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.state import MusicState

DJ_COHOST_PATH = Path(__file__).resolve().parents[2] / "src" / "vibemix" / "agent" / "dj_cohost.py"


class _FakeRecorder:
    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:  # pragma: no cover
        pass


def _build_state() -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.phase = "peak"
    s.bpm = 128.0
    return s


def _kwargs(mocker, tmp_path: Path) -> dict[str, Any]:
    return {
        "genai_client": mocker.MagicMock(),
        "clean_audio_buf": mocker.MagicMock(),
        "screen_buf": mocker.MagicMock(),
        "state": _build_state(),
        "recorder": _FakeRecorder(tmp_path),
        "llm_inst": mocker.MagicMock(),
        "tts_inst": mocker.MagicMock(),
    }


def _valid_profile() -> dict:
    return {
        "preferred_genre": "techno",
        "avg_session_duration": 60.0,
        "mix_style_tags": ["long_blends"],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {
            "TRACK_CHANGE": "sometimes",
            "PHASE": "sometimes",
            "KAAN_SPOKE": "rarely",
            "MIX_MOVE": "sometimes",
            "DISTORTION_CLIMB": "never",
            "ACID_LINE_ENTRY": "never",
            "HEARTBEAT": "rarely",
            "LAYER_ARRIVAL": "sometimes",
        },
    }


# ---------------------------------------------------------------------------
# Accept kwarg + storage
# ---------------------------------------------------------------------------


def test_djcohost_accepts_profile_kwarg(mocker, tmp_path: Path) -> None:
    mocker.patch.object(Agent, "__init__", return_value=None)
    profile = _valid_profile()
    agent = DJCoHostAgent(**_kwargs(mocker, tmp_path), profile=profile)
    assert agent._profile is profile


def test_djcohost_profile_default_none(mocker, tmp_path: Path) -> None:
    """No explicit profile kwarg → self._profile is None."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    agent = DJCoHostAgent(**_kwargs(mocker, tmp_path))
    assert agent._profile is None


def test_djcohost_explicit_profile_none(mocker, tmp_path: Path) -> None:
    """profile=None is identical to omitting the kwarg."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    agent_omitted = DJCoHostAgent(**_kwargs(mocker, tmp_path))
    mocker.patch.object(Agent, "__init__", return_value=None)
    agent_explicit = DJCoHostAgent(**_kwargs(mocker, tmp_path), profile=None)
    assert agent_omitted._profile is agent_explicit._profile is None


# ---------------------------------------------------------------------------
# Byte-identical v2.0 4-kwarg path (P53)
# ---------------------------------------------------------------------------


def test_djcohost_kwargs_only_byte_identical_path(mocker, tmp_path: Path) -> None:
    """P53: v2.0-shaped construction without `profile=` produces an agent
    whose visible per-turn state (gen_cfg.system_instruction, pending_event,
    history deque, history maxlen) is identical to a profile=None construction.

    This is the regression gate that catches the "5th kwarg breaks 4-kwarg
    path" failure mode from Pitfall P53.
    """
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    mocker.patch.object(Agent, "__init__", return_value=None)
    v2_agent = DJCoHostAgent(**_kwargs(mocker, tmp_path))

    mocker.patch.object(Agent, "__init__", return_value=None)
    p32_agent = DJCoHostAgent(**_kwargs(mocker, tmp_path), profile=None)

    # System instruction identical (cache + per-turn path both unaffected).
    assert v2_agent._gen_cfg.system_instruction == p32_agent._gen_cfg.system_instruction
    assert v2_agent._gen_cfg.system_instruction.startswith(SYSTEM_INSTRUCTION)
    # Pending event default identical.
    assert v2_agent._pending_event == p32_agent._pending_event is None
    # History deque identical: maxlen 10, empty.
    assert v2_agent._ai_text_history.maxlen == p32_agent._ai_text_history.maxlen == 10
    assert len(v2_agent._ai_text_history) == len(p32_agent._ai_text_history) == 0
    # Profile state identical.
    assert v2_agent._profile is p32_agent._profile is None


def test_djcohost_profile_does_not_affect_gen_cfg(mocker, tmp_path: Path) -> None:
    """Even with a profile attached, the per-turn gen_cfg.system_instruction
    must NOT contain profile content (P60 — profile lives in the cache only)."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    agent = DJCoHostAgent(**_kwargs(mocker, tmp_path), profile=_valid_profile())
    instruction = agent._gen_cfg.system_instruction
    # Profile-specific markers from cache_render must NOT appear.
    assert "preferred_genre" not in instruction.lower()
    assert "mix_style_tags" not in instruction.lower()
    assert "tempo_preference_bin" not in instruction.lower()


# ---------------------------------------------------------------------------
# Kwargs-only enforcement (the `*` separator)
# ---------------------------------------------------------------------------


def test_djcohost_profile_kwargs_only_rejects_positional(mocker, tmp_path: Path) -> None:
    """Passing `profile` positionally must raise TypeError because of the
    `*` separator in the constructor signature (P53)."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    with pytest.raises(TypeError):
        # Positional args would shift everything — but actually since ALL args
        # are after `*`, even one positional should fail. Try a single positional
        # value (the profile dict itself) — the constructor should reject it.
        DJCoHostAgent(_valid_profile())  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AST gate (P60 enforcement at the constructor seam)
# ---------------------------------------------------------------------------


def test_profile_only_referenced_in_init(mocker, tmp_path: Path) -> None:
    """`_profile` attribute is set ONLY in __init__ — never read inside
    llm_node or any other per-turn method. This duplicates the gate in
    tests/profile/test_profile_not_in_per_turn_prompt.py but at the
    constructor seam (catches a regression of "_profile" appearing in
    llm_node specifically)."""
    src = DJ_COHOST_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    init_refs = 0
    other_method_refs = 0
    for klass in ast.walk(tree):
        if isinstance(klass, ast.ClassDef) and klass.name == "DJCoHostAgent":
            for node in klass.body:
                if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    body_src = ast.unparse(node)
                    count = body_src.count("self._profile")
                    if node.name == "__init__":
                        init_refs += count
                    else:
                        other_method_refs += count
    assert init_refs >= 1, "expected at least one self._profile assignment in __init__"
    assert other_method_refs == 0, (
        f"P60 violation: self._profile is read in {other_method_refs} "
        f"non-__init__ method(s). Profile MUST live in the cache, not per-turn."
    )
