# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent — AGENT-01..04 + LLM-NODE-01..11 + PKG-03.

Pins the multimodal llm_node hijack as a v4-verbatim port: pending event
flow, AICoach prompt construction, per-invocation dump folder, anti-history
clause, deque maxlen + 140-char truncation, recorder log events, exception
handling.
"""

from __future__ import annotations

import asyncio
import collections
import json
from pathlib import Path
from typing import Any

import numpy as np
from google.genai import types
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.agent.dj_cohost import (
    _build_attached_audio_context_clause,
    _build_recall_query_context,
)
from vibemix.audio import INPUT_SR_TARGET, AudioBuffer
from vibemix.prompts.matrix import AUDIO_VIBE_CONTRACT_BLOCK, TTS_TAGS
from vibemix.state import AICoach, Event, MusicState
from vibemix.state.deck_state import DeckState, DeckTrack

# ---------- helpers ----------


def _async_iter(chunks):
    """Build an async iterable yielding objects with a .text attribute."""

    async def gen():
        for c in chunks:
            yield type("Chunk", (), {"text": c})()

    return gen()


def _async_iter_raise(exc):
    """Async iterable that raises immediately."""

    async def gen():
        raise exc
        yield  # pragma: no cover

    return gen()


def _async_iter_after(callback, chunks):
    """Build an async iterable that mutates state after prompt construction."""

    async def gen():
        callback()
        for c in chunks:
            yield type("Chunk", (), {"text": c})()

    return gen()


class _FakeRecorder:
    """Minimal recorder stub — no 0o700 dir creation, no real wav writers."""

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


def _deck_track(title: str, *, camelot: str = "8A") -> DeckTrack:
    return DeckTrack(
        title=title,
        track_id=title.lower().replace(" ", "-"),
        bpm=128.0,
        camelot=camelot,
        confidence=0.9,
        source="rekordbox_xml",
    )


def _build_agent(
    mocker, tmp_path: Path, **agent_kwargs
) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
    """Construct a DJCoHostAgent with the parent ``Agent.__init__`` mocked
    and a fake recorder pointing at tmp_path."""
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
        **agent_kwargs,
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    """Run llm_node to completion and return the list of yielded chunks."""

    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


# ---------- AGENT-01..04 ----------


def test_agent_01_subclass_of_livekit_agent() -> None:
    """AGENT-01: DJCoHostAgent is a subclass of livekit.agents.Agent."""
    assert issubclass(DJCoHostAgent, Agent)


def test_agent_02_super_init_kwargs(mocker, tmp_path) -> None:
    """AGENT-02: super().__init__ called with instructions, llm, tts,
    allow_interruptions=False.

    Plan 18-03: ``instructions`` now includes the citation-grammar block
    appended after the v4 body — assert the v4 body is the prefix and the
    grammar block's signature substring is present.
    """
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    llm = mocker.MagicMock()
    tts = mocker.MagicMock()
    DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=llm,
        tts_inst=tts,
    )
    kw = Agent.__init__.call_args.kwargs
    assert kw["instructions"].startswith(SYSTEM_INSTRUCTION)
    assert "[ev:" in kw["instructions"]  # Plan 18-03 grammar block present
    assert kw["llm"] is llm
    assert kw["tts"] is tts
    assert kw["allow_interruptions"] is False


def test_agent_03_initial_state(mocker, tmp_path) -> None:
    """AGENT-03: pending event None, history empty deque maxlen 10, gen cfg.

    Plan 18-03: ``_gen_cfg.system_instruction`` includes the citation-grammar
    block appended after the v4 body.
    """
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    agent, _, _, _ = _build_agent(mocker, tmp_path)
    assert agent._pending_event is None
    assert isinstance(agent._ai_text_history, collections.deque)
    assert len(agent._ai_text_history) == 0
    assert agent._ai_text_history.maxlen == 10

    assert isinstance(agent._gen_cfg, types.GenerateContentConfig)
    # GenerateContentConfig is a pydantic model — direct field access works
    assert agent._gen_cfg.system_instruction.startswith(SYSTEM_INSTRUCTION)
    assert "[ev:" in agent._gen_cfg.system_instruction
    assert AUDIO_VIBE_CONTRACT_BLOCK in agent._gen_cfg.system_instruction
    for tag in TTS_TAGS:
        assert tag not in agent._gen_cfg.system_instruction
    assert agent._gen_cfg.temperature == 1.0
    assert agent._gen_cfg.max_output_tokens == 1024
    level = agent._gen_cfg.thinking_config.thinking_level
    assert str(getattr(level, "value", level)).lower() == "minimal"


def test_agent_04_set_next_event(mocker, tmp_path) -> None:
    """AGENT-04: set_next_event(ev) mutates _pending_event."""
    agent, _, _, state = _build_agent(mocker, tmp_path)
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    assert agent._pending_event is ev


# ---------- LLM-NODE-01..11 ----------


def test_llm_node_01_yields_chunks_in_order(mocker, tmp_path) -> None:
    """LLM-NODE-01: yields each non-empty text chunk in order.

    Plan 18-03: build_prompt is now called with kwarg
    ``registry_snapshot=None`` when no registry is wired (the agent's
    default state in this test). Assert positional ev + kwarg explicitly.

    Plan 19-02: build_prompt also receives a ``diet=True/False`` kwarg —
    HEARTBEAT is ack-eligible so diet=True. Asserted explicitly so a future
    diet-dispatch regression is caught here too.
    """
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: rms=0.05")

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["hello ", "world"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)

    chunks = _drive_llm_node(agent)
    assert chunks == ["hello ", "world"]
    AICoach.build_prompt.assert_called_once_with(ev, registry_snapshot=None, diet=True)
    # pending event was consumed
    assert agent._pending_event is None


def test_llm_node_02_fallback_to_manual_when_no_event(mocker, tmp_path) -> None:
    """LLM-NODE-02: when _pending_event is None, falls back to MANUAL Event."""
    agent, gen_client, _, _state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    _drive_llm_node(agent)

    AICoach.build_prompt.assert_called_once()
    called_with = AICoach.build_prompt.call_args.args[0]
    assert isinstance(called_with, Event)
    assert called_with.type == "MANUAL"
    assert called_with.state is agent._state
    assert called_with.extra == {}


def test_llm_node_logs_ai_message_observability_with_moves(mocker, tmp_path) -> None:
    """A spoken live-coach response gets one durable ai_message row with moves."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    state.recent_moves = [(0.3, "A_low: flat->cut")]
    state.deck_a = {"vol": 127, "eq_low": 20, "filter": 64, "play": True}
    state.deck_b = {"vol": 0, "eq_low": 64, "filter": 64, "play": False}
    state.xfader = 10
    state.controller_connected = True
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["that low cut reads clearly"])
    )

    ev = Event(type="MIX_MOVE", state=state, extra={"moves": [(0.2, "A_low: flat->cut")]})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    rows = [fields for kind, fields in recorder.events if kind == "ai_message"]
    assert len(rows) == 1
    row = rows[0]
    assert row["engine"] == "live_coach"
    assert row["event"] == "MIX_MOVE"
    assert row["message"] == "that low cut reads clearly"
    assert row["moves"]["recent_moves"] == [{"label": "A_low: flat->cut", "age_s": 0.3}]
    assert row["moves"]["event_moves"] == [{"label": "A_low: flat->cut", "age_s": 0.2}]
    assert row["moves"]["deck_mixer"]["A"]["eq_low"] == 20
    prompt_text = Path(row["artifacts"]["session_prompt_path"]).read_text(encoding="utf-8")
    assert prompt_text.startswith("EVIDENCE: x")
    assert "AUDIO CONTEXT MAP FOR ATTACHED P1" in prompt_text
    assert (
        Path(row["artifacts"]["session_response_path"]).read_text(encoding="utf-8")
        == "that low cut reads clearly"
    )


def test_llm_node_strips_emote_tags_and_sets_mascot_intent(mocker, tmp_path) -> None:
    """Inline emote controls must drive the mascot, not leak into spoken text."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Nice [emote:fist_pump]drop."])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)

    assert "".join(chunks) == "Nice drop."
    assert state.last_reaction_intent == "fist_pump"
    assert state.last_reaction_intent_seq == 1
    ai_texts = [fields["text"] for kind, fields in recorder.events if kind == "ai_text"]
    assert ai_texts == ["Nice drop."]
    intent_rows = [fields for kind, fields in recorder.events if kind == "mascot_reaction_intent"]
    assert len(intent_rows) == 1
    assert intent_rows[0]["intent"] == "fist_pump"
    assert intent_rows[0]["seq"] == 1
    assert isinstance(intent_rows[0]["response_id"], str)


def test_llm_node_strips_unknown_emote_tags_without_mascot_intent(mocker, tmp_path) -> None:
    """Unknown emote controls are removed from speech but do not fire the mascot."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Nice [emote:wink]drop."])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)

    assert "".join(chunks) == "Nice drop."
    assert state.last_reaction_intent is None
    assert state.last_reaction_intent_seq == 0
    ai_texts = [fields["text"] for kind, fields in recorder.events if kind == "ai_text"]
    assert ai_texts == ["Nice drop."]
    assert "mascot_reaction_intent" not in [kind for kind, _fields in recorder.events]


def test_llm_node_strips_legacy_voice_tags_from_speech_and_ai_message(mocker, tmp_path) -> None:
    """Legacy Gemini-TTS tags are internal controls, not user-visible speech."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["[chill] A fast kick sat over the low end."])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)

    assert "".join(chunks) == "A fast kick sat over the low end."
    assert state.last_reaction_intent is None
    ai_texts = [fields["text"] for kind, fields in recorder.events if kind == "ai_text"]
    assert ai_texts == ["A fast kick sat over the low end."]
    rows = [fields for kind, fields in recorder.events if kind == "ai_message"]
    assert len(rows) == 1
    assert rows[0]["message"] == "A fast kick sat over the low end."
    assert rows[0]["extra"]["spoken_response_chars"] == len("A fast kick sat over the low end.")
    assert "[chill]" not in rows[0]["message"]
    assert "mascot_reaction_intent" not in [kind for kind, _fields in recorder.events]


def test_llm_node_suppresses_non_english_spoken_text_but_keeps_raw_artifact(
    mocker, tmp_path
) -> None:
    """Prompt-only English is not enough: runtime blocks non-English speech."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    raw_response = "Süper drop abi, çok iyi."
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter([raw_response])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)

    assert chunks == []
    assert "ai_text" not in [kind for kind, _fields in recorder.events]
    suppression_rows = [
        fields for kind, fields in recorder.events if kind == "non_english_suppressed"
    ]
    assert len(suppression_rows) == 1
    assert "phrase:çok iyi" in suppression_rows[0]["matches"]
    rows = [fields for kind, fields in recorder.events if kind == "ai_message"]
    assert len(rows) == 1
    row = rows[0]
    assert row["message"] == ""
    assert row["message_chars"] == 0
    assert row["suppression"] == "non_english"
    assert row["stop_reason"] == "non_english"
    assert "phrase:çok iyi" in row["extra"]["language_matches"]
    assert row["extra"]["spoken_response_chars"] == 0
    assert (
        Path(row["artifacts"]["session_response_path"]).read_text(encoding="utf-8") == raw_response
    )


def test_llm_node_english_only_guard_preserves_grounded_english_response(mocker, tmp_path) -> None:
    """English with citations keeps raw receipts but not audience-facing text."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    response = "That low end is moving [aud:rms@12.0]."
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter([response])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive_llm_node(agent)

    assert "".join(chunks) == "That low end is moving."
    ai_texts = [fields["text"] for kind, fields in recorder.events if kind == "ai_text"]
    assert ai_texts == ["That low end is moving."]
    rows = [fields for kind, fields in recorder.events if kind == "ai_message"]
    assert len(rows) == 1
    assert rows[0]["message"] == "That low end is moving."
    assert (
        Path(rows[0]["artifacts"]["session_response_path"]).read_text(encoding="utf-8") == response
    )
    assert rows[0]["suppression"] is None
    assert rows[0]["extra"]["language_matches"] == []
    assert rows[0]["extra"]["spoken_response_chars"] == len("That low end is moving.")


def test_llm_node_ai_message_uses_prompt_time_mixer_snapshot(mocker, tmp_path) -> None:
    """Model latency must not rewrite the saved mixer evidence for the turn."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    state.recent_moves = [(0.3, "A_low: flat->cut")]
    state.deck_a = {"vol": 127, "eq_low": 20, "filter": 64, "play": True}
    state.deck_b = {"vol": 0, "eq_low": 64, "filter": 64, "play": False}
    state.xfader = 10
    state.controller_connected = True
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    def mutate_live_state() -> None:
        state.recent_moves = []
        state.deck_a = {"vol": 0, "eq_low": 99, "filter": 64, "play": False}
        state.xfader = 127

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter_after(mutate_live_state, ["still saw the original low cut"])
    )

    ev = Event(type="MIX_MOVE", state=state, extra={"moves": [(0.2, "A_low: flat->cut")]})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    rows = [fields for kind, fields in recorder.events if kind == "ai_message"]
    assert len(rows) == 1
    row = rows[0]
    assert row["moves"]["recent_moves"] == [{"label": "A_low: flat->cut", "age_s": 0.3}]
    assert row["moves"]["deck_mixer"]["A"]["eq_low"] == 20
    assert row["moves"]["deck_mixer"]["A"]["vol"] == 127
    assert row["moves"]["deck_mixer"]["xfader"] == 10


def test_llm_node_03_screen_jpeg_none_unconditional(mocker, tmp_path) -> None:
    """LLM-NODE-03: screen_jpeg=None unconditionally; v4:1502 comment present."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # Even if screen_buf would return a real image, llm_node should set None.
    agent._screen_buf.latest.return_value = (b"REAL_JPEG", (1920, 1080))
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    # 2 entries — text + audio Part. NO image Part.
    assert len(contents) == 2

    # Source file contains the literal v4:1502 anti-hallucination comment
    src = Path("src/vibemix/agent/dj_cohost.py").read_text()
    assert "# Single-modality: audio only. Screen + MIDI metadata caused hallucination." in src


def test_llm_node_03a_fences_cold_p1_audio_with_claim_policy(mocker, tmp_path) -> None:
    """Even a cold deck state gets an audio map beside P1, not an empty suffix."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    state.audible = False
    state.audible_deck = "none"
    state.audible_track = ""
    state.audible_track_confidence = 0.0
    state.controller_connected = False
    state.deck_state = DeckState()
    state.recent_moves = []
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: cold")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    prompt_text = contents[0]
    audio_map_at = prompt_text.index("AUDIO CONTEXT MAP FOR ATTACHED P1")
    attached_at = prompt_text.index("Attached: P1")

    assert audio_map_at < attached_at
    assert "context_feed_contract[" in prompt_text
    assert "surface=gemini_p1" in prompt_text
    assert "history=past_comparison_not_live_proof" in prompt_text
    assert "cache=static_persona_rules_only" in prompt_text
    assert "per_turn=small_text+single_P1_audio" in prompt_text
    assert "speed=no_extra_model_pass" in prompt_text
    assert "audio_part_context[" in prompt_text
    assert "surface=gemini_parts" in prompt_text
    assert "P1=live_global_mix" in prompt_text
    assert "P1_model_heard=true" in prompt_text
    assert "P1_runtime_observed=true" in prompt_text
    assert "P1_deck_audio=global_mix_not_stems" in prompt_text
    assert "per_deck_audio=not_attached" in prompt_text
    assert "rule=part_labels_not_outcome_verdict" in prompt_text
    assert "deck_audio_separation_context[" in prompt_text
    assert "deckA_audio=not_captured" in prompt_text
    assert "deckB_audio=not_captured" in prompt_text
    assert "current_capture=P1_global_mix" in prompt_text
    assert "audio_window_context[" in prompt_text
    assert "audio_window_map[" in prompt_text
    assert "P1=master_global_mix" in prompt_text
    assert "move_anchor=none" in prompt_text
    assert "deckA_audio=not_attached" in prompt_text
    assert "deckB_audio=not_attached" in prompt_text
    assert "lane_aliases=deck1:A,deck2:B" in prompt_text


def test_llm_node_audio_map_reflects_configured_deck_pair_capture(mocker, tmp_path) -> None:
    audio_capture_context = {
        "requested_device": "BlackHole 16ch",
        "device_name": "BlackHole 16ch",
        "input_channels": 16,
        "opened_channels": 4,
        "sample_rate": 48000,
        "master_channels": "0,1,2,3",
        "deck_channels": {"A": "0,1", "B": "2,3"},
        "deck_audio_capture_enabled": True,
    }
    agent, gen_client, _, state = _build_agent(
        mocker,
        tmp_path,
        audio_capture_context=audio_capture_context,
    )
    audio_capture_context["deck_audio_rms"] = {"A": 0.02, "B": 0.0}
    audio_capture_context["deck_audio_features"] = {
        "A": {"activity": "active", "rms": 0.02, "peak": 0.1, "zcr": 0.03},
        "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
    }
    audio_capture_context["deck_audio_deltas"] = {
        "A": ["rms_rose_100pct_strong"],
        "B": ["rms_fell_50pct_strong"],
    }
    audio_capture_context["deck_audio_windows"] = {
        "pre_s": [-6.0, -1.0],
        "current_s": [-1.0, 0.0],
        "A": {
            "pre": {"activity": "active", "rms": 0.02, "peak": 0.1, "flux": 0.004},
            "current": {"activity": "active", "rms": 0.04, "peak": 0.12, "flux": 0.009},
            "delta": ["rms_rose_100pct_strong"],
        },
        "B": {
            "pre": {"activity": "active", "rms": 0.03, "peak": 0.11, "flux": 0.006},
            "current": {"activity": "silent", "rms": 0.0, "peak": 0.0, "flux": 0.001},
            "delta": ["rms_fell_50pct_strong"],
        },
    }
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: multichannel")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    _drive_llm_node(agent)

    assert AICoach.build_prompt.call_args.kwargs["audio_capture_context"] is audio_capture_context
    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    prompt_text = contents[0]
    assert "deck_audio_separation_context[" in prompt_text
    assert "mode=deck_pair_capture_configured" in prompt_text
    assert "deckA_audio=captured" in prompt_text
    assert "deckB_audio=captured" in prompt_text
    assert "per_deck_audio=captured_not_attached" in prompt_text
    assert "deck_audio_activity=A_active+B_silent" in prompt_text
    assert "deck_audio_features_context[" in prompt_text
    assert "A_activity=active" in prompt_text
    assert "B_activity=silent" in prompt_text
    assert "deck_audio_delta_context[" in prompt_text
    assert "A_delta=rms_rose_100pct_strong" in prompt_text
    assert "deck_audio_window_context[" in prompt_text
    assert "timeline=pre_action_current" in prompt_text
    assert "A_current=active_rms_0.040" in prompt_text
    assert "deck_audio_capture=A_active+B_silent" in prompt_text
    assert "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000" in prompt_text
    assert "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong" in prompt_text
    assert (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_silent_pre_0.030_current_0.000" in prompt_text
    )
    assert "claim_policy[policy=requires_more_evidence" in prompt_text
    assert "rule=multi_deck_outcome_requires_live_support" in prompt_text
    assert "AUDIO PART CONTRACT: P1=live_global_mix isolated_decks=false" in prompt_text
    assert "deck_audio_parts=not_attached" in prompt_text
    assert "optional_later_parts_not_current_deck_audio" not in prompt_text
    assert "global mix, not isolated deck stems" in prompt_text


def test_llm_node_downgrades_verdict_when_deck_audio_parts_not_attached(mocker, tmp_path) -> None:
    audio_capture_context = {
        "requested_device": "BlackHole 16ch",
        "device_name": "BlackHole 16ch",
        "input_channels": 16,
        "opened_channels": 4,
        "sample_rate": 48000,
        "master_channels": "0,1,2,3",
        "deck_channels": {"A": "0,1", "B": "2,3"},
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.04, "B": 0.04},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.04, "peak": 0.2, "zcr": 0.03},
            "B": {"activity": "active", "rms": 0.04, "peak": 0.18, "zcr": 0.04},
        },
        "deck_audio_deltas": {
            "A": ["rms_rose_60pct_strong"],
            "B": ["rms_rose_40pct_strong"],
        },
        "deck_audio_windows": {
            "A": {
                "pre": {"activity": "active", "rms": 0.025, "peak": 0.12},
                "current": {"activity": "active", "rms": 0.04, "peak": 0.2},
                "delta": ["rms_rose_60pct_strong"],
            },
            "B": {
                "pre": {"activity": "active", "rms": 0.028, "peak": 0.13},
                "current": {"activity": "active", "rms": 0.04, "peak": 0.18},
                "delta": ["rms_rose_40pct_strong"],
            },
        },
    }
    agent, gen_client, recorder, state = _build_agent(
        mocker,
        tmp_path,
        audio_capture_context=audio_capture_context,
        deck_audio_parts_mode="auto",
    )
    state.audible_deck = "mix"
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={"A": _deck_track("Deck Left"), "B": _deck_track("Deck Right", camelot="9A")}
    )

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFMASTER")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: no deck parts")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Great transition, that blend was clean."])
    )

    agent.set_next_event(Event(type="MIX_MOVE", state=state, extra={"moves": ["xfader→center"]}))
    chunks = _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    prompt_text = contents[0]
    heard = "".join(chunks)
    guard_events = [fields for kind, fields in recorder.events if kind == "live_claim_guard"]
    assert len(contents) == 2
    assert "claim_policy[policy=candidate_not_verdict" in prompt_text
    assert "reason=deck_audio_parts_not_attached" in prompt_text
    assert "rule=candidate_not_quality_verdict" in prompt_text
    assert "claim_policy[policy=supported_verdict" not in prompt_text
    assert "deck_audio_parts=not_attached" in prompt_text
    assert "Great transition" not in heard
    assert heard == ""
    assert guard_events
    assert guard_events[-1]["action"] == "strip"
    assert guard_events[-1]["reason"] == "deck_audio_parts_not_attached"
    assert "Great transition" in guard_events[-1]["raw_text"]
    assert "Great transition" not in guard_events[-1]["corrected_text"]


def test_llm_node_live_claim_guard_uses_event_audio_capture_context(mocker, tmp_path) -> None:
    audio_capture_context = {
        "deck_channels": {"A": "0,1", "B": "2,3"},
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.04, "B": 0.04},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.04, "peak": 0.2, "zcr": 0.03},
            "B": {"activity": "active", "rms": 0.04, "peak": 0.18, "zcr": 0.04},
        },
        "deck_audio_deltas": {
            "A": ["rms_rose_60pct_strong"],
            "B": ["rms_rose_40pct_strong"],
        },
        "deck_audio_windows": {
            "A": {
                "pre": {"activity": "active", "rms": 0.025, "peak": 0.12},
                "current": {"activity": "active", "rms": 0.04, "peak": 0.2},
                "delta": ["rms_rose_60pct_strong"],
            },
            "B": {
                "pre": {"activity": "active", "rms": 0.028, "peak": 0.13},
                "current": {"activity": "active", "rms": 0.04, "peak": 0.18},
                "delta": ["rms_rose_40pct_strong"],
            },
        },
    }
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    state.audible_deck = "mix"
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={"A": _deck_track("Deck Left"), "B": _deck_track("Deck Right", camelot="9A")}
    )

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFMASTER")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: event capture")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Great transition, that blend was clean."])
    )

    agent.set_next_event(
        Event(
            type="MIX_MOVE",
            state=state,
            extra={"moves": ["xfader→center"], "audio_capture_context": audio_capture_context},
        )
    )
    chunks = _drive_llm_node(agent)

    assert AICoach.build_prompt.call_args.kwargs["audio_capture_context"] is audio_capture_context
    guard_events = [fields for kind, fields in recorder.events if kind == "live_claim_guard"]
    assert "Great transition" not in "".join(chunks)
    assert "".join(chunks) == ""
    assert guard_events
    assert guard_events[-1]["action"] == "strip"
    assert guard_events[-1]["reason"] == "deck_audio_parts_not_attached"


def test_llm_node_attaches_configured_deck_audio_parts_on_mix_move(mocker, tmp_path) -> None:
    deck_a = AudioBuffer(seconds=4.0, sr=INPUT_SR_TARGET)
    deck_b = AudioBuffer(seconds=4.0, sr=INPUT_SR_TARGET)
    samples = int(INPUT_SR_TARGET * 3.0)
    deck_a.push(np.full(samples, 1200, dtype=np.int16))
    deck_b.push(np.full(samples, 900, dtype=np.int16))
    audio_capture_context = {
        "requested_device": "BlackHole 16ch",
        "device_name": "BlackHole 16ch",
        "input_channels": 16,
        "opened_channels": 4,
        "sample_rate": 48000,
        "master_channels": "0,1,2,3",
        "deck_channels": {"A": "0,1", "B": "2,3"},
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.04, "B": 0.04},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.04, "peak": 0.2, "zcr": 0.03},
            "B": {"activity": "active", "rms": 0.04, "peak": 0.18, "zcr": 0.04},
        },
        "deck_audio_deltas": {
            "A": ["rms_rose_60pct_strong"],
            "B": ["rms_rose_40pct_strong"],
        },
        "deck_audio_windows": {
            "A": {
                "pre": {"activity": "active", "rms": 0.025, "peak": 0.12},
                "current": {"activity": "active", "rms": 0.04, "peak": 0.2},
                "delta": ["rms_rose_60pct_strong"],
            },
            "B": {
                "pre": {"activity": "active", "rms": 0.028, "peak": 0.13},
                "current": {"activity": "active", "rms": 0.04, "peak": 0.18},
                "delta": ["rms_rose_40pct_strong"],
            },
        },
    }
    agent, gen_client, recorder, state = _build_agent(
        mocker,
        tmp_path,
        audio_capture_context=audio_capture_context,
        deck_audio_buffers={"A": deck_a, "B": deck_b},
        deck_audio_parts_mode="auto",
        deck_audio_part_seconds=3.0,
    )
    state.audible_deck = "mix"
    state.deck_state = DeckState(
        decks={"A": _deck_track("Deck Left"), "B": _deck_track("Deck Right", camelot="9A")}
    )

    def _pcm_to_wav(pcm, sample_rate, *args, **kwargs):
        peak = int(np.abs(pcm).max()) if pcm.size else 0
        if peak == 1200:
            return b"RIFFDECKA"
        if peak == 900:
            return b"RIFFDECKB"
        return b"RIFFUNKNOWN"

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFMASTER")
    pcm_to_wav = mocker.patch("vibemix.agent.dj_cohost.pcm_to_wav", side_effect=_pcm_to_wav)
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: deck parts")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    agent.set_next_event(Event(type="MIX_MOVE", state=state, extra={"moves": ["xfader→center"]}))
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    prompt_text = contents[0]
    audio_part_line = next(
        line for line in prompt_text.splitlines() if line.startswith("audio_part_context[")
    )
    audio_window_line = next(
        line for line in prompt_text.splitlines() if line.startswith("audio_window_context[")
    )
    audio_window_map_line = next(
        line for line in prompt_text.splitlines() if line.startswith("audio_window_map[")
    )
    assert len(contents) == 4
    assert contents[1].inline_data.data == b"RIFFMASTER"
    assert contents[2].inline_data.data == b"RIFFDECKA"
    assert contents[3].inline_data.data == b"RIFFDECKB"
    assert pcm_to_wav.call_count == 2
    assert "Additional attached deck audio:" in prompt_text
    assert "P2 = captured Deck A audio (active)" in prompt_text
    assert "P3 = captured Deck B audio (active)" in prompt_text
    assert "P1 remains the audience-truth master mix" in prompt_text
    assert "claim_policy[policy=supported_verdict" in prompt_text
    assert "rule=grounded_verdict_allowed" in prompt_text
    assert "deck_audio_parts=attached_configured_deck_pair_refs" in prompt_text
    assert "part_order=P1,P2,P3" in prompt_text
    assert "model_audio_tokens_est=384" in prompt_text
    assert "deckA_audio=P2" in prompt_text
    assert "deckB_audio=P3" in prompt_text
    assert "deckA_activity=active" in prompt_text
    assert "deckB_activity=active" in prompt_text
    assert "deck_parts_rule=reference_not_quality_verdict" in prompt_text
    assert "deck_separation=deck_pair_parts" in prompt_text
    assert "optional_later_parts_not_current_deck_audio" not in prompt_text
    assert "per_deck_audio=deck_pair_parts" in audio_part_line
    assert "duplicate_audio=separate_deck_pair_parts" in audio_part_line
    assert "deckA_part=P2" in audio_part_line
    assert "deckB_part=P3" in audio_part_line
    assert "P2=deckA_configured_capture" in audio_part_line
    assert "P3=deckB_configured_capture" in audio_part_line
    assert "P2_activity=deckA_active" in audio_part_line
    assert "P3_activity=deckB_active" in audio_part_line
    assert "P2_rule=deck_pair_capture_reference_not_quality_verdict" in audio_part_line
    assert "deckA_audio=P2" in audio_window_line
    assert "deckB_audio=P3" in audio_window_line
    assert "per_deck_audio=deck_pair_parts" in audio_window_line
    assert "deck_audio_separation=deck_audio_separation_context" in audio_window_line
    assert "deck_part_span=-3.0..0.0" in audio_window_line
    assert "deckA_activity=active" in audio_window_line
    assert "deckB_activity=active" in audio_window_line
    assert "deckA_audio=P2:-3.0..0.0" in audio_window_map_line
    assert "deckB_audio=P3:-3.0..0.0" in audio_window_map_line
    assert "per_deck_audio=deck_pair_parts" in audio_window_map_line
    assert "duplicate_audio=separate_deck_pair_parts" in audio_window_map_line
    attached = [fields for kind, fields in recorder.events if kind == "deck_audio_parts_attached"]
    assert attached
    assert attached[-1]["event"] == "MIX_MOVE"
    assert attached[-1]["labels"] == "P2+P3"
    invokes = [fields for kind, fields in recorder.events if kind == "llm_invoke"]
    assert invokes[-1]["audio_tokens_est"] == 384
    assert attached[-1]["activity"] == "A:active+B:active"


def test_attached_audio_contract_orders_mic_lookahead_and_deck_parts() -> None:
    state = _build_state()
    state.audible_deck = "mix"
    state.deck_state = DeckState(
        decks={"A": _deck_track("Deck Left"), "B": _deck_track("Deck Right", camelot="9A")}
    )

    prompt = _build_attached_audio_context_clause(
        state,
        ["xfader→center"],
        audio_capture_context={
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.04, "B": 0.04},
            "deck_audio_features": {
                "A": {"activity": "active", "rms": 0.04, "peak": 0.2, "zcr": 0.03},
                "B": {"activity": "active", "rms": 0.04, "peak": 0.18, "zcr": 0.04},
            },
        },
        mic_part_label="P2",
        lookahead_part_label="P3",
        deck_part_labels={"A": "P4", "B": "P5"},
        deck_part_activity={"A": "active", "B": "active"},
    )

    assert "audio_part_context[" in prompt
    assert "part_order=P1,P2,P3,P4,P5" in prompt
    assert "P2=user_mic" in prompt
    assert "P3=source_file_lookahead" in prompt
    assert "deckA_part=P4" in prompt
    assert "deckB_part=P5" in prompt
    assert "deckA_audio=P4" in prompt
    assert "deckB_audio=P5" in prompt
    assert "AUDIO PART CONTRACT: P1=live_global_mix isolated_decks=false" in prompt
    assert "deck_separation=deck_pair_parts" in prompt
    assert "part_order=P1,P2,P3,P4,P5 deck_parts_rule=reference_not_quality_verdict" in prompt
    assert "deck_separation=structured_text_only" not in prompt


def test_attached_audio_contract_falls_back_on_conflicting_deck_part_labels() -> None:
    state = _build_state()
    state.audible_deck = "mix"
    state.deck_state = DeckState(
        decks={"A": _deck_track("Deck Left"), "B": _deck_track("Deck Right", camelot="9A")}
    )

    prompt = _build_attached_audio_context_clause(
        state,
        ["xfader→center"],
        audio_capture_context={
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.04, "B": 0.04},
        },
        mic_part_label="P2",
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "active"},
    )

    assert "audio_part_context[" in prompt
    assert "part_order=P1,P2" in prompt
    assert "deckA_part=" not in prompt
    assert "deckB_part=" not in prompt
    assert "deck_audio_parts=not_attached" in prompt
    assert "deck_separation=structured_text_only" in prompt
    assert "deck_separation=deck_pair_parts" not in prompt


def test_llm_node_03b_places_deck_audio_map_next_to_audio_part(mocker, tmp_path) -> None:
    """Deck/live gates are repeated adjacent to Gemini's P1 audio Part."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    state.controller_connected = True
    state.audible_deck = "A"
    state.deck_a = {
        "vol": 110,
        "eq_low": 0,
        "eq_mid": 64,
        "eq_hi": 64,
        "filter": 64,
        "play": True,
    }
    state.deck_b = {
        "vol": 0,
        "eq_low": 64,
        "eq_mid": 64,
        "eq_hi": 64,
        "filter": 64,
        "play": False,
    }
    state.xfader = 0
    state.deck_state = DeckState(decks={"A": _deck_track("Strobe")})
    state.recent_moves = [(1.5, "A_low: flat→killed")]
    state.audio_delta = ["low energy fell 50% (strong)"]
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: base")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(
        type="MIX_MOVE",
        state=state,
        extra={
            "moves": ["A_low: flat→killed"],
            "audio_capture_context": {
                "deck_channels": {"A": "0,1", "B": "2,3"},
                "deck_audio_capture_enabled": True,
                "deck_audio_rms": {"A": 0.02, "B": 0.0},
                "deck_audio_features": {
                    "A": {"activity": "active", "rms": 0.02, "peak": 0.1, "zcr": 0.03},
                    "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
                },
                "deck_audio_deltas": {
                    "A": ["rms_rose_100pct_strong"],
                    "B": ["rms_fell_50pct_strong"],
                },
            },
        },
    )
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    prompt_text = contents[0]
    audio_map_at = prompt_text.index("AUDIO CONTEXT MAP FOR ATTACHED P1")
    attached_at = prompt_text.index("Attached: P1")

    assert len(contents) == 2
    assert prompt_text.startswith("EVIDENCE: base")
    assert (
        AICoach.build_prompt.call_args.kwargs["audio_capture_context"]
        is ev.extra["audio_capture_context"]
    )
    assert audio_map_at < attached_at
    assert "context_feed_contract[" in prompt_text
    assert "surface=gemini_p1" in prompt_text
    assert "labels=deck1:A,deck2:B" in prompt_text
    assert "volatile=deck_state+deck_mixer+recent_moves+audio_delta+audio_window" in prompt_text
    assert "audio_part_context[" in prompt_text
    assert "surface=gemini_parts" in prompt_text
    assert "P1=live_global_mix" in prompt_text
    assert "P1_model_heard=true" in prompt_text
    assert "P1_runtime_observed=true" in prompt_text
    assert "P1_span=-6.0..0.0" in prompt_text
    assert "P1_deck_audio=global_mix_not_stems" in prompt_text
    assert "rule=part_labels_not_outcome_verdict" in prompt_text
    assert "deck_lanes_context[" in prompt_text
    assert "B=unknown:muted" in prompt_text
    assert "deck_reference_context[" in prompt_text
    assert "deck1=A" in prompt_text
    assert "deck2=B" in prompt_text
    assert "audio=P1_global_mix" in prompt_text
    assert "deck_source_context[" in prompt_text
    assert "second_deck=independent_source_required" in prompt_text
    assert "rule=unresolved_deck_is_not_transition_evidence" in prompt_text
    assert "deck_audio_context[" in prompt_text
    assert "deck_audio_separation_context[" in prompt_text
    assert "deckA_audio=captured" in prompt_text
    assert "deckB_audio=captured" in prompt_text
    assert "per_deck_audio=captured_not_attached" in prompt_text
    assert "deck_audio_features_context[" in prompt_text
    assert "deck_audio_delta_context[" in prompt_text
    assert "source=global_mix" in prompt_text
    assert "audio_window_context[" in prompt_text
    assert "P1=master_global_mix" in prompt_text
    assert "P1_heard=true" in prompt_text
    assert "timeline=past_action_future" in prompt_text
    assert "pre=-6.0..-1.0" in prompt_text
    assert "current=-1.0..0.0" in prompt_text
    assert "action=-1.0..0.0" in prompt_text
    assert "move_anchor=A_low:_flat_to_killed@-1.5s:inside_P1" in prompt_text
    assert "anchors=A_low:_flat_to_killed@-1.5s:inside_P1" in prompt_text
    assert "future_heard=false" in prompt_text
    assert "future=not_attached" in prompt_text
    assert "deckA_audio=not_attached" in prompt_text
    assert "deckB_audio=not_attached" in prompt_text
    assert "AUDIO PART CONTRACT: P1=live_global_mix isolated_decks=false" in prompt_text
    assert "deck_audio_parts=not_attached" in prompt_text
    assert "optional_later_parts_not_current_deck_audio" not in prompt_text
    assert "deck_separation=structured_text_only" in prompt_text
    assert "audio_window_context=time_aligned" in prompt_text
    assert "deck_audio_separation_context=capture_capability" in prompt_text
    assert "live_evidence[" in prompt_text
    assert "move_effect_context[" in prompt_text
    assert "claim_policy[policy=blocked reason=single_resolved_deck" in prompt_text
    assert "global mix, not isolated deck stems" in prompt_text
    assert "Transition/blend/drop/handoff/bridge claims require" in prompt_text


def test_llm_node_04_per_invocation_dump_folder(mocker, tmp_path) -> None:
    """LLM-NODE-04: writes <session>/invocations/NNNN_TS_EVENT/{audio,prompt,
    response,meta} + <session>/last_gemini_audio.wav."""
    agent, gen_client, _recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["hello ", "world"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    invocations = list((tmp_path / "invocations").iterdir())
    assert len(invocations) == 1
    invoke_dir = invocations[0]
    assert invoke_dir.name.startswith("0001_")
    assert invoke_dir.name.endswith("_HEARTBEAT")

    assert (invoke_dir / "audio.wav").read_bytes() == b"FAKEWAV"
    assert (tmp_path / "last_gemini_audio.wav").read_bytes() == b"FAKEWAV"
    assert (invoke_dir / "response.txt").read_text() == "hello world"
    assert (invoke_dir / "prompt.txt").exists()

    meta = json.loads((invoke_dir / "meta.json").read_text())
    expected_keys = {
        "event",
        "ts",
        "invoke_n",
        "audible",
        "deck",
        "track",
        "track_confidence",
        "phase",
        "rms",
        "bpm",
        "audio_bytes",
        "audio_seconds",
        "llm_latency_s",
        "llm_error",
        "response_chars",
    }
    assert expected_keys.issubset(set(meta.keys()))
    assert meta["event"] == "HEARTBEAT"
    assert meta["invoke_n"] == 1
    assert meta["audible"] is True
    assert meta["deck"] == "A"
    assert meta["track"] == "Daft Punk - Around the World"
    assert meta["phase"] == "peak"
    assert meta["audio_bytes"] == len(b"FAKEWAV")
    assert meta["response_chars"] == len("hello world")
    assert meta["llm_error"] is None


def test_llm_node_05_invoke_counter_advances(mocker, tmp_path) -> None:
    """LLM-NODE-05: second invocation gets 0002_ prefix, counter is 2."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    def _stream(*_a, **_kw):
        return _async_iter(["chunk"])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)

    for _ in range(2):
        ev = Event(type="HEARTBEAT", state=state, extra={})
        agent.set_next_event(ev)
        _drive_llm_node(agent)

    invocations = sorted((tmp_path / "invocations").iterdir(), key=lambda p: p.name)
    assert len(invocations) == 2
    assert invocations[0].name.startswith("0001_")
    assert invocations[1].name.startswith("0002_")
    assert agent._invoke_counter == 2


def test_llm_node_06_history_clause_shape(mocker, tmp_path) -> None:
    """LLM-NODE-06: second invocation prompt contains the anti-repetition
    history clause referencing the first invocation's text."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    def _stream(*_a, **_kw):
        return _async_iter(["first_reply "])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    first_contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    first_prompt_text = first_contents[0]
    assert "RECENT THINGS YOU JUST SAID" not in first_prompt_text

    # Now drive a second invocation
    def _stream2(*_a, **_kw):
        return _async_iter(["second_reply"])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream2)
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    second_contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    second_prompt_text = second_contents[0]
    assert "RECENT THINGS YOU JUST SAID (each tagged [M:SS]" in second_prompt_text
    assert "first_reply" in second_prompt_text


def test_llm_node_07_history_truncation_to_140_chars(mocker, tmp_path) -> None:
    """LLM-NODE-07: stripped text truncated to 140 chars before deque append
    (entry also carries a leading [M:SS] set-time prefix — Kaan-directed 2026-05-21)."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="x")

    long_chunk = "A" * 300
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter([long_chunk])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    assert len(agent._ai_text_history) == 1
    # Text portion capped at 140 chars; the [M:SS] prefix adds a few more.
    assert agent._ai_text_history[0].count("A") == 140
    assert agent._ai_text_history[0].startswith("[")


def test_llm_node_08_history_maxlen_10(mocker, tmp_path) -> None:
    """LLM-NODE-08: after 12 successful invocations, deque holds exactly 10."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="x")

    counter = {"n": 0}

    def _stream(*_a, **_kw):
        counter["n"] += 1
        return _async_iter([f"reply_{counter['n']}"])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)

    for _ in range(12):
        ev = Event(type="HEARTBEAT", state=state, extra={})
        agent.set_next_event(ev)
        _drive_llm_node(agent)

    assert len(agent._ai_text_history) == 10


def test_llm_node_09_recorder_log_events(mocker, tmp_path) -> None:
    """LLM-NODE-09: llm_invoke logged before stream, ai_text after non-empty."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["hello"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    kinds = [k for k, _ in recorder.events]
    assert "llm_invoke" in kinds
    assert "ai_text" in kinds
    # llm_invoke first
    assert kinds.index("llm_invoke") < kinds.index("ai_text")

    invoke_kw = dict(recorder.events[kinds.index("llm_invoke")][1])
    assert set(
        [
            "event",
            "audible",
            "deck",
            "track",
            "phase",
            "audio_bytes",
            "has_screen",
            "prompt",
            "invoke_dir",
        ]
    ).issubset(invoke_kw.keys())

    ai_kw = dict(recorder.events[kinds.index("ai_text")][1])
    assert set(["text", "latency_s"]).issubset(ai_kw.keys())


def test_llm_node_10_empty_completion_skips_ai_text_log(mocker, tmp_path) -> None:
    """LLM-NODE-10: empty completion → no ai_text log, no deque append,
    meta.json still has response_chars=0."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["   ", ""])  # whitespace only — strip yields empty
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    kinds = [k for k, _ in recorder.events]
    assert "ai_text" not in kinds
    assert len(agent._ai_text_history) == 0

    invoke_dirs = list((tmp_path / "invocations").iterdir())
    assert len(invoke_dirs) == 1
    meta = json.loads((invoke_dirs[0] / "meta.json").read_text())
    assert meta["response_chars"] == 3  # the three whitespace chars yielded


def test_llm_node_11_exception_does_not_propagate(mocker, tmp_path) -> None:
    """LLM-NODE-11: stream raises → caught, llm_error set in meta.json."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="x")

    async def _raise(*_a, **_kw):
        raise RuntimeError("boom")

    gen_client.aio.models.generate_content_stream = _raise

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    # Should NOT raise
    chunks = _drive_llm_node(agent)
    assert chunks == []

    invoke_dirs = list((tmp_path / "invocations").iterdir())
    meta = json.loads((invoke_dirs[0] / "meta.json").read_text())
    assert meta["llm_error"] is not None
    assert "boom" in meta["llm_error"]


# ---------- PKG-03 ----------


def test_pkg_03_dj_cohost_agent_exported() -> None:
    """PKG-03: DJCoHostAgent resolves from vibemix.agent and is in __all__."""
    import vibemix.agent as vagent

    assert "DJCoHostAgent" in vagent.__all__


# ---------- Plan 18-03 — evidence_registry threading (Tests U–X) ----------


def _build_agent_with_registry(
    mocker, tmp_path: Path, registry
) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
    """Variant of _build_agent that threads an EvidenceRegistry into the agent."""
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
        evidence_registry=registry,
    )
    return agent, genai_client, recorder, state


def test_u_evidence_registry_kwarg_accepted_and_grammar_in_system_instruction(
    mocker, tmp_path
) -> None:
    """Test U — DJCoHostAgent(..., evidence_registry=...) constructs cleanly
    (default None preserves backward compat) AND the system instruction Gemini
    sees contains the citation-grammar block (proves Task 1's wiring reached
    the live LLM path)."""
    from vibemix.state import EvidenceRegistry

    # Default None — backward compat
    agent, _, _, _ = _build_agent(mocker, tmp_path)
    assert agent._registry is None

    # Explicit registry — stored on the agent
    registry = EvidenceRegistry()
    agent2, _, _, _ = _build_agent_with_registry(mocker, tmp_path, registry)
    assert agent2._registry is registry

    # Plan 18-03 Task 1 wiring sanity — system_instruction the LLM sees
    # contains the grammar block. Locks the dispatcher → prompt_body →
    # _gen_cfg.system_instruction path end-to-end.
    assert "[ev:" in agent2._gen_cfg.system_instruction
    assert "encouraged, not required" in agent2._gen_cfg.system_instruction


def test_v_llm_node_calls_build_prompt_with_snapshot_when_registry_wired(mocker, tmp_path) -> None:
    """Test V — when registry wired AND pre-loaded, llm_node calls
    AICoach.build_prompt with kwarg ``registry_snapshot=`` containing the
    loaded observation."""
    from vibemix.state import EvidenceRegistry

    registry = EvidenceRegistry()
    registry.write("ev", "TRACK_CHANGE@30.0", 30.0)

    agent, gen_client, _, state = _build_agent_with_registry(mocker, tmp_path, registry)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    AICoach.build_prompt.assert_called_once()
    call = AICoach.build_prompt.call_args
    # Positional first arg = the Event
    assert call.args[0] is ev
    # Kwarg registry_snapshot present + non-empty + contains the loaded obs
    snap = call.kwargs.get("registry_snapshot")
    assert snap is not None, "registry_snapshot kwarg missing"
    assert "ev" in snap
    assert "TRACK_CHANGE@30.0" in snap["ev"]
    assert snap["ev"]["TRACK_CHANGE@30.0"] == (30.0,)


def test_llm_node_passes_recall_moments_to_diet_mix_move(mocker, tmp_path) -> None:
    """MIX_MOVE can use hot historical move memory without leaving diet mode."""
    from vibemix.state import EvidenceRegistry

    class _StubRecord:
        record_id = "20260520-2200:7"
        signature = (
            "coach_line | event=MIX_MOVE | move_effect=move_effect_context[rule=dsp_delta_not_causal_proof] "
            "| audio_delta=low energy fell 50% (strong) | said: heard the low cut thin out"
        )
        session_id = "20260520-2200"
        ts = 42.0

    class _StubRecall:
        def get_latest(self) -> list:
            return [_StubRecord()]

        def clear(self, bump_generation: bool = True) -> None:
            pass

    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    state.audio_delta = ["low energy fell 50% (strong)"]
    recorder = _FakeRecorder(tmp_path)
    registry = EvidenceRegistry()
    gen_client = mocker.MagicMock()
    agent = DJCoHostAgent(
        genai_client=gen_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
        evidence_registry=registry,
        recall=_StubRecall(),
        recall_enabled=True,
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(
        type="MIX_MOVE",
        state=state,
        extra={
            "moves": ["A_low: flat→killed"],
            "audio_capture_context": {
                "deck_channels": {"A": "0,1", "B": "2,3"},
                "deck_audio_capture_enabled": True,
                "deck_audio_rms": {"A": 0.02, "B": 0.0},
                "deck_audio_features": {
                    "A": {"activity": "active", "rms": 0.02, "peak": 0.1, "zcr": 0.03},
                    "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
                },
                "deck_audio_deltas": {
                    "A": ["rms_rose_100pct_strong"],
                    "B": ["rms_fell_50pct_strong"],
                },
            },
        },
    )
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    kwargs = AICoach.build_prompt.call_args.kwargs
    assert kwargs["diet"] is True
    assert kwargs["recall_moments"][0].record_id == "20260520-2200:7"


def test_recall_query_context_includes_time_aligned_audio_window() -> None:
    state = _build_state()
    state.audible = True
    state.audible_deck = "A"
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.recent_moves = [(0.8, "A_low: flat→killed")]
    state.audio_delta = ["low energy fell 50% (strong)"]

    ev = Event(
        type="MIX_MOVE",
        state=state,
        extra={
            "moves": ["A_low: flat→killed"],
            "audio_capture_context": {
                "deck_channels": {"A": "0,1", "B": "2,3"},
                "deck_audio_capture_enabled": True,
                "deck_audio_rms": {"A": 0.02, "B": 0.0},
                "deck_audio_features": {
                    "A": {"activity": "active", "rms": 0.02, "peak": 0.1, "zcr": 0.03},
                    "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
                },
                "deck_audio_deltas": {
                    "A": ["rms_rose_100pct_strong"],
                    "B": ["rms_fell_50pct_strong"],
                },
                "deck_audio_windows": {
                    "pre_s": [-6.0, -1.0],
                    "current_s": [-1.0, 0.0],
                    "A": {
                        "pre": {
                            "activity": "active",
                            "rms": 0.02,
                            "peak": 0.1,
                            "flux": 0.004,
                        },
                        "current": {
                            "activity": "active",
                            "rms": 0.04,
                            "peak": 0.12,
                            "flux": 0.009,
                        },
                        "delta": ["rms_rose_100pct_strong"],
                    },
                    "B": {
                        "pre": {
                            "activity": "active",
                            "rms": 0.03,
                            "peak": 0.11,
                            "flux": 0.006,
                        },
                        "current": {
                            "activity": "silent",
                            "rms": 0.0,
                            "peak": 0.0,
                            "flux": 0.001,
                        },
                        "delta": ["rms_fell_50pct_strong"],
                    },
                },
            },
        },
    )

    context = _build_recall_query_context(ev)

    assert "context_feed=context_feed_contract[" in context
    assert "surface=gemini_recall_query" in context
    assert "history=past_comparison_not_live_proof" in context
    assert "cache=static_persona_rules_only" in context
    assert "speed=no_extra_model_pass" in context
    assert "audio_window=audio_window_context[" in context
    assert "deck_ref=deck_reference_context[" in context
    assert "deck_audio_separation=deck_audio_separation_context[" in context
    assert "deck_audio_features=deck_audio_features_context[" in context
    assert "A_activity=active" in context
    assert "deck_audio_delta=deck_audio_delta_context[" in context
    assert "A_delta=rms_rose_100pct_strong" in context
    assert "deck_audio_window=deck_audio_window_context[" in context
    assert "timeline=pre_action_current" in context
    assert "A_current=active_rms_0.040" in context
    assert "deck_source=deck_source_context[" in context
    assert "second_deck=independent_source_required" in context
    assert "deck_audio_capture=A_active+B_silent" in context
    assert "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong" in context
    assert "deck1=A" in context
    assert "deck2=B" in context
    assert "P1=master_global_mix" in context
    assert "move_anchor=A_low:_flat_to_killed@-0.8s:inside_P1" in context
    assert "deckA_audio=not_attached" in context


def test_w_llm_node_passes_none_snapshot_when_no_registry(mocker, tmp_path) -> None:
    """Test W — when evidence_registry=None (default — Phase 4 behavior),
    llm_node calls build_prompt with registry_snapshot=None (or kwarg
    absent — both are valid no-op contracts)."""
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)
    assert agent._registry is None  # default

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    AICoach.build_prompt.assert_called_once()
    call = AICoach.build_prompt.call_args
    # Either registry_snapshot=None OR kwarg absent — both are no-op contracts
    snap = call.kwargs.get("registry_snapshot", None)
    assert snap is None, f"expected None snapshot when registry unwired, got {snap!r}"


def test_x_llm_node_takes_fresh_snapshot_per_turn(mocker, tmp_path) -> None:
    """Test X — two consecutive llm_node invocations; between them, write a
    new observation; the SECOND build_prompt call MUST receive a snapshot
    containing the new observation. Locks "snapshot per turn" semantic."""
    from vibemix.state import EvidenceRegistry

    registry = EvidenceRegistry()
    registry.write("ev", "TRACK_CHANGE@10.0", 10.0)

    agent, gen_client, _, state = _build_agent_with_registry(mocker, tmp_path, registry)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    def _stream(*_a, **_kw):
        return _async_iter(["chunk"])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)

    # First turn — snapshot has 1 observation
    ev1 = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev1)
    _drive_llm_node(agent)
    first_snap = AICoach.build_prompt.call_args.kwargs["registry_snapshot"]
    assert "TRACK_CHANGE@10.0" in first_snap["ev"]
    assert "TRACK_CHANGE@20.0" not in first_snap.get("ev", {})

    # Mutate registry between turns — add a fresh observation
    registry.write("ev", "TRACK_CHANGE@20.0", 20.0)

    # Second turn — snapshot MUST include the new observation
    ev2 = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev2)
    _drive_llm_node(agent)
    second_snap = AICoach.build_prompt.call_args.kwargs["registry_snapshot"]
    assert "TRACK_CHANGE@10.0" in second_snap["ev"]
    assert "TRACK_CHANGE@20.0" in second_snap["ev"], (
        "snapshot is stale across llm_node calls — must be taken fresh per turn"
    )


# ---------- Plan 18-03 Task 3 — cross-package smoke test (Test Y) ----------


def test_y_full_prompt_path_evidence_corpus_and_grammar_block_smoke(mocker, tmp_path) -> None:
    """Test Y — END-TO-END smoke (GROUND-02 + GROUND-03):

    Plan 18-01 (registry instantiation) →
    Plan 18-02 (EventDetector._fire writes ev observation; AICoach threads
                snapshot into evidence_line corpus footer) →
    Plan 18-03 (build_system_instruction appends CITATION_GRAMMAR_BLOCK;
                DJCoHostAgent.llm_node passes snapshot through).

    Drive a synthetic TRACK_CHANGE through EventDetector (writes
    [ev:TRACK_CHANGE@<t>] to registry), then call llm_node with the fired
    event. Intercept the ``contents[0]`` string passed to genai.generate_
    content_stream and assert:

      a) "evidence_corpus[ev=" — Plan 18-02 footer present (snapshot threaded
         all the way through to AICoach.evidence_line).
      b) Plan 18-03 Task 1 wiring — _gen_cfg.system_instruction (the LLM-side
         system prompt) contains the CITATION_GRAMMAR_BLOCK (verified via the
         "encouraged, not required" v1.0 fail-open phrase substring).

    Locks the entire Plan 18 prompt-side wiring in one assertion."""
    from vibemix.state import EventDetector, EvidenceRegistry

    # Plan 18-01 — registry
    registry = EvidenceRegistry()
    # Plan 18-02 — EventDetector wired with the registry; firing TRACK_CHANGE
    # writes [ev:TRACK_CHANGE@<t_session>] to the registry as a side effect.
    detector = EventDetector(evidence_registry=registry)

    # Build a state that will trigger TRACK_CHANGE on the SECOND detect()
    # call. The first call seeds last_audible_track baseline; the second
    # observes the change and fires.
    state = _build_state()

    # Plan 18-03 — DJCoHostAgent wired with the SAME registry so its
    # llm_node threads the snapshot through to AICoach.build_prompt.
    agent, gen_client, _, _ = _build_agent_with_registry(mocker, tmp_path, registry)

    # Force EventDetector to bypass music-presence + cooldown gates so the
    # synthetic state in this unit-test environment fires TRACK_CHANGE
    # immediately (the gates exist for live runs; they would otherwise
    # require a 7s warmup + valid BPM history that the unit test can't
    # reasonably synthesize). Patching is the smallest-blast-radius move
    # vs. constructing 10+ state ticks.
    mocker.patch.object(detector, "_music_truly_playing", return_value=True)
    detector.last_audible_track = "OLD_TRACK"  # seed baseline so a flip fires

    # Drive detect() — fires TRACK_CHANGE + writes to registry.
    ev = detector.detect(state, kaan_just_spoke=False, manual=False)
    assert ev is not None, "EventDetector did not fire — test setup bug"
    assert ev.type == "TRACK_CHANGE"

    # Sanity — registry has the [ev:TRACK_CHANGE@<t>] observation.
    snap_check = registry.snapshot()
    assert "ev" in snap_check
    assert any(k.startswith("TRACK_CHANGE") for k in snap_check["ev"]), (
        f"EventDetector._fire did not write to registry; snap={snap_check}"
    )

    # Wire the agent + drive llm_node end-to-end.
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    captured: dict[str, Any] = {}

    async def _capturing_stream(*_a, **kwargs):
        captured["contents"] = kwargs["contents"]
        captured["config"] = kwargs["config"]
        return _async_iter(["[ev:TRACK_CHANGE@30.0] track flipped — heavier"])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_capturing_stream)

    agent.set_next_event(ev)
    _drive_llm_node(agent)

    # (a) Plan 18-02 footer present in the user prompt text — proves the
    # snapshot threaded all the way through to AICoach.evidence_line.
    assert "contents" in captured, "generate_content_stream was not called"
    user_prompt_text: str = captured["contents"][0]
    assert "evidence_corpus[ev=" in user_prompt_text, (
        f"Plan 18-02 corpus footer missing from user prompt; got: {user_prompt_text[:300]!r}"
    )

    # (b) Plan 18-03 Task 1 — the CITATION_GRAMMAR_BLOCK is in the SYSTEM
    # instruction (NOT the user prompt — system instructions live in the
    # GenerateContentConfig). Verify via the v1.0 fail-open phrase.
    sys_instr: str = captured["config"].system_instruction
    assert "encouraged, not required" in sys_instr, (
        "CITATION_GRAMMAR_BLOCK missing from system_instruction — Plan 18-03 Task 1 wiring broken"
    )
    # Grammar surface check — at least one EBNF source form is in the system
    # instruction so Gemini can pattern-match against it.
    assert "[ev:" in sys_instr


# ---------- Plan 18-04 — citation-count telemetry (Tests AE–AJ) -------------


def test_AE_citation_count_event_written_per_turn(mocker, tmp_path) -> None:
    """Test AE — every Gemini turn writes a ``citation_count`` events.jsonl
    line with the integer count parsed from the FULL response text + a
    response_id matching the per-invocation dump folder pattern.

    Closes ROADMAP success criterion #4: events.jsonl records
    citation_count_per_response per AI turn.
    """
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # Two valid citations in the response.
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["great drop [ev:KICK_SWAP@45.2] [aud:bpm@45.2]"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    citation_events = [e for e in recorder.events if e[0] == "citation_count"]
    assert len(citation_events) == 1, (
        f"expected 1 citation_count event, got {len(citation_events)}: {recorder.events!r}"
    )
    kind, fields = citation_events[0]
    assert kind == "citation_count"
    assert fields["count"] == 2
    # response_id matches NNNN_TS pattern (e.g. "0001_HHMMSS")
    rid = fields["response_id"]
    assert rid.startswith("0001_"), f"response_id {rid!r} should start with 0001_"
    assert len(rid.split("_")) == 2


def test_AF_citation_count_fires_for_silence_suppressed_turn(mocker, tmp_path) -> None:
    """Test AF — silence-suppressed turn STILL emits citation_count.

    Phase 16 ear-test needs Gemini's true emission rate, NOT the post-
    suppression rate. A turn that emits ``<silence/>`` along with an ev
    citation must still register count=1 in events.jsonl.
    """
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # <silence/> short-circuits the turn but the citation atom is still in
    # the full_text the parser sees.
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/> [ev:HEARTBEAT@30.0]"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    kinds = [k for k, _ in recorder.events]
    # Suppression MUST have fired (silence_short_circuit) AND citation_count
    # MUST have been written for the same turn.
    assert "silence_short_circuit" in kinds
    citation_events = [e for e in recorder.events if e[0] == "citation_count"]
    assert len(citation_events) == 1
    assert citation_events[0][1]["count"] == 1


def test_AG_citation_count_zero_when_no_citations(mocker, tmp_path) -> None:
    """Test AG — response with zero citations emits ``count=0``."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["great drop"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    citation_events = [e for e in recorder.events if e[0] == "citation_count"]
    assert len(citation_events) == 1
    assert citation_events[0][1]["count"] == 0


def test_AH_registry_record_citation_count_called_per_turn(mocker, tmp_path) -> None:
    """Test AH — when registry wired, ``record_citation_count`` is called per
    llm_node turn, advancing ``citation_telemetry()["total_turns_observed"]``
    by exactly 1 per call."""
    from vibemix.state import EvidenceRegistry

    registry = EvidenceRegistry()
    agent, gen_client, _, state = _build_agent_with_registry(mocker, tmp_path, registry)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    def _stream(*_a, **_kw):
        return _async_iter(["great drop [ev:KICK_SWAP@45.2] [aud:bpm@45.2]"])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)

    # Pre-call baseline.
    assert registry.citation_telemetry()["total_turns_observed"] == 0

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)
    assert registry.citation_telemetry()["total_turns_observed"] == 1
    assert registry.citation_telemetry()["mean"] == 2.0  # 2 citations parsed

    # Second call advances total_turns by 1 again.
    ev2 = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev2)
    _drive_llm_node(agent)
    assert registry.citation_telemetry()["total_turns_observed"] == 2


def test_AI_telemetry_path_is_best_effort_never_raises(mocker, tmp_path) -> None:
    """Test AI — if ``parse_citations`` raises (corrupt regex, OOM, anything),
    the LLM response path MUST still complete: chunks yielded, ai_text event
    written. No exception escapes into the LiveKit cascade.

    Mitigates threat T-18-04-03 (telemetry breaking the LLM stream).
    """
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # Force parse_citations to raise — simulates a corrupt regex / OOM /
    # whatever future regression. The agent code MUST swallow it.
    mocker.patch(
        "vibemix.agent.dj_cohost.parse_citations",
        side_effect=RuntimeError("simulated parse failure"),
    )
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["clean reply text"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    # MUST NOT raise.
    chunks = _drive_llm_node(agent)
    assert chunks == ["clean reply text"]
    # ai_text event still written — LLM response path completed cleanly.
    kinds = [k for k, _ in recorder.events]
    assert "ai_text" in kinds
    # citation_count may be missing OR count=0 — both are valid best-effort
    # outcomes. The hard contract is "no exception escapes".
    citation_events = [e for e in recorder.events if e[0] == "citation_count"]
    if citation_events:
        # If the agent chose to emit a fallback count=0, that's fine too.
        assert citation_events[0][1]["count"] == 0


def test_AJ_no_registry_path_writes_recorder_event_only(mocker, tmp_path) -> None:
    """Test AJ — when ``evidence_registry=None`` (default Phase 4 backward-
    compat), ``citation_count`` event STILL lands in events.jsonl (recorder-
    side write), but the registry-side rolling buffer is simply not updated
    (because there is no registry).
    """
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    assert agent._registry is None  # default

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["great drop [track:abc-123]"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    citation_events = [e for e in recorder.events if e[0] == "citation_count"]
    assert len(citation_events) == 1, (
        "citation_count events.jsonl line MUST land even when no registry wired"
    )
    assert citation_events[0][1]["count"] == 1


# ---------- Plan 18-04 Task 3 — Phase 16 readiness signal (Test AK) ---------


def test_AK_phase16_readiness_signal_end_to_end(mocker, tmp_path) -> None:
    """Test AK — END-TO-END Phase 16 readiness signal (ROADMAP success #4):

    Construct the full stack (registry + EventDetector(registry) +
    DJCoHostAgent(registry)). Drive 10 mock LLM turns with varying
    citation counts. After all turns, ``registry.citation_telemetry()``
    returns the EXACT signal Phase 16 ear-test will consume to gate
    Phase 20 enforcement readiness.

    Counts: [3, 0, 2, 1, 4, 0, 2, 5, 1, 3] = 21 total / 10 turns = mean 2.1
    """
    from vibemix.state import EventDetector, EvidenceRegistry

    registry = EvidenceRegistry()
    # Construct EventDetector with the same registry (Plan 18-02 wiring).
    EventDetector(evidence_registry=registry)

    agent, gen_client, _, state = _build_agent_with_registry(mocker, tmp_path, registry)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    # Build 10 response strings with the exact citation counts below.
    # Use a mix of single-citation and multi-citation forms so the parser
    # exercises both paths.
    responses = [
        "[ev:A@1] [ev:B@2] [ev:C@3]",  # 3
        "no citations here",  # 0
        "[ev:A@1,aud:bpm@1]",  # 2 (multi-citation in one bracket)
        "[track:xyz-1]",  # 1
        "[ev:A@1] [aud:bpm@2] [midi:cue_a@3] [track:xyz-1]",  # 4
        "<silence/>",  # 0
        "[ev:A@1] [aud:bpm@2]",  # 2
        "[ev:A@1] [aud:bpm@2] [midi:cue_a@3] [track:xyz-1] [screen:wave_a]",  # 5
        "[mix:audible_deck=A]",  # 1
        "[mix:audible_deck=A] [ev:A@1] [aud:bpm@2]",  # 3
    ]
    expected_counts = [3, 0, 2, 1, 4, 0, 2, 5, 1, 3]

    response_iter = iter(responses)

    def _stream(*_a, **_kw):
        return _async_iter([next(response_iter)])

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)

    for _ in range(10):
        ev = Event(type="HEARTBEAT", state=state, extra={})
        agent.set_next_event(ev)
        _drive_llm_node(agent)

    tel = registry.citation_telemetry()
    assert tel["window_size"] == 10
    assert tel["total_turns_observed"] == 10
    expected_mean = sum(expected_counts) / 10
    assert tel["mean"] == expected_mean, (
        f"Phase 16 readiness signal drift: expected mean {expected_mean}, got {tel['mean']}"
    )


# ---------- Plan 19-05 — TTFTMeter wiring ----------


def _build_agent_with_meter(mocker, tmp_path: Path, meter):
    """Construct a DJCoHostAgent wired to the supplied TTFTMeter."""
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
        ttft_meter=meter,
    )
    return agent, genai_client, recorder, state


def test_ttft_set_next_event_calls_meter_record_event_fired(mocker, tmp_path) -> None:
    """Plan 19-05: agent.set_next_event(ev) → meter.record_event_fired called."""
    meter = mocker.MagicMock()
    agent, _, _, state = _build_agent_with_meter(mocker, tmp_path, meter)
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    meter.record_event_fired.assert_called_once()


def test_ttft_set_next_event_no_meter_does_nothing(mocker, tmp_path) -> None:
    """Plan 19-05: agent constructed without ttft_meter — set_next_event still works."""
    agent, _, _, state = _build_agent(mocker, tmp_path)
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)  # Must not raise
    assert agent._pending_event is ev


def test_ttft_llm_node_records_first_chunk_on_first_non_empty(mocker, tmp_path) -> None:
    """Plan 19-05: llm_node calls meter.record_first_chunk exactly once on the
    first non-empty chunk yield (not per-chunk)."""
    meter = mocker.MagicMock()
    agent, gen_client, _, state = _build_agent_with_meter(mocker, tmp_path, meter)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["", "hello", " ", "kaan"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    # Exactly one record_first_chunk call (on "hello" — the first non-empty).
    meter.record_first_chunk.assert_called_once()


# ---------- Phase 66 review WR-04 regression — set_s_at_event threading ----------


def test_record_said_uses_event_fired_set_seconds_when_provided(mocker, tmp_path) -> None:
    """Phase 66 WR-05 (regression for WR-04) — when ``_record_said`` is called
    with ``set_s_at_event=<captured-at-event-time>``, the [M:SS] stamp baked
    into ``_ai_text_history`` MUST reflect that captured value, NOT the live
    ``self._state.set_seconds`` at the moment of the call.

    Pins the "event-fired set_seconds threaded through _record_said" contract.
    A future refactor that drops the kwarg threading at any of the three
    llm_node call sites would silently re-engage the multi-second-drift bug
    WR-04 closed (~2-3s drift across stream + lint + bus emit on a typical
    reaction turn). This test catches that regression.
    """
    agent, _, _, state = _build_agent(mocker, tmp_path)

    # Live state.set_seconds = 12.5s into the set (post-stream snapshot — the
    # drifted value). The event fired at 10.0s — that is the value we MUST
    # see in the history stamp.
    state.set_start_at = 1000.0
    mocker.patch(
        "vibemix.state.music_state.time.time",
        return_value=1012.5,
    )

    agent._record_said("clean reply text", set_s_at_event=10.0)

    assert len(agent._ai_text_history) == 1
    entry = agent._ai_text_history[0]
    # Event fired at 10s → [0:10]. If the threading regresses and the kwarg
    # is dropped, the fallback path reads live state.set_seconds (=12.5) →
    # [0:12], failing this assertion.
    assert entry.startswith("[0:10]"), (
        f"expected event-fired stamp [0:10]; got {entry!r} — WR-04 regression: "
        "set_s_at_event kwarg not honored by _record_said"
    )
    assert "clean reply text" in entry


def test_record_said_legacy_fallback_uses_live_state_set_seconds(mocker, tmp_path) -> None:
    """Phase 66 WR-05 (regression for WR-04 — fallback half) — when
    ``_record_said`` is called WITHOUT ``set_s_at_event`` (or with None), it
    falls back to live ``self._state.set_seconds`` (the legacy pre-WR-04
    behavior). This is the multi-second-drift footprint by design — kept
    so legacy callers that don't yet thread the event-fired value still
    work.

    Pins the "None fallback === live state.set_seconds" contract so a
    future refactor that changes the fallback semantics (e.g. defaults to
    0.0 or raises) is caught here. Combined with the sibling test above,
    this nails both halves of the _record_said(set_s_at_event=...) contract.
    """
    agent, _, _, state = _build_agent(mocker, tmp_path)

    # state.set_seconds == 12.5 — same drifted-clock setup as the sibling
    # test, but this time we DON'T pass set_s_at_event.
    state.set_start_at = 1000.0
    mocker.patch(
        "vibemix.state.music_state.time.time",
        return_value=1012.5,
    )

    # Legacy call shape — no set_s_at_event kwarg at all.
    agent._record_said("legacy reply")
    # Explicit-None call shape — same fallback path.
    agent._record_said("explicit none reply", set_s_at_event=None)

    assert len(agent._ai_text_history) == 2
    # Both entries reflect live state.set_seconds (12.5s → [0:12]) — the
    # documented legacy multi-second-drift behavior the fallback preserves.
    assert agent._ai_text_history[0].startswith("[0:12]"), (
        f"expected legacy live-state stamp [0:12]; got {agent._ai_text_history[0]!r}"
    )
    assert agent._ai_text_history[1].startswith("[0:12]"), (
        f"expected legacy live-state stamp [0:12] for explicit-None; got "
        f"{agent._ai_text_history[1]!r}"
    )


def test_llm_node_threads_event_fired_set_seconds_to_record_said(mocker, tmp_path) -> None:
    """Phase 66 WR-05 (regression for WR-04 — end-to-end) — drive ``llm_node``
    with a clock that advances DURING the stream (event fires at 10.0s,
    _record_said is reached at 12.5s after stream + lint + bus emit). The
    [M:SS] stamp baked into ``_ai_text_history`` MUST reflect 0:10 (the
    event-fired set_seconds), NOT 0:12 (the post-emit live set_seconds).

    Locks the capture-at-top-of-llm_node + kwarg-threaded-to-three-call-sites
    contract end-to-end. A future refactor that:
      * drops the ``ev_set_seconds = float(getattr(ev.state, "set_seconds", 0.0) ...)``
        capture at the top of llm_node, OR
      * drops the ``set_s_at_event=ev_set_seconds`` kwarg at any of the
        three ``_record_said`` call sites (legacy ai_text path, citation
        bypass path, citation valid path)
    would re-engage the multi-second-drift bug and fail this test.
    """
    agent, gen_client, _, state = _build_agent(mocker, tmp_path)

    # Event fired at set_seconds=10.0; by the time _record_said runs (after
    # stream + lint + bus emit), set_seconds has advanced to 12.5. The
    # WR-04 fix MUST stamp 0:10, not 0:12.
    state.set_start_at = 1000.0
    times = iter([1010.0, 1012.5, 1012.5, 1012.5, 1012.5, 1012.5])

    def _advancing_time() -> float:
        try:
            return next(times)
        except StopIteration:
            return 1012.5

    mocker.patch(
        "vibemix.state.music_state.time.time",
        side_effect=_advancing_time,
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["clean reply"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    assert len(agent._ai_text_history) == 1
    entry = agent._ai_text_history[0]
    # 10s = 0:10. If WR-04 regresses and the kwarg threading is dropped,
    # the fallback path reads live state.set_seconds (=12.5) → 0:12,
    # failing this assertion.
    assert entry.startswith("[0:10]"), (
        f"expected event-fired stamp [0:10]; got {entry!r} — WR-04 regression: "
        "ev_set_seconds capture or set_s_at_event= threading dropped"
    )
    assert "clean reply" in entry


# ---------------------------------------------------------------------------
# Phase 79 Wave 0 — _resolve_prompt_cell reads the SHARED lens
#
# Plan 03 edits _resolve_prompt_cell so a shared lens (read from
# ConfigStore.extra["lens"]) resolves (mode, mood) via LENS_TO_MODE_MOOD. When
# NO lens is set (cold path), the existing env/DEFAULT_* resolution is unchanged
# → byte-identical to today. xfail-strict until Plan 03.
# ---------------------------------------------------------------------------

import vibemix.agent.dj_cohost as dj_mod  # noqa: E402
from vibemix.prompts.matrix import build_system_instruction  # noqa: E402


def test_resolve_prompt_cell_uses_shared_lens(tmp_path, monkeypatch) -> None:
    """A shared lens 'critique' resolves the (coach, coach) cell.

    The lens read wins over the DEFAULT_* env resolution — critique → coach mode
    → a coach-cell prompt (NOT today's hype default). xfail-strict until Plan 03
    wires _resolve_prompt_cell to read extra['lens'].
    """
    import vibemix.runtime.config_store as cs_mod

    # No env overrides — prove the lens (not the env) drives the cell.
    monkeypatch.delenv("VIBEMIX_MODE", raising=False)
    monkeypatch.delenv("VIBEMIX_MOOD", raising=False)
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    store.extra["lens"] = "critique"
    cs_mod.save_config(store)

    out = dj_mod._resolve_prompt_cell()
    # critique → (coach, coach): the coach persona fragment is substituted in.
    assert "post-mortem-anchored" in out


def test_resolve_prompt_cell_cold_path_byte_identical(tmp_path, monkeypatch) -> None:
    """With NO shared lens + default env, the live cell stays deterministic.

    REAL-GREEN co-host cold-path guard: when extra['lens'] is unset and no env
    overrides, _resolve_prompt_cell must equal the MOSS-only live prompt shape:
    default hype cell + grounding/audio contract, but no legacy Gemini-TTS tags.
    """
    import vibemix.runtime.config_store as cs_mod

    monkeypatch.delenv("VIBEMIX_MODE", raising=False)
    monkeypatch.delenv("VIBEMIX_MOOD", raising=False)
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    assert "lens" not in store.extra
    cs_mod.save_config(store)

    out = dj_mod._resolve_prompt_cell()
    assert out == build_system_instruction(
        "intermediate",
        "hype",
        "hype-man",
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
    )
    assert AUDIO_VIBE_CONTRACT_BLOCK in out
    for tag in TTS_TAGS:
        assert tag not in out


def test_resolve_prompt_cell_lens_wins_over_live_mood(tmp_path, monkeypatch) -> None:
    """CR-01 production-path pin: an explicit lens WINS over the live mood arg.

    The real caller ``DJCoHostAgent.__init__`` ALWAYS passes a non-None
    ``mood=live_mood`` (``MusicState.mood`` defaults "hype-man", never None). The
    old guard only consulted the lens when ``mood is None``, so setting the lens
    had zero effect on the live co-host. This test exercises the REAL production
    call shape (``mood="hype-man"``) with a ``tutor`` lens and asserts the tutor
    cell (coach mode + teacher persona) is produced — NOT the default hype cell.
    """
    import vibemix.runtime.config_store as cs_mod

    monkeypatch.delenv("VIBEMIX_MODE", raising=False)
    monkeypatch.delenv("VIBEMIX_MOOD", raising=False)
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    store.extra["lens"] = "tutor"
    cs_mod.save_config(store)

    # The exact arg the production agent passes — auto-derived live mood.
    out = dj_mod._resolve_prompt_cell(mood="hype-man")
    # tutor → (coach, teacher): the teacher persona fragment is substituted in,
    # and it equals the canonical tutor cell — NOT the hype default.
    assert "framework-anchored" in out
    assert out == build_system_instruction(
        "intermediate",
        "coach",
        "teacher",
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
    )
    for tag in TTS_TAGS:
        assert tag not in out


def test_resolve_prompt_cell_corrupt_lens_falls_back_no_crash(tmp_path, monkeypatch) -> None:
    """CR-02: a corrupt persisted lens must NOT crash agent construction.

    ``read_shared_lens`` returns any non-empty string unvalidated. A
    ``config.json`` carrying ``extra["lens"]="coach"`` (a valid MOOD but not a
    lens key) used to raise an uncaught ``KeyError`` on the raw
    ``LENS_TO_MODE_MOOD[lens]`` subscript. The fix validates before subscripting
    and falls through to the cold path — so with default env the result is the
    byte-identical hype default, no exception.
    """
    import vibemix.runtime.config_store as cs_mod

    monkeypatch.delenv("VIBEMIX_MODE", raising=False)
    monkeypatch.delenv("VIBEMIX_MOOD", raising=False)
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    store.extra["lens"] = "coach"  # valid mood, NOT a valid lens key
    cs_mod.save_config(store)

    # Must not raise; falls through to the cold path (default hype cell).
    out = dj_mod._resolve_prompt_cell(mood="hype-man")
    assert out == build_system_instruction(
        "intermediate",
        "hype",
        "hype-man",
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
    )
    for tag in TTS_TAGS:
        assert tag not in out
