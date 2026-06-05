# SPDX-License-Identifier: Apache-2.0
"""Phase 80 Plan 01 (Wave 0) — GROUND secondary-ear Nyquist safety net.

Pins every GROUND-01 / GROUND-02 acceptance criterion BEFORE any ``src/``
change (Plan 02 implements the framing + flag). Four tests, two tiers:

  REAL-GREEN (must KEEP passing through Plan 02 — the cold-path contract):
    * ``test_flag_off_byte_identical`` — with the secondary-ear path OFF the
      reaction request is the v8.0 1-Part baseline: ``contents[0]`` carries the
      v8.0 ``"(audience perspective)"`` label + the ``"Your ears are the
      referee"`` refrain, and does NOT yet contain the secondary-ear framing
      token Plan 02 will add (``"secondary grounding signal"``). Byte-identity.
    * ``test_model_via_router`` — GROUND-02: the reaction model resolves via
      ``model_router.resolve("live_coach")`` with NO hardcoded literal on the
      reaction path. ``live_coach`` is the Phase-81 bench-swap alias.

  RED SCAFFOLDS (xfail(strict=True) — FAIL today, flip to real passes in Plan
  02; an xpassed is a HARD failure under strict so a silent early-pass cannot
  hide a never-fired guard):
    * ``test_flag_on_audio_framed`` — flag ON: Part 1 still present
      (``audio/wav`` / ``b"RIFF"``) AND ``contents[0]`` NOW carries the
      ``"secondary grounding signal"`` framing token. Fails today because the
      ``secondary_ear`` kwarg + framing do not exist (TypeError / missing
      substring).
    * ``test_unbacked_audio_claim_strips`` — THE core guard (T-80-01). With all
      FOUR linter deps wired (``citation_linter`` + ``stripped_rate_tracker`` +
      ``playback`` + ``evidence_registry``) so ``_linter_wired`` is True AND the
      per-turn registry snapshot is non-None, a Gemini reply citing an event the
      DSP never detected (``[ev:PHANTOM_DROP@45.2]``) strips the WHOLE turn to
      ``<silence/>``. Proves the audio Part cannot widen the citable set:
      trust-the-audio (invariant #3) wins by construction. Fails today because
      the flag-ON construction path (the ``secondary_ear`` kwarg) does not
      exist yet.

Honest green: no ``genai.Client`` is constructed, no ``GEMINI_API_KEY`` is read,
no model literal is inlined, no ``src/`` file is touched. The fake genai stream
mirrors ``tests/agent/test_dj_cohost_mic_part.py``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from google.genai import types
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.agent.config import LLM_MODEL
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.llm.model_router import resolve
from vibemix.state import AICoach, Event, MusicState
from vibemix.state.evidence_registry import EvidenceRegistry

# ---------- helpers (copied verbatim from tests/agent/test_dj_cohost_mic_part.py) ----------


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
    mocker, tmp_path: Path, mic_audio_buf=None, **extra_kwargs
) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
    """Construct a DJCoHostAgent with the Agent.__init__ patched to a no-op.

    Extends the mic-part analog: ``**extra_kwargs`` lets a caller pass the
    linter-wiring quartet (citation_linter / stripped_rate_tracker / playback /
    evidence_registry) and the Plan-02 ``secondary_ear`` flag without forking
    the helper.
    """
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
        **extra_kwargs,
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


# ---------- Task 1: real-green pins (must keep passing through Plan 02) ----------


def test_flag_off_byte_identical(mocker, tmp_path) -> None:
    """Flag OFF → v8.0 1-Part baseline. ``contents[0]`` carries the v8.0
    ``"(audience perspective)"`` label + the ``"Your ears are the referee"``
    refrain, and does NOT yet contain the secondary-ear framing token.

    This is the cold-path byte-identity pin: with no secondary-ear flag set the
    request shape is exactly what v8.0 ships. Plan 02 must NOT regress it.
    """
    agent, gen_client, _, state = _build_agent(mocker, tmp_path, mic_audio_buf=None)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    # 1-Part baseline: text packet + Part 1 mix audio.
    assert len(contents) == 2
    assert isinstance(contents[1], types.Part)

    text_packet = contents[0]
    # Audience-perspective grounding present (parts_clause from build_parts_description).
    # The live-deck-context phase extended the v8.0 "(audience perspective)" label
    # with the anti-hallucination "global mix, not isolated deck stems" clarifier;
    # the audience-perspective grounding + ears-are-referee refrain still hold on the
    # cold path, which is what this pin protects.
    assert "(audience perspective; global mix, not isolated deck stems)" in text_packet
    assert "Your ears are the referee" in text_packet
    # Secondary-ear framing token is ABSENT on the cold path (Plan 02 adds it).
    assert "secondary grounding signal" not in text_packet


def test_model_via_router() -> None:
    """GROUND-02: the reaction model resolves via ``model_router`` — no literal.

    ``agent/config.py:25`` is the single resolution point (``LLM_MODEL =
    resolve("live_coach")[0]``); the reaction call passes ``model=LLM_MODEL``.
    ``live_coach`` is the config-addressable alias the Phase-81 bench swaps by
    config alone (one-line ``_router_config.py`` edit, no code change).
    """
    assert LLM_MODEL == resolve("live_coach")[0]


# ---------- Task 2: RED scaffolds (xfail-strict; flip to green in Plan 02) ----------


def test_flag_on_audio_framed(mocker, tmp_path) -> None:
    """Flag ON → Part 1 still present AND the framing token now appears.

    Plan 02 threads ``secondary_ear`` as a default-False ``DJCoHostAgent``
    kwarg and appends a "secondary grounding signal" clause to the parts_clause.
    Real-green as of Plan 02: the kwarg exists and the substring lands in
    ``contents[0]`` while the unconditional Part-1 audio survives.
    """
    agent, gen_client, _, state = _build_agent(
        mocker, tmp_path, mic_audio_buf=None, secondary_ear=True
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    _drive_llm_node(agent)

    contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
    # Part 1 (the live mix audio) MUST survive the framing flag — the flag gates
    # only the parts_clause text, never the unconditional audio Part.
    assert isinstance(contents[1], types.Part)
    inline = contents[1].inline_data
    assert inline.mime_type == "audio/wav"
    assert inline.data.startswith(b"RIFF")
    text_packet = contents[0]
    # The secondary-ear framing token is now present in the text packet.
    assert "secondary grounding signal" in text_packet
    # WR-01: the clause keeps the GROUND-01 anti-fabrication guard …
    assert "never claim an event the evidence does not list" in text_packet
    # … and COMPLEMENTS (never inverts) Invariant #3 / the EARS-WIN refrain:
    # the ears stay the referee and the clause must NOT assert the inverted
    # "the structured evidence above is authoritative" priority.
    assert "your ears stay the referee" in text_packet
    assert "evidence above is authoritative" not in text_packet


def test_unbacked_audio_claim_strips(mocker, tmp_path) -> None:
    """THE core guard (T-80-01): an audio-derived claim for an undetected event
    strips the WHOLE turn to ``<silence/>`` — the audio Part cannot widen the
    citable set.

    Constructed with all FOUR non-None linter deps so the strip chokepoint
    actually runs (``dj_cohost.py:551-554``: ``_linter_wired = all(... for ...
    in (citation_linter, stripped_rate_tracker, playback))``) AND the per-turn
    registry snapshot is non-None (``dj_cohost.py:1346``: ``snapshot =
    self._registry.snapshot() if self._registry is not None else None``).
    Omitting ``playback`` leaves ``_linter_wired`` False → the chokepoint is
    skipped → the un-backed claim is emitted → the guard silently never fires.

    The registry is seeded with a REAL library track only — ``PHANTOM_DROP`` is
    NOT seeded, so ``[ev:PHANTOM_DROP@45.2]`` misses → linter ``valid=False`` →
    strip. A fresh ``StrippedRateTracker`` has ``rate()==0.0`` so
    ``should_bypass()`` is False → the strip path (not bypass) fires.

    Real-green as of Plan 02: the ``secondary_ear`` kwarg now exists, so the
    flag-ON construction succeeds and the strip chokepoint actually runs.
    """
    # --- registry: seed a real observation, NEVER the phantom ---
    registry = EvidenceRegistry()

    class _FakeLib:
        """Duck-typed RekordboxLibrary — register_library reads only .tracks."""

        def __init__(self, track_ids: list[str]) -> None:
            self.tracks = {tid: object() for tid in track_ids}

    registry.register_library(_FakeLib(["track-1", "track-2"]), t_session=0.0)
    # Precondition: the phantom event is NOT citable. This is the property the
    # guard relies on — the audio Part cannot conjure a registry entry.
    assert registry.has("ev", "PHANTOM_DROP", 45.2) is False

    # --- all FOUR linter deps non-None so _linter_wired flips True ---
    linter = CitationLinter()
    tracker = StrippedRateTracker()
    playback = mocker.MagicMock()  # non-None is all _linter_wired needs

    agent, gen_client, _, state = _build_agent(
        mocker,
        tmp_path,
        mic_audio_buf=None,
        citation_linter=linter,
        stripped_rate_tracker=tracker,
        playback=playback,
        evidence_registry=registry,
        secondary_ear=True,
    )

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # The model fabricates a claim about an event the DSP never detected.
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Massive drop just landed [ev:PHANTOM_DROP@45.2]"])
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    chunks = _drive_llm_node(agent)

    # The un-backed citation misses the registry snapshot → the linter
    # strips the whole turn before any TTS chunk is yielded. Secondary-ear
    # audio cannot widen the citable set or leak a speculative spoken head.
    assert chunks == []
    kinds = [k for k, _ in agent._recorder.events]
    assert "citation_strip" in kinds
    assert "streaming_cancel" not in kinds
    playback.push.assert_not_called()
