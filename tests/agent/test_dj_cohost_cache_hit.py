# SPDX-License-Identifier: Apache-2.0
"""Plan 41-02 Task 3 — cache_hit telemetry in DJCoHostAgent.llm_node.

Surfaces ``UsageMetadata.cached_content_token_count`` from every Gemini
stream chunk to ``events.jsonl`` as a ``cache_hit`` event. Locked design:

  - emit ONLY when ``cached_tokens > 0`` (zero = no cache hit; do not log
    noise for cache-miss turns)
  - emit at most once per turn per distinct token-count value (the SDK
    repeats the final UsageMetadata snapshot on multiple chunks)
  - missing ``usage_metadata`` attribute on a chunk → silent no-op (don't
    crash on early stream chunks that pre-date the metadata)
  - recorder write failure → swallow (best-effort; never break the LLM
    stream consumer)

Mirrors the helper pattern in ``test_dj_cohost_3part.py``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.state import AICoach, Event, MusicState


# ---------- helpers ----------


def _async_iter(chunks):
    async def gen():
        for c in chunks:
            yield c

    return gen()


def _mk_chunk(text: str = "", *, cached_tokens: int | None = None,
              has_usage_metadata: bool = True) -> Any:
    """Build a Gemini stream chunk stub.

    text: chunk text payload.
    cached_tokens: if set + has_usage_metadata=True, attaches usage_metadata
      with cached_content_token_count = cached_tokens.
    has_usage_metadata=False: returns a chunk with NO usage_metadata
      attribute at all (early-stream behaviour before the SDK populates it).
    """
    if not has_usage_metadata:
        # Use a plain object so getattr(chunk, "usage_metadata", None) is None.
        chunk = type("Chunk", (), {"text": text})()
        return chunk

    usage = type("Usage", (), {})()
    if cached_tokens is not None:
        usage.cached_content_token_count = cached_tokens
    chunk = type("Chunk", (), {"text": text, "usage_metadata": usage})()
    return chunk


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


def _build_agent(mocker, tmp_path: Path) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
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
        mic_audio_buf=None,
        lookahead=None,
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


def _cache_hit_events(recorder: _FakeRecorder) -> list[dict]:
    return [fields for kind, fields in recorder.events if kind == "cache_hit"]


# ---------- tests ----------


def test_cache_hit_event_logged_when_usage_metadata_present(mocker, tmp_path) -> None:
    """A chunk carrying usage_metadata.cached_content_token_count=1234 →
    exactly one ``cache_hit`` recorder event with that count."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    chunks = [
        _mk_chunk(text="hello ", has_usage_metadata=False),
        _mk_chunk(text="kaan", cached_tokens=1234),
    ]
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(chunks)
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    hits = _cache_hit_events(recorder)
    assert len(hits) == 1, f"expected 1 cache_hit event, got {len(hits)}"
    assert hits[0]["cached_tokens"] == 1234
    assert hits[0]["path"] == "live_coach"
    # cache_state must propagate (will be "disabled" here — no cache wired).
    assert "cache_state" in hits[0]


def test_cache_hit_event_not_logged_when_zero(mocker, tmp_path) -> None:
    """cached_content_token_count = 0 means cache MISS — do not emit a
    cache_hit event (would pollute the log with miss-noise)."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    chunks = [
        _mk_chunk(text="hello ", cached_tokens=0),
        _mk_chunk(text="kaan", cached_tokens=0),
    ]
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(chunks)
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    assert _cache_hit_events(recorder) == [], (
        "cache_hit must NOT be logged when cached_content_token_count == 0"
    )


def test_cache_hit_event_not_logged_when_metadata_absent(mocker, tmp_path) -> None:
    """Chunk without usage_metadata attribute → no event, no error.

    Early stream chunks from the Gemini SDK can arrive before the final
    UsageMetadata snapshot is populated; the telemetry path must tolerate
    that without crashing or emitting spurious events.
    """
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    chunks = [
        _mk_chunk(text="hello ", has_usage_metadata=False),
        _mk_chunk(text=" kaan", has_usage_metadata=False),
    ]
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(chunks)
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    # MUST NOT raise.
    _drive_llm_node(agent)

    assert _cache_hit_events(recorder) == []


def test_cache_hit_event_dedupes_within_turn(mocker, tmp_path) -> None:
    """If the SDK emits the same cached_content_token_count across multiple
    chunks (it does — UsageMetadata is repeated on the final chunks), we
    log it EXACTLY ONCE per turn. Subsequent identical values are skipped;
    a NEW distinct value triggers a fresh emission."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    chunks = [
        _mk_chunk(text="hello ", cached_tokens=500),
        _mk_chunk(text="kaan ", cached_tokens=500),  # dedupe — same value
        _mk_chunk(text="my ", cached_tokens=500),    # dedupe — same value
        _mk_chunk(text="friend", cached_tokens=900),  # new value → emit again
    ]
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(chunks)
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive_llm_node(agent)

    hits = _cache_hit_events(recorder)
    assert len(hits) == 2, (
        f"expected 2 cache_hit events (500 + 900, dedupe of 500), got {len(hits)}: "
        f"{hits!r}"
    )
    assert hits[0]["cached_tokens"] == 500
    assert hits[1]["cached_tokens"] == 900
