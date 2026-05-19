# SPDX-License-Identifier: Apache-2.0
"""Plan 41-04 Task 2 — DJCoHostAgent llm_node streaming pipe-through tests.

Pins the dual-phase gate behavior:

  * **Head-fast emit:** as soon as ``find_sentence_end`` returns a
    boundary at bracket depth 0, the head is yielded SPECULATIVELY before
    the LLM stream completes — provided ``passes_head_gate`` clears it.
    The LLMToTTSDeltaMeter records the head-emission timestamp.

  * **Trailing-fast emit:** subsequent chunks stream as-they-arrive (no
    further sentence-boundary accumulator gating — the head has already
    bound the speculative path, trailing audio just keeps the listener in
    flow).

  * **Post-stream full gate:** after stream completes, the existing
    silence-suppression / slop-filter / citation-linter pipeline runs on
    the full text. When the head was emitted speculatively AND the
    post-stream gate fails (slop / citation_failure), a silence-pad
    frame is pushed to the playback queue and a ``streaming_cancel``
    event is emitted (T-41-04-01 / T-41-04-04 mitigation).

  * **Pitfall 1 — citation period collision:** a period INSIDE
    ``[ev:foo@2.5]`` must NEVER trigger a premature yield.

  * **Phase 40 regression baseline preserved:** Part 1/2/3 attach logic
    untouched; recorder events for mic_part_* / lookahead_part_* still
    fire on the same code path.

Tests rely on a mocker-driven async stream so chunk timing is
deterministic. The meter's ``time_fn`` is left at default (monotonic) —
the streaming-pipe assertions check ORDER + EMISSION, not absolute ms.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState


# ---------- helpers ----------


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
    """Construct without the citation-linter wiring (Phase 18 path)."""
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
    """Construct with all 4 linter kwargs supplied (Phase 20 wired path)."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()

    linter = CitationLinter()
    tracker = StrippedRateTracker()
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
        playback=playback,
    )
    return agent, genai_client, recorder, state, tracker, playback


def _drive(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        out: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            out.append(txt)
        return out

    return asyncio.run(_go())


# ---------- Streaming-pipe tests ----------


def test_first_sentence_streams_before_completion(mocker, tmp_path) -> None:
    """Head yields after the first chunk (containing the boundary) — the
    subsequent chunks stream as-they-arrive.

    The chunked split ``["This is a long enough opener. ", "Then a tail.",
    " Closing."]`` yields the head as soon as the first chunk's "opener. "
    boundary clears MIN_HEAD_LEN. Tail chunks pass through unchanged.
    """
    agent, gen, _, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "This is a long enough opener. ",
                "Then a tail.",
                " Closing.",
            ]
        )
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    # First yielded element MUST contain the head sentence. Trailing
    # chunks stream as-they-arrive (legacy yielded order preserved).
    full = "".join(chunks)
    assert full == "This is a long enough opener. Then a tail. Closing."
    # The head must come out as the first yield (proves speculative emit).
    assert chunks[0] == "This is a long enough opener. "


def test_no_boundary_in_short_response_yields_after_stream(mocker, tmp_path) -> None:
    """No mid-stream boundary → head never emitted; full text yields
    post-stream via the legacy emit branch."""
    agent, gen, _, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # 'Yeah.' = 5 chars, below MIN_HEAD_LEN — no head fires.
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Yeah."])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    # The legacy path emits "Yeah." as a single tail chunk.
    assert "".join(chunks) == "Yeah."


def test_silence_token_head_suppresses_all(mocker, tmp_path) -> None:
    """LLM emits ``<silence/>`` only — head gate fails AND post-stream
    silence-suppression fires; nothing yielded."""
    agent, gen, recorder, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/>"])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "silence_short_circuit" in kinds


def test_slop_prefix_head_suppresses_via_full_filter(mocker, tmp_path) -> None:
    """Head opens with a banned slop prefix → head_gate rejects the
    speculative emit; the post-stream slop filter is the authority and
    must fire ``slop_suppressed``. No streaming yield happens.
    """
    agent, gen, recorder, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "As an AI assistant, I think the drop is good. ",
                "It really hit hard.",
            ]
        )
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    # Slop suppression — nothing yielded.
    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "slop_suppressed" in kinds


def test_citation_failure_after_head_emits_cancel(mocker, tmp_path) -> None:
    """Head streams (passes head gate), but full text fails citation
    linter → PlaybackQueue.push called with silence-pad PCM + a
    ``streaming_cancel`` event with reason ``citation_failure``."""
    registry = EvidenceRegistry()  # empty — every citation will miss
    agent, gen, recorder, state, _, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "Killer drop coming in hot here. ",
                "That bassline [ev:NOT_IN_REGISTRY@99.9] though.",
            ]
        )
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    # Head was emitted speculatively (passed head_gate — clean prefix).
    assert chunks and chunks[0].startswith("Killer drop coming in hot here.")
    # streaming_cancel event fired with citation_failure reason.
    kinds = [k for k, _ in recorder.events]
    assert "streaming_cancel" in kinds
    cancel_idx = kinds.index("streaming_cancel")
    cancel_fields = recorder.events[cancel_idx][1]
    assert cancel_fields["reason"] == "citation_failure"
    # Silence-pad pushed to playback queue.
    playback.push.assert_called()
    pad_args = playback.push.call_args.args
    assert isinstance(pad_args[0], bytes)
    assert len(pad_args[0]) > 0
    # Silence pad MUST be zero-filled (sanity — no random data).
    assert pad_args[0] == b"\x00" * len(pad_args[0])


def test_citation_failure_no_head_emitted_full_suppress(mocker, tmp_path) -> None:
    """Short response that never hits a boundary; the head never
    emitted; full text fails citation linter → standard strip path; no
    silence-pad needed (nothing to cancel)."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # Single short chunk, no terminal punctuation → no head emit.
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["wow [ev:MISS@0.1] yeah"])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    # Strip path — no chunks yielded, no streaming_cancel event (no head
    # to cancel), citation_strip fires per pre-existing pipeline.
    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    assert "streaming_cancel" not in kinds
    # The strip path may push ack PCM via playback — but never the
    # silence-pad. We only verify streaming_cancel is absent.


def test_citation_pass_no_head_yields_after_stream(mocker, tmp_path) -> None:
    """Clean valid response with no mid-stream boundary → yields after
    stream completes via the legacy emit branch (head never fired)."""
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)
    agent, gen, recorder, state, _, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # No sentence boundary — single short chunk with citation.
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["nice [ev:KICK_SWAP@45.2] yeah"])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    assert "".join(chunks) == "nice [ev:KICK_SWAP@45.2] yeah"
    kinds = [k for k, _ in recorder.events]
    assert "ai_text" in kinds
    assert "streaming_cancel" not in kinds


def test_llm_to_tts_meter_records_first_sentence_yielded(mocker, tmp_path) -> None:
    """When a head is speculatively yielded, the meter records the delta
    and emits an ``llm_to_tts_delta_ms`` event."""
    agent, gen, recorder, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["A speculative head emit here. Tail."])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)
    kinds = [k for k, _ in recorder.events]
    assert "llm_to_tts_delta_ms" in kinds
    fields = dict(recorder.events[kinds.index("llm_to_tts_delta_ms")][1])
    assert "delta_ms" in fields
    assert isinstance(fields["delta_ms"], int)
    assert fields["delta_ms"] >= 0


def test_per_turn_meter_resets(mocker, tmp_path) -> None:
    """Two consecutive turns: each emits its own ``llm_to_tts_delta_ms``
    event with state reset between turns."""
    agent, gen, recorder, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    def _stream(*_a, **_kw):
        return _async_iter(["A speculative head emit here. Tail."])

    gen.aio.models.generate_content_stream = mocker.AsyncMock(side_effect=_stream)
    for _ in range(2):
        ev = Event(type="HEARTBEAT", state=state, extra={})
        agent.set_next_event(ev)
        _drive(agent)
    kinds = [k for k, _ in recorder.events]
    assert kinds.count("llm_to_tts_delta_ms") == 2


def test_pitfall_1_citation_period_no_premature_yield(mocker, tmp_path) -> None:
    """Pitfall 1 — period INSIDE ``[ev:kick@2.5]`` MUST NOT trigger a
    premature head yield. Sentence boundary only fires at the period
    AFTER the bracket closes.
    """
    agent, gen, _, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # Chunk 1 ends in mid-citation — the period inside [ev:kick@2.5] must
    # NOT fire a boundary. The real boundary lives after the closing
    # bracket in chunk 2.
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "Killer drop building up [ev:kick@2.5",
                "] hit hard. Next track up.",
            ]
        )
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)
    full = "".join(chunks)
    assert full == "Killer drop building up [ev:kick@2.5] hit hard. Next track up."
    # Head yielded only when bracket closed + boundary period seen.
    # First chunk (with citation period) must NOT have been emitted alone.
    assert chunks[0] != "Killer drop building up [ev:kick@2.5"


def test_phase_40_three_part_contract_preserved(mocker, tmp_path) -> None:
    """Phase 40 regression — the 3-Part contract holds end-to-end through
    the refactor: ``contents`` list shape unchanged when no mic/lookahead
    is wired (text + 1 audio Part)."""
    agent, gen, _, state = _build_agent_legacy(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Yeah, killer."])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)
    contents = gen.aio.models.generate_content_stream.call_args.kwargs["contents"]
    # 2 elements: text + Part 1 mix. No mic, no lookahead.
    assert len(contents) == 2
