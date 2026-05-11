# SPDX-License-Identifier: Apache-2.0
"""DJ-COHOST-SILENCE — <silence/> short-circuit + slop_suppressed filter.

When the LLM stream contains the literal token ``<silence/>`` (typically as
the only content), the cascade MUST:

1. Suppress all yielded chunks (no TTS turn).
2. Log a ``silence_short_circuit`` event to the recorder.
3. Skip the ``ai_text`` log (the response wasn't a real reaction).
4. NOT add the response to the anti-history deque.

When the post-hoc ``filter_for_slop`` matches a banned phrase in the final
accumulated text, the cascade MUST:

1. Suppress all yielded chunks.
2. Log a ``slop_suppressed`` event with the matched phrases.
3. Skip the ``ai_text`` log.
4. NOT add the response to the anti-history deque.

Clean text passes through unchanged (no extra suppression event logged).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.state import AICoach, Event, MusicState

# ---------- shared minimal stubs (mirror tests/agent/test_dj_cohost.py) ----


def _async_iter(chunks: list[str]):
    async def gen():
        for c in chunks:
            yield type("Chunk", (), {"text": c})()

    return gen()


class _FakeRecorder:
    def __init__(self, session_dir: Path) -> None:
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


def _build_agent(mocker, tmp_path: Path):
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


# ---------- <silence/> short-circuit -------------------------------------


def test_silence_01_silence_token_only_suppresses_tts(mocker, tmp_path) -> None:
    """LLM emits exactly '<silence/>' → no chunks yielded to TTS path."""
    agent, gen_client, _recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/>"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)
    assert chunks == [], f"silence not suppressed: {chunks!r}"


def test_silence_02_silence_logged_as_event(mocker, tmp_path) -> None:
    """LLM emits '<silence/>' → recorder.log_event('silence_short_circuit', ...)
    fires (so coach scorecard can ignore it as a non-slop signal)."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/>"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    kinds = [k for k, _ in recorder.events]
    assert "silence_short_circuit" in kinds
    # Should NOT log ai_text (it wasn't a real reaction)
    assert "ai_text" not in kinds


def test_silence_03_silence_does_not_pollute_history(mocker, tmp_path) -> None:
    """LLM emits '<silence/>' → not added to _ai_text_history (deque stays empty)."""
    agent, gen_client, _recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/>"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)
    assert len(agent._ai_text_history) == 0


def test_silence_04_silence_with_whitespace_padding(mocker, tmp_path) -> None:
    """'  <silence/>  ' — surrounding whitespace still triggers suppression."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["  <silence/>  "]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)
    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "silence_short_circuit" in kinds


def test_silence_05_silence_meta_records_no_response(mocker, tmp_path) -> None:
    """Even on silence, the per-invocation meta.json still gets written."""
    agent, gen_client, _recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/>"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    invoke_dirs = list((tmp_path / "invocations").iterdir())
    assert len(invoke_dirs) == 1
    meta = json.loads((invoke_dirs[0] / "meta.json").read_text())
    # response_chars reflects what the model literally emitted (the silence token)
    assert meta["response_chars"] == len("<silence/>")


# ---------- slop filter -----------------------------------------------------


def test_slop_01_banned_phrase_suppresses_tts(mocker, tmp_path) -> None:
    """LLM emits 'Amazing mix!' → filter_for_slop catches 'amazing' → no chunks."""
    agent, gen_client, _recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Amazing mix!"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)
    assert chunks == [], f"slop not suppressed: {chunks!r}"


def test_slop_02_banned_phrase_logs_slop_event_with_matches(mocker, tmp_path) -> None:
    """LLM emits banned phrase → recorder logs slop_suppressed with matches list."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Amazing work!"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    kinds = [k for k, _ in recorder.events]
    assert "slop_suppressed" in kinds
    slop_kw = recorder.events[kinds.index("slop_suppressed")][1]
    assert "matches" in slop_kw
    assert any("amazing" in m.lower() for m in slop_kw["matches"])
    # ai_text NOT logged (suppressed turn)
    assert "ai_text" not in kinds


def test_slop_03_clean_text_passes_through(mocker, tmp_path) -> None:
    """Clean DJ-friend text → no slop_suppressed event, normal ai_text flow."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["that 303 squelch hit hard"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)
    assert chunks == ["that 303 squelch hit hard"]

    kinds = [k for k, _ in recorder.events]
    assert "slop_suppressed" not in kinds
    assert "silence_short_circuit" not in kinds
    assert "ai_text" in kinds


def test_slop_04_slop_does_not_pollute_history(mocker, tmp_path) -> None:
    """Slop-suppressed reply not appended to _ai_text_history."""
    agent, gen_client, _recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Awesome drop!"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)
    assert len(agent._ai_text_history) == 0


# ---------- streaming chunk delivery semantics -----------------------------


def test_silence_06_streaming_chunks_buffered_then_dropped(mocker, tmp_path) -> None:
    """LLM streams '<sil' + 'ence/>' across two chunks — accumulated text is
    '<silence/>' which short-circuits. Cascade must NOT yield either partial."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<sil", "ence/>"]),
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)
    assert chunks == [], f"partial silence emitted: {chunks!r}"
    kinds = [k for k, _ in recorder.events]
    assert "silence_short_circuit" in kinds
