# SPDX-License-Identifier: Apache-2.0
"""Plan 40-03 Task 2 — DJCoHostAgent lookahead Part 3 integration tests.

Pins the 4 Part-count scenarios per locked CONTEXT.md Q1 (3-Part additive)
plus the exception-safety guarantee that lookahead failures never crash
``llm_node``:

  scenario              | mic | lookahead | parts | notes
  ----------------------|-----|-----------|-------|-------------------------------------
  1_no_mic_no_lookahead |  F  |    F      |  1+1  | text + P1 mix
  2_lookahead_only      |  F  |    T      |  1+2  | text + P1 mix + P2 lookahead; "NOT YET HEARD" in prompt
  2_mic_only            |  T  |    F      |  1+2  | text + P1 mix + P2 mic; "NOT YET HEARD" NOT in prompt
  3_mic_and_lookahead   |  T  |    T      |  1+3  | text + P1 mix + P2 mic + P3 lookahead
  lookahead_exception   |  F  |  raises   |  1+1  | provider.snapshot_wav crashes → 1-Part fallback

Plus: recorder events ``lookahead_part_attached`` / ``lookahead_part_skipped``
fire on the respective paths.

Reference: 40-03-PLAN.md ``<tasks>`` block (Task 2 behavior), Plan 40-01
SUMMARY's Part 2 attach point at dj_cohost.py:417 (we append Part 3
immediately after that block).
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import numpy as np
from google.genai import types
from livekit.agents import Agent

from tests.audio.conftest import int16_sine
from vibemix.agent import DJCoHostAgent
from vibemix.audio import INPUT_SR_TARGET, AudioBuffer
from vibemix.audio.lookahead import LookaheadProvider
from vibemix.state import AICoach, Event, MusicState


# ---------- helpers (mirror tests/agent/test_dj_cohost_mic_part.py) ----------


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
    mocker,
    tmp_path: Path,
    mic_audio_buf: AudioBuffer | None,
    lookahead: LookaheadProvider | None,
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
        mic_audio_buf=mic_audio_buf,
        lookahead=lookahead,
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


def _fill_ring_with_sine(buf: AudioBuffer) -> None:
    """Push 8s of 1kHz int16 sine into the ring so snapshot_wav comes back
    with real signal (RMS well above MIC_AUDIO_PART_PRESENCE_RMS * 32767)."""
    samples = int16_sine(freq_hz=1000.0, duration_sec=8.0, sample_rate=INPUT_SR_TARGET)
    buf.push(samples)


def _build_lookahead_mock(wav: bytes | None, meta: dict | None = None) -> LookaheadProvider:
    """Build a real LookaheadProvider whose snapshot_wav is monkeypatched to
    return a deterministic ``(wav, meta)`` tuple. Per Plan 40-03 spec the
    provider is real (so __init__ wiring is exercised) but snapshot_wav is
    swapped on the instance — no subprocess invocations during tests.
    """
    provider = LookaheadProvider()
    payload_meta = meta if meta is not None else (
        {"ok": True, "reason": "ok", "title": "fixture", "file": "/tmp/x.mp3"}
        if wav is not None
        else {"ok": False, "reason": "no file", "title": "fixture", "file": None}
    )
    provider.snapshot_wav = lambda: (wav, payload_meta)
    return provider


# ---------- 4 Part-count scenarios ----------


def test_part_count_1_no_mic_no_lookahead(mocker, tmp_path) -> None:
    """mic_audio_buf=None AND lookahead=None → Part count = 2 (text + P1 mix).

    Backward-compat with Plan 40-01's mic_audio_buf=None default + this
    plan's new lookahead=None default. Both Part 2 and Part 3 paths short
    out at the instance-presence gate.
    """
    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=None, lookahead=None
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 2, f"expected 2 elements (text + P1 mix), got {len(contents)}"
    # Text prompt suffix must NOT mention "NOT YET HEARD" or "P2".
    text = contents[0]
    assert "NOT YET HEARD" not in text
    assert "P2" not in text


def test_part_count_2_lookahead_only(mocker, tmp_path) -> None:
    """mic_audio_buf=None, lookahead returns bytes → Part count = 3
    (text + P1 mix + P2 lookahead). Per locked Q2, when no mic is in the
    way the lookahead occupies the P2 slot — slot numbering stays
    contiguous and the "NOT YET HEARD BY AUDIENCE" label refers to P2.
    """
    lookahead = _build_lookahead_mock(wav=b"RIFFFAKELOOKAHEAD")
    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=None, lookahead=lookahead
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 3, (
        f"expected 3 elements (text + P1 mix + P2 lookahead), got {len(contents)}"
    )
    text = contents[0]
    assert "NOT YET HEARD BY AUDIENCE" in text, (
        f"locked Q2 label missing from prompt suffix: ...{text[-200:]!r}"
    )
    # Lookahead Part is at index 2 (after text + Part 1); mime audio/wav.
    lookahead_part = contents[2]
    assert isinstance(lookahead_part, types.Part)
    assert lookahead_part.inline_data.mime_type == "audio/wav"
    assert lookahead_part.inline_data.data == b"RIFFFAKELOOKAHEAD"


def test_part_count_2_mic_only(mocker, tmp_path) -> None:
    """mic ring populated with signal, lookahead returns None (no file
    match) → Part count = 3 (text + P1 mix + P2 mic). Prompt suffix
    mentions P2 but NOT "NOT YET HEARD" (no lookahead present).
    """
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    _fill_ring_with_sine(mic_audio_buf)
    lookahead = _build_lookahead_mock(wav=None, meta={"ok": False, "reason": "no file"})

    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf, lookahead=lookahead
    )
    state.last_kaan_spoke_at = time.time()

    from vibemix.audio.features import snapshot_wav as _real_snapshot_wav

    real_snapshot_wav = mocker.patch("vibemix.agent.dj_cohost.snapshot_wav")

    def _side(buf, seconds, **kwargs):
        if isinstance(buf, AudioBuffer):
            return _real_snapshot_wav(buf, seconds, **kwargs)
        return b"RIFFFAKEWAVMIX"

    real_snapshot_wav.side_effect = _side

    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="KAAN_SPOKE", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 3, (
        f"expected 3 elements (text + P1 mix + P2 mic), got {len(contents)}"
    )
    text = contents[0]
    assert "P2 =" in text
    assert "NOT YET HEARD" not in text, (
        f"NOT YET HEARD label leaked into mic-only path: ...{text[-200:]!r}"
    )


def test_part_count_3_mic_and_lookahead(mocker, tmp_path) -> None:
    """All three signals present → Part count = 4 (text + P1 mix + P2 mic
    + P3 lookahead). Prompt suffix MUST contain both "P3 =" and "NOT YET
    HEARD BY AUDIENCE".
    """
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    _fill_ring_with_sine(mic_audio_buf)
    lookahead = _build_lookahead_mock(wav=b"RIFFFAKELOOKAHEAD")

    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf, lookahead=lookahead
    )
    state.last_kaan_spoke_at = time.time()

    from vibemix.audio.features import snapshot_wav as _real_snapshot_wav

    real_snapshot_wav = mocker.patch("vibemix.agent.dj_cohost.snapshot_wav")

    def _side(buf, seconds, **kwargs):
        if isinstance(buf, AudioBuffer):
            return _real_snapshot_wav(buf, seconds, **kwargs)
        return b"RIFFFAKEWAVMIX"

    real_snapshot_wav.side_effect = _side

    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="KAAN_SPOKE", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 4, (
        f"expected 4 elements (text + P1 + P2 + P3), got {len(contents)}"
    )
    text = contents[0]
    assert "P3 =" in text, f"P3 label missing from prompt: ...{text[-200:]!r}"
    assert "NOT YET HEARD BY AUDIENCE" in text, (
        f"locked Q2 label missing from 3-Part prompt: ...{text[-200:]!r}"
    )
    # Part 3 is the lookahead WAV bytes.
    lookahead_part = contents[3]
    assert isinstance(lookahead_part, types.Part)
    assert lookahead_part.inline_data.mime_type == "audio/wav"
    assert lookahead_part.inline_data.data == b"RIFFFAKELOOKAHEAD"


# ---------- exception safety ----------


def test_lookahead_exception_does_not_crash_llm_node(mocker, tmp_path) -> None:
    """``self._lookahead.snapshot_wav`` raises → llm_node falls back to
    1-Part (text + P1 mix) AND records ``lookahead_part_skipped`` with a
    reason mentioning the exception. T-40-03-02 DoS mitigation.
    """
    lookahead = LookaheadProvider()

    def _boom() -> tuple[bytes | None, dict]:
        raise RuntimeError("boom")

    lookahead.snapshot_wav = _boom

    agent, gen_client, recorder, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=None, lookahead=lookahead
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    # MUST NOT raise — the try/except wrapper in llm_node catches the
    # provider exception and falls back to the (None, meta) contract.
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 2, (
        f"expected 2 elements (1-Part fallback after exception), got {len(contents)}"
    )
    # Recorder should carry a lookahead_part_skipped event with reason
    # mentioning the exception. The reason format is implementation-
    # defined but must reference "exception" or "boom" (so the field is
    # diagnosable in events.jsonl).
    skipped = [e for e in recorder.events if e[0] == "lookahead_part_skipped"]
    assert len(skipped) == 1, (
        f"expected one lookahead_part_skipped event, got {len(skipped)}: {recorder.events!r}"
    )
    reason = skipped[0][1].get("reason", "")
    assert "boom" in reason or "exception" in reason.lower(), (
        f"expected reason to mention exception/boom, got {reason!r}"
    )


# ---------- recorder event surface ----------


def test_lookahead_part_attached_logs_event(mocker, tmp_path) -> None:
    """When lookahead bytes attached, recorder emits ``lookahead_part_attached``
    with at least a ``bytes`` field. When skipped (None bytes), emits
    ``lookahead_part_skipped`` with a ``reason`` field. Mirrors the
    mic_part_* pattern established in Plan 40-01 — coach-loop diagnostics
    and Settings → Diagnostics consume both pairs uniformly.
    """
    lookahead = _build_lookahead_mock(
        wav=b"RIFFFAKELOOKAHEAD",
        meta={"ok": True, "reason": "ok", "title": "FixtureTrack", "duration_sec": 18.0},
    )
    agent, gen_client, recorder, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=None, lookahead=lookahead
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    attached = [e for e in recorder.events if e[0] == "lookahead_part_attached"]
    assert len(attached) == 1, f"events: {recorder.events!r}"
    fields = attached[0][1]
    assert "bytes" in fields
    assert fields["bytes"] == len(b"RIFFFAKELOOKAHEAD")
