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
# (c3) Cross-turn regression — turn N's recall must NOT survive into turn N+1
# --------------------------------------------------------------------------


def test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall(
    mocker, tmp_path
) -> None:
    """Phase 65 review iter-3 BLOCKER regression — every turn rescopes its
    own ``recall`` registrations, so a fabricated ``[recall:<id>]`` that
    matches a PRIOR turn's registration must still strip on a turn whose
    own recall pull came back empty.

    The iter-1 CR-01 fix called ``clear_source("recall")`` only when
    ``recall_moments`` was non-empty for the current turn. That gating
    leaked prior-turn registrations into empty-survivor turns: turn N
    registers ``{A, B}``, turn N+1 has ``recall_moments == []`` so the
    clear is skipped, ``snapshot["recall"]`` still carries ``{A, B}``, and
    Gemini can fabricate ``[recall:A]`` against the stale registration —
    the linter accepts it. The fix moved ``clear_source("recall")`` OUT of
    the conditional so it fires at the top of every recall-enabled turn,
    making ``snapshot["recall"]`` exactly the ids in the current prompt
    (or ``{}`` when there are none).

    Staging:
      * Wire a stub ``recall`` service whose ``get_latest()`` returns
        ``[A, B]`` on the first call (turn N) and ``[]`` on the second
        (turn N+1). ``recall_enabled=True`` so the seam fires.
      * Turn N: drive a valid-cite turn — both A and B land in the registry.
      * Turn N+1: drive with a fabricated ``[recall:<A.record_id>]``
        alongside a real ev cite. The clear-source-unconditional invariant
        means snapshot["recall"] is empty on turn N+1 → the fabricated
        recall is unregistered → the whole turn strips.

    Pre-fix this test would FAIL: turn N+1's snapshot still contains
    ``{A: …, B: …}`` from turn N, so the fabricated ``[recall:A]`` passes
    the existence-only branch and the turn would EMIT. That emit IS the
    cross-turn poisoning hole this fix closes.
    """
    # Stub recall service: returns [A, B] on first get_latest(), [] on second.
    class _StubRecord:
        def __init__(self, record_id: str, signature: str) -> None:
            self.record_id = record_id
            self.signature = signature
            self.session_id = "20260520-2200"
            self.ts = 0.0

    record_a = _StubRecord("20260520-2200:A", "past sig A")
    record_b = _StubRecord("20260520-2200:B", "past sig B")

    class _StubRecall:
        def __init__(self) -> None:
            self._queue = [[record_a, record_b], []]

        def get_latest(self) -> list:
            return self._queue.pop(0) if self._queue else []

        def clear(self, bump_generation: bool = True) -> None:
            pass

    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    linter = CitationLinter()
    tracker = StrippedRateTracker()
    playback = mocker.MagicMock()
    registry = EvidenceRegistry()
    # Pre-seed the ev atom so turn N+1's reaction has a real cite alongside
    # the fabricated recall — the strip can ONLY be caused by the recall.
    registry.write("ev", "KICK_SWAP", 45.2)

    stub_recall = _StubRecall()
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
        recall=stub_recall,
        recall_enabled=True,
    )

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    # Turn N: a legitimate recall turn — A + B both land in the registry.
    gen = genai_client
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                f"that one [ev:KICK_SWAP@45.2] hit — like [recall:{record_a.record_id}] "
                f"and [recall:{record_b.record_id}]"
            ]
        )
    )
    ev1 = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev1)
    _drive(agent)
    # Sanity precondition: A + B did land in the registry on turn N.
    snap_after_n = registry.snapshot()
    assert record_a.record_id in snap_after_n.get("recall", {}), (
        "precondition: turn N registered record A under 'recall'"
    )
    assert record_b.record_id in snap_after_n.get("recall", {}), (
        "precondition: turn N registered record B under 'recall'"
    )

    # Turn N+1: recall_moments comes back EMPTY, but Gemini fabricates a
    # [recall:A] callback referencing the prior-turn registration. Pre-fix
    # the clear_source("recall") gate skipped (because recall_moments==[])
    # and snapshot["recall"] still carried {A, B} → fabricated id passes.
    # Post-fix the clear fires unconditionally → snapshot["recall"] is {}
    # → fabricated id strips the turn.
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                f"remember [recall:{record_a.record_id}] when [ev:KICK_SWAP@45.2] "
                "killed it"
            ]
        )
    )
    ev2 = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev2)
    pre_strip_events = len(recorder.events)
    chunks = _drive(agent)

    # The fabricated recall references a prior-turn id; after the
    # unconditional clear it is unregistered-by-construction → STRIP.
    assert chunks == [], (
        "fabricated [recall:<prior-turn-id>] on an empty-recall turn "
        "must strip the whole turn — the per-turn rescope contract"
    )
    new_kinds = [k for k, _ in recorder.events[pre_strip_events:]]
    assert "citation_strip" in new_kinds, (
        "turn N+1 must log citation_strip for the fabricated recall"
    )
    strip_log = next(
        f for k, f in recorder.events[pre_strip_events:] if k == "citation_strip"
    )
    assert f"[recall:{record_a.record_id}]" in strip_log["raw_text"]
    assert ("recall", record_a.record_id) in strip_log["missing"] or [
        "recall",
        record_a.record_id,
    ] in strip_log["missing"], (
        "strip log must name the fabricated prior-turn recall id"
    )
    # Snapshot invariant: turn N+1's empty recall_moments → no "recall" key
    # (or empty dict under "recall") in the registry snapshot. Pre-fix this
    # would still contain {A, B} → the failing case.
    snap_after_np1 = registry.snapshot()
    assert not snap_after_np1.get("recall"), (
        "turn N+1 (empty recall_moments) must leave snapshot['recall'] empty "
        "— prior-turn registrations must NOT survive into this turn's snapshot"
    )


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


# ---- Phase 66 — coach-tier cooldown tests (COPILOT-02) ----
#
# Pins the coach-tier recall-callback cooldown (>=120s between any two
# recall callbacks + max 1 recall per turn). The cooldown sits ABOVE the
# Phase 65 event-detector cooldowns (which gate whether the event itself
# fires) — the recall-callback cooldown is a SEPARATE concern: the event
# still fires (live reaction still happens), only the recall-callback
# fragment is suppressed.
#
# Wiring contract (Plan 02 Task 1 will add):
#   - Module constant RECALL_CALLBACK_COOLDOWN_S: float = 120.0 in
#     src/vibemix/agent/dj_cohost.py (module scope).
#   - Per-agent self._last_recall_callback_at: float = 0.0 field on
#     DJCoHostAgent (co-located with _invoke_counter / _ai_text_history).
#   - Cooldown gate in llm_node AFTER recall.get_latest() pull and BEFORE
#     the registry write loop: if active, set recall_moments = [].
#   - Cooldown ARM at EMIT path (after the citation linter passes + chunks
#     are emitted + the chip strip is built and emit returns without
#     exception) — strict "REACHED the audience" semantic per CONTEXT.md
#     Area 1 Q3 + RESEARCH §Pitfall 2 + §Open Q5.
#
# Per-test-body imports of RECALL_CALLBACK_COOLDOWN_S wrapped in
# pytest.fail-on-ImportError keep collection clean while the symbol does
# not yet exist (Wave 0 contract).


def test_cooldown_suppresses_back_to_back_recalls_COPILOT02(mocker, tmp_path) -> None:
    """COPILOT-02 — two recall-eligible TRACK_CHANGE turns within the 120s
    cooldown window → turn N emits a recall callback (chip surfaces); turn
    N+1 has non-empty survivors from the stub but the cooldown is active
    so NO recall callback is emitted on turn N+1 (no [recall:<id>] token
    in the reaction → no recall chip).

    Drives two consecutive turns with the wall clock mocked: t=100.0 then
    t=180.0 (80s gap — well inside the 120s cooldown window).

    RED reason: RECALL_CALLBACK_COOLDOWN_S module constant + the
    self._last_recall_callback_at field + the cooldown gate + the
    emit-success-arm all do not exist yet. Plan 02 Task 1 must add them
    together (they form a single coherent unit).
    """
    try:
        from vibemix.agent.dj_cohost import RECALL_CALLBACK_COOLDOWN_S  # noqa: F401
    except ImportError:
        import pytest

        pytest.fail(
            "RECALL_CALLBACK_COOLDOWN_S missing from vibemix.agent.dj_cohost "
            "— Plan 02 Task 1 must add it (COPILOT-02)"
        )

    # Stub recall service that hands out non-empty survivors on BOTH turns
    # (so the only thing that can suppress turn N+1 is the cooldown gate).
    class _StubRecord:
        def __init__(self, record_id: str, signature: str) -> None:
            self.record_id = record_id
            self.signature = signature
            self.session_id = "20260520-2200"
            self.ts = 0.0

    record_a = _StubRecord("20260520-2200:A", "past sig A")
    record_b = _StubRecord("20260520-2200:B", "past sig B")

    class _StubRecall:
        def __init__(self) -> None:
            self._queue = [[record_a], [record_b]]

        def get_latest(self) -> list:
            return self._queue.pop(0) if self._queue else []

        def clear(self, bump_generation: bool = True) -> None:
            pass

    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    linter = CitationLinter()
    tracker = StrippedRateTracker()
    playback = mocker.MagicMock()
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)

    stub_recall = _StubRecall()
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
        recall=stub_recall,
        recall_enabled=True,
    )

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")

    # Wall clock control — t=100.0 on turn N, t=180.0 on turn N+1 (80s gap).
    clock = {"t": 100.0}
    mocker.patch("vibemix.agent.dj_cohost.time.time", side_effect=lambda: clock["t"])

    # Turn N: model emits a valid recall callback. After emit, the cooldown
    # MUST arm (self._last_recall_callback_at = 100.0).
    gen = genai_client
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                f"that [ev:KICK_SWAP@45.2] hit — like "
                f"[recall:{record_a.record_id}] last set"
            ]
        )
    )
    ev1 = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev1)
    chunks_n = _drive(agent)

    assert chunks_n, "turn N must emit (chunks non-empty)"
    assert f"[recall:{record_a.record_id}]" in chunks_n[0], (
        "turn N must carry the recall callback so the cooldown arms"
    )

    # Advance the clock to t=180.0 (inside the 120s window).
    clock["t"] = 180.0

    # Turn N+1: survivors still non-empty (stub returns [record_b]) BUT the
    # cooldown is active. The cooldown gate must drop recall_moments to []
    # so no recall fragment is built, no [recall:<id>] token can land, no
    # chip can surface. Even if the model TRIED to emit one (we simulate
    # that — the agent's cooldown is what prevents Gemini from being
    # invited to emit one in the first place), the prompt would not carry
    # the fragment instruction.
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                # No recall token — simulating the post-cooldown turn where
                # the prompt did not invite a recall callback.
                "that [ev:KICK_SWAP@45.2] hit — clean groove"
            ]
        )
    )
    ev2 = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev2)
    chunks_np1 = _drive(agent)

    assert chunks_np1, "turn N+1 must still emit (event still fires)"
    # No recall callback survives the cooldown.
    joined_np1 = " ".join(chunks_np1)
    assert "[recall:" not in joined_np1, (
        "turn N+1 must NOT carry a recall callback (cooldown active at 80s "
        "< RECALL_CALLBACK_COOLDOWN_S=120s)"
    )
    # The registry snapshot's recall section must be EMPTY on turn N+1
    # (the cooldown gate sets recall_moments=[] BEFORE the registry write
    # loop runs, so nothing is registered for this turn).
    snap_after_np1 = registry.snapshot()
    assert not snap_after_np1.get("recall"), (
        "turn N+1 cooldown gate must skip the recall registration loop "
        "(snapshot['recall'] is empty)"
    )


def test_max_one_recall_per_turn_COPILOT02(mocker, tmp_path) -> None:
    """COPILOT-02 — a single turn with MULTIPLE survivors from
    recall.get_latest() must produce a prompt that interpolates ONLY ONE
    record_id (the strongest) into the fragment portion. The weaker
    survivors still appear in the Phase 65 evidence_line PAST-tense block
    but are NEVER interpolated into the fragment instruction.

    Structural property = the fragment template's "cite EXACTLY ONCE"
    instruction + the registry strict-subset invariant + the single-emit
    stream per turn.

    Uses mocker.patch.object(AICoach, "build_prompt", wraps=...) to
    CAPTURE the kwargs the agent passes to build_prompt and inspect the
    prompt body it returns — this is the most direct way to assert the
    prompt-body invariant without round-tripping through Gemini.

    RED reason: the agent does not currently thread the strongest-only
    structural cap (the helper does not exist; build_prompt ignores
    recall_moments until Plan 02 wires the integration). Today the test
    fails because no fragment is built at all → the prompt body does not
    contain the strongest survivor's record_id in the fragment portion →
    the assertion that the strongest IS present fails.
    """
    try:
        from vibemix.agent.dj_cohost import RECALL_CALLBACK_COOLDOWN_S  # noqa: F401
    except ImportError:
        import pytest

        pytest.fail(
            "RECALL_CALLBACK_COOLDOWN_S missing from vibemix.agent.dj_cohost "
            "— Plan 02 Task 1 must add it (COPILOT-02)"
        )

    class _StubRecord:
        def __init__(self, record_id: str, signature: str) -> None:
            self.record_id = record_id
            self.signature = signature
            self.session_id = "20260520-2200"
            self.ts = 0.0

    record_a = _StubRecord("20260520-2200:A", "past sig A — strongest")
    record_b = _StubRecord("20260520-2200:B", "past sig B")
    record_c = _StubRecord("20260520-2200:C", "past sig C")

    class _StubRecall:
        def __init__(self) -> None:
            self._queue = [[record_a, record_b, record_c]]

        def get_latest(self) -> list:
            return self._queue.pop(0) if self._queue else []

        def clear(self, bump_generation: bool = True) -> None:
            pass

    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    linter = CitationLinter()
    tracker = StrippedRateTracker()
    playback = mocker.MagicMock()
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)

    stub_recall = _StubRecall()
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
        recall=stub_recall,
        recall_enabled=True,
    )

    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")

    # Capture the prompt string the agent built — we inspect the body to
    # assert the strongest-only structural cap.
    captured: dict = {"prompt": None}

    real_build_prompt = AICoach.build_prompt

    def _spy_build_prompt(ev, **kwargs):
        out = real_build_prompt(ev, **kwargs)
        captured["prompt"] = out
        return out

    mocker.patch.object(AICoach, "build_prompt", side_effect=_spy_build_prompt)

    gen = genai_client
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [f"that [ev:KICK_SWAP@45.2] hit — like [recall:{record_a.record_id}]"]
        )
    )
    ev1 = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev1)
    _drive(agent)

    prompt = captured["prompt"]
    assert prompt is not None, "build_prompt was not invoked"

    # The PAST-tense evidence_line block contains all three survivors
    # (Phase 65 contract — already green, pinned here as defense in depth).
    assert record_a.record_id in prompt
    assert record_b.record_id in prompt
    assert record_c.record_id in prompt

    # Locate the fragment portion — everything AFTER the unique transition
    # marker "in the live audio" (the fragment unique substring locked
    # at Wave 0; see tests/state/test_coach.py module comment).
    assert "in the live audio" in prompt, (
        "transition fragment marker missing from the built prompt — "
        "Plan 02 must append the fragment for non-empty survivors"
    )
    fragment_start = prompt.index("in the live audio")
    fragment_portion = prompt[fragment_start:]

    # Strongest record_id is the ONE-AND-ONLY id interpolated into the
    # fragment template. The TRANSITION_SHAPE_RECALL_FRAGMENT_TPL has TWO
    # ``{record_id}`` placeholders — both are filled with the SAME id
    # (the instruction "citing exactly [recall:<id>]" + the rule "cite
    # [recall:<id>] EXACTLY ONCE" are both reinforced with the same id).
    # So the structural property is "only the strongest id appears" — the
    # repeat-count is a property of the TEMPLATE (deterministic), not of
    # the structural cap. Plan 02 Task 2 fix-up: the Wave 0 assertion
    # ``count == 1`` was overly strict; the correct contract is
    # ``count >= 1 AND no other survivor's record_id is present``.
    assert fragment_portion.count(record_a.record_id) >= 1, (
        f"strongest record_id must appear in fragment portion at least once; "
        f"got {fragment_portion.count(record_a.record_id)}"
    )
    # Weaker survivors do NOT appear in the fragment portion (the real
    # structural max-1-per-turn cap: only ONE record_id — the strongest
    # — is named; weaker survivors stay in the upstream evidence_line
    # PAST-tense block but never in the fragment instruction).
    assert record_b.record_id not in fragment_portion, (
        f"record_b ({record_b.record_id}) leaked into the fragment portion"
    )
    assert record_c.record_id not in fragment_portion, (
        f"record_c ({record_c.record_id}) leaked into the fragment portion"
    )
