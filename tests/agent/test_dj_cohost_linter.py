# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent.llm_node — Plan 20-01 Task 2 wiring.

Pins the 4-kwarg wiring (citation_linter, stripped_rate_tracker, ack_bank,
playback) for the post-stream citation gate. Contract:

- All four None (default) → legacy Phase 18/19 path is byte-identical
  (no linter check, no [unverified] log, no ack fallback).
- All four non-None ("wired" mode) → post-stream gate runs after silence/
  slop suppression. Decision ladder: valid → emit + record(False); invalid
  + bypass → emit + record(False) + citation_bypass log; invalid + strip →
  no emit + ack-bank PCM push + citation_strip log + record(True).
- History append on bypass (text was emitted, no-repeat history must
  reflect it) but NOT on strip (no text emitted = nothing to repeat).
- Unknown event class on strip path → ack_bucket=None, no ack played.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import numpy as np
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState

# --------------------------------------------------------------------------
# Helpers (mirrored from tests/agent/test_dj_cohost.py)
# --------------------------------------------------------------------------


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


def _build_agent_legacy(mocker, tmp_path: Path):
    """Phase 18-style construction: 4 new kwargs left at default None."""
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


def _build_agent_wired(mocker, tmp_path: Path, registry: EvidenceRegistry):
    """Phase 20 wired construction: all 4 new kwargs supplied + registry."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()

    linter = CitationLinter()
    tracker = StrippedRateTracker()
    ack_bank = mocker.MagicMock()
    # Default pick_for_event return — overridden per-test as needed.
    fake_pcm = np.zeros(1024, dtype=np.int16)
    ack_bank.pick_for_event.return_value = ("generic_filler", fake_pcm, 3)
    playback = mocker.MagicMock()

    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
        evidence_registry=registry,
        citation_linter=linter,
        stripped_rate_tracker=tracker,
        ack_bank=ack_bank,
        playback=playback,
    )
    return agent, genai_client, recorder, state, linter, tracker, ack_bank, playback


def _drive(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        out: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            out.append(txt)
        return out

    return asyncio.run(_go())


# --------------------------------------------------------------------------
# (a) Legacy path byte-identical when 4 kwargs are None
# --------------------------------------------------------------------------


def test_legacy_path_byte_identical_when_kwargs_none(mocker, tmp_path) -> None:
    """No linter kwargs → Phase 18 behavior preserved.

    Construct without any of the 4 new kwargs; clean text reply with NO
    citations would be stripped under the wired path, but the legacy path
    must yield it verbatim and log ai_text. This is the v4 byte-identity
    contract (CLAUDE.md project skill).
    """
    agent, gen, recorder, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["clean reply with no citations"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    # Legacy path: chunks emitted regardless of citation grounding.
    assert chunks == ["clean reply with no citations"]
    kinds = [k for k, _ in recorder.events]
    assert "ai_text" in kinds
    assert "citation_strip" not in kinds
    assert "citation_bypass" not in kinds
    # Public state guards: linter wired flag is False.
    assert agent._linter_wired is False


# --------------------------------------------------------------------------
# (b) Valid response passes through when wired
# --------------------------------------------------------------------------


def test_valid_response_passes_through_when_wired(mocker, tmp_path) -> None:
    """Wired + valid citation → chunks yielded + tracker.record(False) +
    ai_text logged. No strip, no bypass, no ack."""
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)
    agent, gen, recorder, state, _, tracker, ack_bank, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["that drop [ev:KICK_SWAP@45.2] was clean"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    assert chunks == ["that drop [ev:KICK_SWAP@45.2] was clean"]
    kinds = [k for k, _ in recorder.events]
    assert "ai_text" in kinds
    assert "citation_strip" not in kinds
    assert "citation_bypass" not in kinds
    # Tracker was told the response was NOT stripped.
    assert tracker.rate() == 0.0
    # Ack bank never consulted on valid path.
    ack_bank.pick_for_event.assert_not_called()
    playback.push.assert_not_called()


# --------------------------------------------------------------------------
# (c) Invalid response strips and fires ack
# --------------------------------------------------------------------------


def test_invalid_response_strips_and_fires_ack(mocker, tmp_path) -> None:
    """Wired + invalid citation → no chunks yielded + ack_bank.pick_for_event
    called + playback.push called + citation_strip logged."""
    registry = EvidenceRegistry()  # empty — citation will not match
    agent, gen, recorder, state, _, tracker, ack_bank, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["fake [ev:UNKNOWN@99.0] reply"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    # No chunks yielded — strip path.
    assert chunks == []
    # Ack-bank fired with the pending event.
    ack_bank.pick_for_event.assert_called_once_with(ev)
    # Playback got the ack PCM bytes.
    playback.push.assert_called_once()
    push_arg = playback.push.call_args.args[0]
    assert isinstance(push_arg, bytes)
    # citation_strip logged.
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    strip_log = next(f for k, f in recorder.events if k == "citation_strip")
    assert strip_log["response_id"].startswith("0001_")
    assert "fake" in strip_log["raw_text"]
    assert ("ev", "UNKNOWN@99.0") in strip_log["missing"] or [
        "ev",
        "UNKNOWN@99.0",
    ] in strip_log["missing"]
    assert strip_log["reason"] == "invalid_atoms"
    # Tracker was told the response WAS stripped.
    assert tracker.rate() == 1.0
    # ai_text NOT logged on strip.
    assert "ai_text" not in kinds


# --------------------------------------------------------------------------
# (d) No-citations response strips
# --------------------------------------------------------------------------


def test_no_citations_response_strips(mocker, tmp_path) -> None:
    """Wired + uncited reply → strip (no_citations reason)."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, ack_bank, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["that was clean"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    strip_log = next(f for k, f in recorder.events if k == "citation_strip")
    assert strip_log["reason"] == "no_citations"
    ack_bank.pick_for_event.assert_called_once_with(ev)
    playback.push.assert_called_once()
    assert tracker.rate() == 1.0


# --------------------------------------------------------------------------
# (e) Bypass emits with [unverified] marker
# --------------------------------------------------------------------------


def test_bypass_emits_with_unverified_marker(mocker, tmp_path, capsys) -> None:
    """Force tracker.should_bypass()→True; invalid response → chunks YIELDED,
    citation_bypass logged, stdout contains '[ai_text:unverified]'."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, ack_bank, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # Force the bypass to fire on this turn — monkey-patch the tracker's
    # should_bypass to return True exactly once (mirrors one-shot semantic).
    bypass_calls = {"n": 0}

    def _force_bypass() -> bool:
        bypass_calls["n"] += 1
        return bypass_calls["n"] == 1

    mocker.patch.object(tracker, "should_bypass", side_effect=_force_bypass)
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["unverified [ev:NONEXISTENT@1.0] reply"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    # Chunks ARE yielded under bypass.
    assert chunks == ["unverified [ev:NONEXISTENT@1.0] reply"]
    kinds = [k for k, _ in recorder.events]
    assert "citation_bypass" in kinds
    bypass_log = next(f for k, f in recorder.events if k == "citation_bypass")
    assert bypass_log["response_id"].startswith("0001_")
    assert "unverified" in bypass_log["raw_text"]
    assert bypass_log["reason"] == "invalid_atoms"
    # Ack NOT fired on bypass — we emitted text instead.
    ack_bank.pick_for_event.assert_not_called()
    playback.push.assert_not_called()
    # Stdout marker.
    captured = capsys.readouterr().out
    assert "[ai_text:unverified]" in captured


# --------------------------------------------------------------------------
# (f) Strip path with unknown event class → ack_bucket=None
# --------------------------------------------------------------------------


def test_strip_path_with_unknown_event_class(mocker, tmp_path) -> None:
    """ev.type='WEIRD' not in BUCKET_FOR_EVENT → strip still happens but no
    ack played and citation_strip log records ack_bucket=None."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, ack_bank, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["[ev:GHOST@1.0] junk"])
    )

    # Construct event with an event type not in BUCKET_FOR_EVENT.
    ev = Event(type="WEIRD", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    assert chunks == []  # strip
    # ack_bank NOT called (event type unknown to bucket map).
    ack_bank.pick_for_event.assert_not_called()
    playback.push.assert_not_called()
    # citation_strip logged with ack_bucket=None.
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    strip_log = next(f for k, f in recorder.events if k == "citation_strip")
    assert strip_log["ack_bucket"] is None
    # Tracker still recorded the strip.
    assert tracker.rate() == 1.0


# --------------------------------------------------------------------------
# (g) History appended on bypass, NOT on strip
# --------------------------------------------------------------------------


def test_history_appended_on_bypass_not_on_strip(mocker, tmp_path) -> None:
    """_ai_text_history grows on bypass (text was emitted) but NOT on strip
    (no text emitted = nothing to repeat)."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, ack_bank, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    # Turn 1: strip path (no bypass).
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["[ev:NONE@1.0] one"])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)
    assert len(agent._ai_text_history) == 0, "strip path must NOT grow history"

    # Turn 2: force bypass.
    bypass_state = {"used": False}

    def _force_bypass_once() -> bool:
        if bypass_state["used"]:
            return False
        bypass_state["used"] = True
        return True

    mocker.patch.object(tracker, "should_bypass", side_effect=_force_bypass_once)
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["[ev:NONE@2.0] two"])
    )
    ev2 = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev2)
    _drive(agent)
    assert len(agent._ai_text_history) == 1, "bypass path MUST grow history"
    assert "two" in agent._ai_text_history[0]
