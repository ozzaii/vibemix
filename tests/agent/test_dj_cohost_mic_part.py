# SPDX-License-Identifier: Apache-2.0
"""Plan 40-01 Task 2 — DJCoHostAgent Part 2 (mic) attachment integration tests.

Pins the 1-Part / 2-Part contract:

* Part count = 2 (text + Part 1 mix audio_wav) when mic_audio_buf is None
  OR KAAN_SPOKE not recent OR mic ring is silent.
* Part count = 3 (text + Part 1 mix + Part 2 mic) when ALL three gates pass:
    1. self._mic_audio_buf is not None
    2. now - state.last_kaan_spoke_at <= MIC_AUDIO_PART_RECENCY_S (4.0s)
    3. mic ring RMS > MIC_AUDIO_PART_PRESENCE_RMS * 32767 (~163 int16)

* mime_type of Part 2 = "audio/wav"; data starts with b"RIFF" (real WAV bytes).

v4 reference (READ-ONLY POC): cohost_v4.py:1791-1813 Part-assembly pattern.
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
from vibemix.audio import AudioBuffer, INPUT_SR_TARGET
from vibemix.state import AICoach, Event, MusicState


# ---------- helpers (mirror tests/agent/test_dj_cohost.py shape) ----------


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
    mocker, tmp_path: Path, mic_audio_buf: AudioBuffer | None
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


# ---------- backward-compat baseline ----------


def test_part_count_2_when_no_mic_audio_buf(mocker, tmp_path) -> None:
    """No mic_audio_buf kwarg → Part count = 2 (text + Part 1 mix audio).

    Plan 4/18/19 backward-compat: existing 9-kwarg DJCoHostAgent
    constructor + 1-Part request must keep working byte-identically.
    """
    agent, gen_client, _, state = _build_agent(mocker, tmp_path, mic_audio_buf=None)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 2
    # Part 1 = audio/wav for the live mix
    assert isinstance(contents[1], types.Part)


def test_part_count_2_when_kaan_spoke_not_recent(mocker, tmp_path) -> None:
    """mic_audio_buf populated with signal but last_kaan_spoke_at = 0.0
    → KAAN_SPOKE-recent gate fails → Part 2 NOT attached → count = 2.
    """
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    _fill_ring_with_sine(mic_audio_buf)

    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf
    )
    state.last_kaan_spoke_at = 0.0  # never spoke
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 2


def test_part_count_2_when_mic_silent(mocker, tmp_path) -> None:
    """mic_audio_buf filled with zeros, last_kaan_spoke_at = now()
    → presence-floor gate fails → Part 2 NOT attached → count = 2.
    """
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    # Push zeros (silence)
    mic_audio_buf.push(np.zeros(INPUT_SR_TARGET * 8, dtype=np.int16))

    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf
    )
    state.last_kaan_spoke_at = time.time()
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    ev = Event(type="KAAN_SPOKE", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    assert len(contents) == 2


# ---------- happy path ----------


def test_part_count_3_when_recent_kaan_with_signal(mocker, tmp_path) -> None:
    """All three gates pass: mic_audio_buf populated with sine AND
    last_kaan_spoke_at within MIC_AUDIO_PART_RECENCY_S AND ring RMS above
    presence floor → Part 2 attached → count = 3.
    """
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    _fill_ring_with_sine(mic_audio_buf)

    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf
    )
    state.last_kaan_spoke_at = time.time()
    # NOTE: do NOT mock snapshot_wav globally — Part 2 path needs a real WAV
    # for the RMS gate. The agent's Part 1 call to snapshot_wav uses the
    # mocked MagicMock(clean_audio_buf), which the function tolerates because
    # snapshot_wav reads buf._sr and buf.snapshot(); we patch only the Part 1
    # call path via side_effect.
    real_snapshot_wav = mocker.patch("vibemix.agent.dj_cohost.snapshot_wav")

    # First call (Part 1, mix) returns fake bytes; second call (Part 2, mic)
    # returns the real WAV from the populated ring — uses the ACTUAL
    # snapshot_wav so the RMS gate sees real signal.
    from vibemix.audio.features import snapshot_wav as _real_snapshot_wav

    def _side(buf, seconds, **kwargs):
        # Identify which buf we got. The clean_audio_buf is a MagicMock; the
        # mic_audio_buf is the real AudioBuffer.
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
        f"expected 3 Parts (text + mix + mic), got {len(contents)}"
    )


def test_mic_part_mime_is_audio_wav(mocker, tmp_path) -> None:
    """In the 3-Part happy path, Part 2 has mime_type='audio/wav' and the
    data starts with b'RIFF' (real WAV envelope from snapshot_wav)."""
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    _fill_ring_with_sine(mic_audio_buf)

    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf
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
    assert len(contents) == 3
    mic_part = contents[2]
    # types.Part exposes inline_data with mime_type + data attributes
    inline = mic_part.inline_data
    assert inline.mime_type == "audio/wav"
    assert inline.data.startswith(b"RIFF"), (
        f"expected RIFF envelope, got {inline.data[:16]!r}"
    )


# ---------- logging surface ----------


def test_mic_part_attached_logs_event(mocker, tmp_path) -> None:
    """When Part 2 is attached, recorder emits a 'mic_part_attached' event
    with duration_s + kaan_spoke_age_s fields. When skipped, emits
    'mic_part_skipped' with a 'reason' field. The structured log surface
    is what coach-loop diagnostics + Settings UI will consume."""
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    _fill_ring_with_sine(mic_audio_buf)

    agent, gen_client, recorder, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=mic_audio_buf
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

    attached = [e for e in recorder.events if e[0] == "mic_part_attached"]
    assert len(attached) == 1
    fields = attached[0][1]
    assert "duration_s" in fields
    assert "kaan_spoke_age_s" in fields
