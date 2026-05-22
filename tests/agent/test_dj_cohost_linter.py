# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent.llm_node — Plan 20-01 Task 2 wiring (post-ack-bank).

Pins the 3-kwarg wiring (citation_linter, stripped_rate_tracker,
playback) for the post-stream citation gate. Contract:

- All three None (default) → legacy Phase 18/19 path is byte-identical
  (no linter check, no [unverified] log).
- All three non-None ("wired" mode) → post-stream gate runs after silence/
  slop suppression. Decision ladder: valid → emit + record(False); invalid
  + bypass → emit + record(False) + citation_bypass log; invalid + strip →
  no emit + citation_strip log + record(True). Silence is the strip
  substitute — the pre-recorded ack-bank surface was retired.
- History append on bypass (text was emitted, no-repeat history must
  reflect it) but NOT on strip (no text emitted = nothing to repeat).
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
    """Phase 20 wired construction: linter kwargs supplied + registry.

    (The ack_bank slot was retired with the placeholder OPUS clips —
    citation strips now go silent rather than substituting a
    pre-recorded ack.)
    """
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
    return agent, genai_client, recorder, state, linter, tracker, playback


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
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
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
    # Valid path does not push any audio to the playback queue.
    playback.push.assert_not_called()


# --------------------------------------------------------------------------
# (c) Invalid response strips silently (ack-bank substitution retired)
# --------------------------------------------------------------------------


def test_invalid_response_strips_silently(mocker, tmp_path) -> None:
    """Wired + invalid citation → no chunks yielded, no audio substitute,
    citation_strip logged.

    Pre-2026-05-19 the strip path injected a pre-recorded ack clip from
    AckBank. That surface was retired with the placeholder OPUS clip
    system; silence is the cleanest substitute and matches the persona's
    "if you have NOTHING grounded to say, say NOTHING" rule.
    """
    registry = EvidenceRegistry()  # empty — citation will not match
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
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
    # No audio substitute pushed (silence is the strip substitute).
    playback.push.assert_not_called()
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
# (c2) THE HEADLINE — fabricated [recall:<unregistered>] strips the WHOLE turn
# --------------------------------------------------------------------------


def test_fabricated_recall_strips_turn(mocker, tmp_path) -> None:
    """Phase 65 / RECALL-01 headline poisoning gate — the milestone's anti-slop
    release gate, expressed as a test.

    A past-session signature crosses the trust boundary into the live prompt as
    raw text. If Gemini fabricates a callback citing a ``[recall:<id>]`` whose
    ``record_id`` the registry NEVER wrote (the model invented the id, or echoed
    a lookalike out of a past signature), the whole turn MUST strip — exactly
    like a fabricated ``[ev:UNKNOWN@99.0]`` or ``[key:A:12B]``. A confabulated
    "remember when you…" that never happened is the worst slop class this
    milestone exists to kill.

    Mirrors test_invalid_response_strips_silently: empty registry → the recall
    id is unregistered-by-construction → CitationLinter.check(..., mode="live")
    returns invalid → no chunks yielded + citation_strip logged + tracker
    records the strip.

    The id MUST be a structurally-valid recall body (``f"{session_id}:{seq}"``,
    inner colon) so this is a genuine "registered? no" failure once recall is
    parseable — NOT merely an unparsed token. To make this RED for the RIGHT
    reason (and not a same-now-as-later smoke test that would pass even with the
    poisoning hole open), the reaction ALSO carries a real, registered ``[ev:…]``
    citation. That ev atom is valid, so the ONLY thing that can strip this turn
    is the linter recognizing the fabricated ``[recall:…]`` as an
    unregistered/invalid atom.

    RED until Plans 65-02 (recall joins EVIDENCE_SOURCES + _SOURCE_ALT so
    parse_citations sees it) + 65-04 (registration wiring): TODAY the recall
    token is unparsed, so only the valid ``[ev:…]`` is seen → the turn is EMITTED
    (no strip) → this test FAILS. That failure IS the poisoning hole, made
    visible. Once 65-02 lands sites 1+2, the fabricated recall parses, fails
    existence-only validation (``invalid_atoms``, id named in ``missing``), and
    the WHOLE turn strips. That green transition is the non-negotiable contract.
    """
    # Registry knows the ev atom but NOT the recall id.
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    # A fabricated recall callback riding ALONGSIDE a genuinely valid ev cite.
    fabricated_id = "20260520-2200:999"
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                f"that [ev:KICK_SWAP@45.2] hit — remember when you "
                f"[recall:{fabricated_id}] killed that same drop"
            ]
        )
    )

    ev = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    # The WHOLE turn is silenced — the fabricated callback poisons the otherwise
    # valid reaction. (The valid ev atom cannot rescue an invalid recall atom:
    # response-level binary grounding.)
    assert chunks == []
    playback.push.assert_not_called()
    # citation_strip logged; the fabricated reaction text is captured (silenced).
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    strip_log = next(f for k, f in recorder.events if k == "citation_strip")
    assert f"[recall:{fabricated_id}]" in strip_log["raw_text"]
    # The strip names the fabricated recall id as the missing/invalid atom.
    assert ("recall", fabricated_id) in strip_log["missing"] or [
        "recall",
        fabricated_id,
    ] in strip_log["missing"]
    assert strip_log["reason"] == "invalid_atoms"
    # Tracker recorded the strip; ai_text NOT logged (nothing emitted).
    assert tracker.rate() == 1.0
    assert "ai_text" not in kinds


# --------------------------------------------------------------------------
# (d) No-citations response strips
# --------------------------------------------------------------------------


def test_no_citations_response_strips(mocker, tmp_path) -> None:
    """Wired + uncited reply → strip (no_citations reason)."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
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
    # No ack substitute fires on the strip path post-retirement.
    playback.push.assert_not_called()
    assert tracker.rate() == 1.0


# --------------------------------------------------------------------------
# (e) Bypass emits with [unverified] marker
# --------------------------------------------------------------------------


def test_bypass_emits_with_unverified_marker(mocker, tmp_path, capsys) -> None:
    """Force tracker.should_bypass()→True; invalid response → chunks YIELDED,
    citation_bypass logged, stdout contains '[ai_text:unverified]'."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
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
    # No audio pushed on bypass — we emitted text instead.
    playback.push.assert_not_called()
    # Stdout marker.
    captured = capsys.readouterr().out
    assert "[ai_text:unverified]" in captured


# --------------------------------------------------------------------------
# (f) Strip path with unknown event class — strips silently regardless
# --------------------------------------------------------------------------


def test_strip_path_with_unknown_event_class(mocker, tmp_path) -> None:
    """Unknown ev.type still goes through the strip path; with ack-bank
    retired, the event-class bucket mapping no longer matters — every
    strip is silent, regardless of event type."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["[ev:GHOST@1.0] junk"])
    )

    ev = Event(type="WEIRD", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    assert chunks == []  # strip
    # No audio substitute, no matter the event class.
    playback.push.assert_not_called()
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    strip_log = next(f for k, f in recorder.events if k == "citation_strip")
    # The strip log no longer carries the legacy ack_bucket field.
    assert "ack_bucket" not in strip_log
    # Tracker still recorded the strip.
    assert tracker.rate() == 1.0


# --------------------------------------------------------------------------
# (g) History appended on bypass, NOT on strip
# --------------------------------------------------------------------------


def test_history_appended_on_bypass_not_on_strip(mocker, tmp_path) -> None:
    """_ai_text_history grows on bypass (text was emitted) but NOT on strip
    (no text emitted = nothing to repeat)."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
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
