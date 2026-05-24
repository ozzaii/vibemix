# SPDX-License-Identifier: Apache-2.0
"""v8.0 LOG-02 — per-turn consolidated evidence + citation-gate logging.

When the debug-log switch is ON, every reaction turn appends one
``reaction_evidence`` event (evidence-source digest + the citation-gate
decision) to events.jsonl. When OFF (default), it is absent — the discrete
citation_count / ai_text events are unchanged (byte-identical default).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.runtime import debug_flags
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState


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


def _state() -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.audible_track = "Daft Punk - Around the World"
    s.audible_track_confidence = 0.8
    s.phase = "peak"
    s.rms = 0.05
    s.bpm = 128.0
    return s


def _wired_agent(mocker, tmp_path: Path):
    mocker.patch.object(Agent, "__init__", return_value=None)
    recorder = _FakeRecorder(tmp_path)
    gen = mocker.MagicMock()
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)
    state = _state()
    agent = DJCoHostAgent(
        genai_client=gen,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
        evidence_registry=registry,
        citation_linter=CitationLinter(),
        stripped_rate_tracker=StrippedRateTracker(),
        playback=mocker.MagicMock(),
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["that drop [ev:KICK_SWAP@45.2] was clean"])
    )
    return agent, recorder, state


def _drive(agent: DJCoHostAgent) -> None:
    async def _go():
        async for _ in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            pass

    asyncio.run(_go())


@pytest.fixture(autouse=True)
def _restore_flag():
    before = debug_flags.debug_log_enabled()
    yield
    debug_flags.set_debug_log(before)


def test_reaction_evidence_logged_when_debug_on(mocker, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_DEBUG_LOG", raising=False)
    debug_flags.set_debug_log(True)
    agent, recorder, state = _wired_agent(mocker, tmp_path)
    agent.set_next_event(Event(type="TRACK_CHANGE", state=state, extra={}))
    _drive(agent)

    kinds = [k for k, _ in recorder.events]
    assert "reaction_evidence" in kinds
    rec = next(f for k, f in recorder.events if k == "reaction_evidence")
    assert rec["citation_action"] == "emit"
    assert rec["citation_count"] >= 1
    # Evidence digest is a {source: count} dict including the registered 'ev'.
    assert isinstance(rec["evidence_sources"], dict)
    assert rec["evidence_sources"].get("ev", 0) >= 1


def test_reaction_evidence_absent_when_debug_off(mocker, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_DEBUG_LOG", raising=False)
    debug_flags.set_debug_log(False)
    agent, recorder, state = _wired_agent(mocker, tmp_path)
    agent.set_next_event(Event(type="TRACK_CHANGE", state=state, extra={}))
    _drive(agent)

    kinds = [k for k, _ in recorder.events]
    assert "reaction_evidence" not in kinds
    # Default decision telemetry is unchanged — ai_text still logged.
    assert "ai_text" in kinds
