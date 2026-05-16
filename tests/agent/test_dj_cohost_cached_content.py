# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent — Plan 19-03 cached_content wiring.

Pins:
  - Constructor accepts optional ``cache: GeminiContextCache | None = None``
  - llm_node passes cached_content into types.GenerateContentConfig when warm
  - llm_node falls back to self._gen_cfg (system_instruction path) when cold
    OR when cache is None (disabled)
  - recorder.log_event("llm_invoke") payload gains ``cache_state`` field
  - DJCoHostAgent.invalidate_cache() chokepoint wraps cache.invalidate()

Mocks the genai client end-to-end — no real network calls. Mirrors the
fixture pattern from tests/agent/test_dj_cohost.py (parent Agent.__init__
mocked, _FakeRecorder, _drive_llm_node helper).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.agent.cache import GeminiContextCache
from vibemix.state import AICoach, Event, MusicState

# ---------- helpers (mirror test_dj_cohost.py conventions) ----------


def _async_iter(chunks):
    async def gen():
        for c in chunks:
            yield type("Chunk", (), {"text": c})()

    return gen()


class _FakeRecorder:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
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


def _build_agent(
    mocker, tmp_path: Path, *, cache: GeminiContextCache | None = None
) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    screen_buf = mocker.MagicMock()
    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=screen_buf,
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
        cache=cache,
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


# ---------- Constructor ----------


def test_constructor_accepts_cache_kwarg(mocker, tmp_path) -> None:
    """DJCoHostAgent(..., cache=GeminiContextCache(...)) accepted; self._cache == cache."""
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    agent, _, _, _ = _build_agent(mocker, tmp_path, cache=fake_cache)
    assert agent._cache is fake_cache


def test_constructor_default_cache_none(mocker, tmp_path) -> None:
    """No cache kwarg → self._cache is None (preserves Phase 4 backward compat)."""
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
    assert agent._cache is None


# ---------- llm_node — warm cache path ----------


def test_llm_node_warm_cache_passes_cached_content(mocker, tmp_path) -> None:
    """When cache.current_name() returns a string, llm_node builds a per-call
    gen_cfg with cached_content=<name> and OMITS system_instruction (Gemini
    rejects passing both)."""
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    fake_cache.current_name.return_value = "cachedContents/X"
    agent, gen_client, _, state = _build_agent(mocker, tmp_path, cache=fake_cache)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    cfg = gen_client.aio.models.generate_content_stream.call_args.kwargs["config"]
    assert cfg.cached_content == "cachedContents/X"
    # system_instruction is None or NOT_GIVEN — both forms acceptable; the
    # contract is "not set to a real string body".
    assert not cfg.system_instruction or cfg.system_instruction is None or str(
        cfg.system_instruction
    ) in {"None", ""}


def test_llm_node_warm_cache_preserves_thinking_temp_max_tokens(mocker, tmp_path) -> None:
    """Warm-path per-call gen_cfg preserves thinking_config + temperature +
    max_output_tokens from the constructor's _gen_cfg."""
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    fake_cache.current_name.return_value = "cachedContents/X"
    agent, gen_client, _, state = _build_agent(mocker, tmp_path, cache=fake_cache)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    cfg = gen_client.aio.models.generate_content_stream.call_args.kwargs["config"]
    assert cfg.temperature == 1.0
    assert cfg.max_output_tokens == 220
    level = cfg.thinking_config.thinking_level
    assert str(getattr(level, "value", level)).lower() == "minimal"


# ---------- llm_node — cold cache path (warm-up window OR post-invalidate) ----------


def test_llm_node_cold_cache_falls_back_to_system_instruction(mocker, tmp_path) -> None:
    """When cache is non-None BUT current_name() returns None, llm_node
    falls back to self._gen_cfg — system_instruction is the v4 prompt body,
    cached_content is unset."""
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    fake_cache.current_name.return_value = None
    agent, gen_client, _, state = _build_agent(mocker, tmp_path, cache=fake_cache)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    cfg = gen_client.aio.models.generate_content_stream.call_args.kwargs["config"]
    # The fallback IS self._gen_cfg — system_instruction set to the v4 body.
    assert cfg.system_instruction is not None
    assert len(cfg.system_instruction) > 100  # the actual prompt body
    # cached_content NOT set — None or NOT_GIVEN.
    assert not cfg.cached_content


# ---------- llm_node — disabled cache (None at construction) ----------


def test_llm_node_disabled_cache_uses_self_gen_cfg(mocker, tmp_path) -> None:
    """When cache is None at construction, llm_node uses self._gen_cfg
    identically to the Phase 4 backward-compat path."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path, cache=None)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    cfg = gen_client.aio.models.generate_content_stream.call_args.kwargs["config"]
    # Identical to Phase 4: self._gen_cfg passed by reference.
    assert cfg is agent._gen_cfg
    assert cfg.system_instruction is not None


# ---------- llm_invoke payload ----------


def test_log_event_payload_contains_cache_state_warm(mocker, tmp_path) -> None:
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    fake_cache.current_name.return_value = "cachedContents/X"
    agent, gen_client, recorder, state = _build_agent(
        mocker, tmp_path, cache=fake_cache
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    invoke = next(e for e in recorder.events if e[0] == "llm_invoke")
    assert invoke[1]["cache_state"] == "warm"


def test_log_event_payload_contains_cache_state_cold(mocker, tmp_path) -> None:
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    fake_cache.current_name.return_value = None
    agent, gen_client, recorder, state = _build_agent(
        mocker, tmp_path, cache=fake_cache
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    invoke = next(e for e in recorder.events if e[0] == "llm_invoke")
    assert invoke[1]["cache_state"] == "cold"


def test_log_event_payload_contains_cache_state_disabled(mocker, tmp_path) -> None:
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path, cache=None)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    invoke = next(e for e in recorder.events if e[0] == "llm_invoke")
    assert invoke[1]["cache_state"] == "disabled"


# ---------- invalidate_cache() chokepoint ----------


def test_invalidate_cache_calls_cache_invalidate(mocker, tmp_path) -> None:
    """agent.invalidate_cache() awaits cache.invalidate() exactly once."""
    fake_cache = mocker.MagicMock(spec=GeminiContextCache)
    fake_cache.invalidate = AsyncMock()
    agent, _, _, _ = _build_agent(mocker, tmp_path, cache=fake_cache)
    asyncio.run(agent.invalidate_cache())
    fake_cache.invalidate.assert_awaited_once()


def test_invalidate_cache_no_op_when_disabled(mocker, tmp_path) -> None:
    """agent.invalidate_cache() with cache=None completes cleanly (no error)."""
    agent, _, _, _ = _build_agent(mocker, tmp_path, cache=None)
    # Must not raise.
    asyncio.run(agent.invalidate_cache())
