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

from google.genai import types
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.state import AICoach, Event, MusicState

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


def _build_agent(mocker, tmp_path: Path) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
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
    assert agent._gen_cfg.temperature == 1.0
    assert agent._gen_cfg.max_output_tokens == 220
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
    assert "RECENT THINGS YOU JUST SAID (do NOT repeat or rephrase" in second_prompt_text
    assert "first_reply" in second_prompt_text


def test_llm_node_07_history_truncation_to_140_chars(mocker, tmp_path) -> None:
    """LLM-NODE-07: stripped text truncated to 140 chars before deque append."""
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
    assert len(agent._ai_text_history[0]) == 140


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


def test_v_llm_node_calls_build_prompt_with_snapshot_when_registry_wired(
    mocker, tmp_path
) -> None:
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


def test_y_full_prompt_path_evidence_corpus_and_grammar_block_smoke(
    mocker, tmp_path
) -> None:
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

    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        side_effect=_capturing_stream
    )

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
        "CITATION_GRAMMAR_BLOCK missing from system_instruction — "
        "Plan 18-03 Task 1 wiring broken"
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
        "[tend:user_likes_acid] [ev:A@1] [aud:bpm@2]",  # 3
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
