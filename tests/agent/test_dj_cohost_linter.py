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

from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState
from vibemix.state.deck_state import DeckState, DeckTrack

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


def _deck(title: str, *, camelot: str = "8A") -> DeckTrack:
    return DeckTrack(
        title=title,
        track_id=title.lower().replace(" ", "-"),
        bpm=128.0,
        camelot=camelot,
        confidence=0.8,
        source="rekordbox_xml",
    )


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

    assert chunks == ["that drop was clean"]
    kinds = [k for k, _ in recorder.events]
    assert "ai_text" in kinds
    assert next(f for k, f in recorder.events if k == "ai_text")["text"] == (
        "that drop was clean"
    )
    ai_row = next(f for k, f in recorder.events if k == "ai_message")
    assert ai_row["message"] == "that drop was clean"
    assert ai_row["extra"]["spoken_response_chars"] == len("that drop was clean")
    assert (
        Path(ai_row["artifacts"]["session_response_path"]).read_text(encoding="utf-8")
        == "that drop [ev:KICK_SWAP@45.2] was clean"
    )
    assert "[ev:" not in agent._ai_text_history[0]
    assert "citation_strip" not in kinds
    assert "citation_bypass" not in kinds
    # Tracker was told the response was NOT stripped.
    assert tracker.rate() == 0.0
    # Valid path does not push any audio to the playback queue.
    playback.push.assert_not_called()


def test_live_claim_guard_corrects_single_deck_transition_claim(mocker, tmp_path) -> None:
    """Wired path: one resolved deck blocks all multi-deck outcome synonyms."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["That was a great transition into the drop."])
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    chunks = _drive(agent)

    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "live_claim_guard" in kinds
    assert "ai_text" not in kinds
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "strip"
    assert "second_deck=independent_source_required" in guard_log["summary"]
    assert "citation_strip" not in kinds
    assert tracker.rate() == 1.0
    playback.push.assert_not_called()


def test_live_claim_guard_strips_cited_phase_advice_without_move_proof(mocker, tmp_path) -> None:
    """A valid PHASE citation is not permission to coach without move/deck proof."""
    registry = EvidenceRegistry()
    registry.write("ev", "PHASE", 22.4)
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = True
    state.audible_deck = "none"
    state.audible_track = None
    state.audible_track_confidence = 0.0
    state.recent_moves = []
    state.deck_state = DeckState(decks={})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "That low end was heavy ",
                "but the build released on the 3 — try the 1 next time ",
                "to let that vocal sample find its pocket [ev:PHASE@22.4].",
            ]
        )
    )

    agent.set_next_event(
        Event(type="PHASE", state=state, extra={"prev_phase": "build", "new_phase": "drop"})
    )
    chunks = _drive(agent)

    assert chunks == []
    kinds = [kind for kind, _ in recorder.events]
    assert "ai_text" not in kinds
    assert "citation_strip" not in kinds
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "strip"
    assert guard_log["policy"] == "coaching_advice_not_grounded"
    assert guard_log["reason"] == "advice_without_recent_move_proof"
    assert "try the 1 next time" in guard_log["raw_text"]
    assert "try the 1" not in guard_log["corrected_text"].lower()
    assert tracker.rate() == 1.0
    playback.push.assert_not_called()


def test_live_claim_guard_emits_salvaged_audio_read_before_harmonic_advice(
    mocker, tmp_path
) -> None:
    """Unsupported key advice should not erase the grounded AI audio read before it."""
    registry = EvidenceRegistry()
    registry.write("ev", "PHRASE", 176.5)
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = True
    state.audible_deck = "A"
    state.audible_track = None
    state.audible_track_confidence = 0.0
    state.recent_moves = []
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "The kick fell right back into that hollow [ev:PHRASE@176.5] rhythm. ",
                "Since the sub is holding so much weight, keep the next blend strictly ",
                "in key to prevent the low end from clashing.",
            ]
        )
    )

    agent.set_next_event(
        Event(type="PHASE", state=state, extra={"prev_phase": "drop", "new_phase": "groove"})
    )
    chunks = _drive(agent)

    assert chunks == ["The kick fell right back into that hollow rhythm."]
    kinds = [kind for kind, _ in recorder.events]
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "emit_corrected"
    assert guard_log["policy"] == "harmonic_claim_not_grounded"
    assert "strictly in key" in guard_log["raw_text"]
    assert "strictly in key" not in guard_log["corrected_text"].lower()
    assert "ai_text" in kinds
    assert next(fields for kind, fields in recorder.events if kind == "ai_text")["text"] == (
        "The kick fell right back into that hollow rhythm."
    )
    assert "citation_strip" not in kinds
    assert tracker.rate() == 0.0
    playback.push.assert_not_called()


def test_live_claim_guard_blocks_mixer_claim_surviving_harmonic_salvage(
    mocker, tmp_path
) -> None:
    """A stripped harmonic clause must not let a fake mixer claim reach the mouth."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.controller_connected = True
    state.audible_deck = "mix"
    state.deck_a = {"vol": 0, "eq_low": 81, "eq_mid": 73, "eq_hi": 73, "filter": 64}
    state.deck_b = {"vol": 127, "eq_low": 78, "eq_mid": 83, "eq_hi": 89, "filter": 60}
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "You just killed the lows on deck B and brought it under the incoming track. ",
                "Keep the next blend strictly in key so the breakdown lands clean.",
            ]
        )
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    chunks = _drive(agent)

    assert chunks == []
    kinds = [kind for kind, _ in recorder.events]
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "strip"
    assert guard_log["policy"] == "mixer_contradiction"
    assert "killed the lows" in guard_log["raw_text"].lower()
    assert "killed the lows" not in guard_log["corrected_text"].lower()
    assert "strictly in key" not in guard_log["corrected_text"].lower()
    assert "ai_text" not in kinds
    assert "citation_strip" not in kinds
    assert tracker.rate() == 1.0
    playback.push.assert_not_called()


def test_live_claim_guard_defers_watch_only_stream_before_correction(mocker, tmp_path) -> None:
    """Watch-only crossfader evidence should not leak the raw streamed head."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, _, _ = _build_agent_wired(mocker, tmp_path, registry)
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Nice ", "handoff, that bridge worked."])
    )

    agent.set_next_event(Event(type="MIX_MOVE", state=state, extra={"moves": ["xfader→A-side"]}))
    chunks = _drive(agent)

    assert chunks == []
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "strip"
    assert guard_log["policy"] == "watch_not_claim"
    assert guard_log["reason"] == "two_deck_move_single_audible"
    assert "Nice handoff" in guard_log["raw_text"]


def test_live_claim_guard_strips_sync_advice_when_move_scope_is_unresolved(
    mocker, tmp_path
) -> None:
    """Recent controller moves are not enough to coach sync without deck proof."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = True
    state.audible_deck = "mix"
    state.controller_connected = True
    state.deck_state = DeckState(decks={})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "That heavy scratching texture was scraping over the kick, ",
                "but the kicks stepped on each other for a half-bar — ",
                "tighten up the sync before pushing both channel faders to the top.",
            ]
        )
    )

    agent.set_next_event(
        Event(
            type="HEARTBEAT",
            state=state,
            extra={
                "moves": [
                    "A_vol up (medium)",
                    "B_vol up (medium)",
                    "B_jog nudge forward",
                ]
            },
        )
    )
    chunks = _drive(agent)

    assert chunks == []
    kinds = [kind for kind, _ in recorder.events]
    assert "ai_text" not in kinds
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "strip"
    assert guard_log["policy"] == "transition_coaching_not_grounded"
    assert guard_log["reason"] == "no_resolved_decks"
    assert "kicks stepped on each other" in guard_log["raw_text"]
    assert "tighten up the sync" not in guard_log["corrected_text"].lower()
    assert tracker.rate() == 1.0
    playback.push.assert_not_called()


def test_licensed_move_effect_still_requires_citation(mocker, tmp_path) -> None:
    """A physics-licensed move effect is still silent without a citation."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, _, _ = _build_agent_wired(mocker, tmp_path, registry)
    state.audible = True
    state.audible_deck = "A"
    state.rms = 0.12
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["Your low cut cleaned the mix."])
    )

    agent.set_next_event(
        Event(type="MIX_MOVE", state=state, extra={"moves": ["A_low: flat→killed"]})
    )
    chunks = _drive(agent)

    assert chunks == []
    kinds = [kind for kind, _ in recorder.events]
    assert "ai_text" not in kinds
    assert "live_claim_guard" not in kinds
    assert "citation_strip" in kinds
    strip_log = next(fields for kind, fields in recorder.events if kind == "citation_strip")
    assert strip_log["reason"] == "no_citations"
    assert "Your low cut cleaned" in strip_log["raw_text"]


def test_live_claim_guard_strips_hidden_source_detail_before_tts(mocker, tmp_path) -> None:
    """Audio can ground vibe; source-level song-part claims need a detector."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = True
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["The vocal opened up and the kick got tighter."])
    )

    agent.set_next_event(
        Event(type="MIX_MOVE", state=state, extra={"moves": ["A_low: flat→killed"]})
    )
    chunks = _drive(agent)

    assert chunks == []
    kinds = [kind for kind, _ in recorder.events]
    assert "ai_text" not in kinds
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["action"] == "strip"
    assert guard_log["policy"] == "audio_source_detail_not_proof"
    assert guard_log["reason"] == "source_detail_without_grounded_detector"
    assert "vocal opened" in guard_log["raw_text"]
    assert "source-level proof" in guard_log["corrected_text"]
    assert tracker.rate() == 1.0
    playback.push.assert_not_called()


def test_live_claim_guard_allows_broad_audio_listener_read_before_tts(mocker, tmp_path) -> None:
    """Broad listener texture is the allowed audio-vibe lane when cited."""
    registry = EvidenceRegistry()
    registry.write("ev", "BAND_SHIFT_LOW", 12.3)
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = True
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["The low end got hollow for a moment [ev:BAND_SHIFT_LOW@12.3]"])
    )

    agent.set_next_event(
        Event(
            type="MIX_MOVE",
            state=state,
            extra={
                "moves": ["A_low: flat→killed"],
                "audio_delta_items": ["low energy fell 50% (strong)"],
            },
        )
    )
    chunks = _drive(agent)

    assert chunks == ["The low end got hollow for a moment "]
    kinds = [kind for kind, _ in recorder.events]
    assert "ai_text" in kinds
    assert next(f for kind, f in recorder.events if kind == "ai_text")["text"] == (
        "The low end got hollow for a moment "
    )
    ai_row = next(f for kind, f in recorder.events if kind == "ai_message")
    assert ai_row["message"] == "The low end got hollow for a moment "
    assert (
        Path(ai_row["artifacts"]["session_response_path"]).read_text(encoding="utf-8")
        == "The low end got hollow for a moment [ev:BAND_SHIFT_LOW@12.3]"
    )
    assert "live_claim_guard" not in kinds
    assert "citation_strip" not in kinds
    assert tracker.rate() == 0.0
    playback.push.assert_not_called()


def test_live_claim_guard_defers_hidden_source_detail_without_move(mocker, tmp_path) -> None:
    """Unsupported source detail should not leak as a speculative head."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = True
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["The vocal ", "opened up."])
    )

    agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
    chunks = _drive(agent)

    assert chunks == []
    guard_log = next(fields for kind, fields in recorder.events if kind == "live_claim_guard")
    assert guard_log["policy"] == "audio_source_detail_not_proof"
    assert "The vocal opened up." in guard_log["raw_text"]
    assert tracker.rate() == 1.0
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

    # Chunks-by-chunks pipe yields the TTS-sanitized clean-prefix response
    # immediately; the citation_failure cancel is what enforces the
    # contract that the fabricated atom never reaches the user. In
    # production the cancel beats TTS synthesis on fast-completion streams
    # (single-chunk Gemini responses settle in ~10ms, TTS first-frame is
    # ~100-200ms).
    assert chunks == ["fake reply"]
    kinds = [k for k, _ in recorder.events]
    # Silence-pad cancel fires (head was speculatively in-flight).
    assert "streaming_cancel" in kinds
    cancel_log = next(f for k, f in recorder.events if k == "streaming_cancel")
    assert cancel_log["reason"] == "citation_failure"
    playback.push.assert_called()
    # citation_strip still logged.
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


def test_manual_silent_trigger_skips_llm_before_tts(mocker, tmp_path) -> None:
    """Manual trigger with no live evidence should become silence before Gemini."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, tracker, playback = _build_agent_wired(
        mocker, tmp_path, registry
    )
    state.audible = False
    state.audible_deck = "none"
    state.audible_track = None
    state.phase = "silent"
    state.rms = 0.0
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: none")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["I'm listening."])
    )

    agent.set_next_event(Event(type="MANUAL", state=state, extra={}))
    chunks = _drive(agent)

    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "manual_silence_short_circuit" in kinds
    assert "llm_invoke" not in kinds
    assert "citation_strip" not in kinds
    assert "streaming_cancel" not in kinds
    assert "ai_text" not in kinds
    gen.aio.models.generate_content_stream.assert_not_called()
    playback.push.assert_not_called()
    assert tracker.rate() == 0.0
    ai_message = next(fields for kind, fields in recorder.events if kind == "ai_message")
    assert ai_message["stop_reason"] == "manual_no_live_evidence"
    assert ai_message["citation"]["action"] == "skip"
    assert ai_message["suppression"] == "manual_no_evidence"
    assert ai_message["extra"]["head_yielded"] is False
    assert ai_message["extra"]["audio_tokens_est"] == 0
    assert ai_message["extra"]["avoided_audio_tokens_est"] > 0


def test_manual_trigger_with_audio_signal_still_reaches_model(mocker, tmp_path) -> None:
    """Broad audio can still be a listener-read signal; only true silence skips."""
    registry = EvidenceRegistry()
    agent, gen, recorder, state, _, _, _ = _build_agent_wired(mocker, tmp_path, registry)
    state.audible = False
    state.audible_deck = "none"
    state.audible_track = None
    state.phase = "unknown"
    state.rms = 0.05
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: raw audio signal")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["<silence/>"])
    )

    agent.set_next_event(Event(type="MANUAL", state=state, extra={}))
    chunks = _drive(agent)

    assert chunks == []
    kinds = [k for k, _ in recorder.events]
    assert "manual_silence_short_circuit" not in kinds
    assert "llm_invoke" in kinds
    assert "silence_short_circuit" in kinds
    gen.aio.models.generate_content_stream.assert_called_once()


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
    # Keep the prose neutral so this isolates the citation linter instead of
    # the live-claim guard for unsupported DJ-action praise.
    fabricated_id = "20260520-2200:999"
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [f"that [ev:KICK_SWAP@45.2] hit had this matching old note [recall:{fabricated_id}]"]
        )
    )

    ev = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev)
    chunks = _drive(agent)

    # The fabricated callback fails the linter; speculative chunks were
    # yielded but the silence-pad cancel kills further audio. The contract
    # (no fabricated callback reaches the user) holds via cancel-before-TTS
    # on fast-completion single-chunk streams.
    assert chunks  # yielded mid-stream
    kinds = [k for k, _ in recorder.events]
    assert "streaming_cancel" in kinds
    assert (
        next(f for k, f in recorder.events if k == "streaming_cancel")["reason"]
        == "citation_failure"
    )
    playback.push.assert_called()
    # citation_strip logged; the fabricated reaction text is captured (silenced).
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


def test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall(mocker, tmp_path) -> None:
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
            [f"remember [recall:{record_a.record_id}] when [ev:KICK_SWAP@45.2] killed it"]
        )
    )
    ev2 = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev2)
    pre_strip_events = len(recorder.events)
    chunks = _drive(agent)

    # The fabricated recall references a prior-turn id; after the
    # unconditional clear it is unregistered-by-construction → STRIP.
    # Chunks-by-chunks pipe yields the response speculatively; the
    # silence-pad cancel from citation_failure enforces the no-fabricated-
    # callback contract.
    assert chunks  # yielded mid-stream
    new_kinds = [k for k, _ in recorder.events[pre_strip_events:]]
    assert "citation_strip" in new_kinds, (
        "turn N+1 must log citation_strip for the fabricated recall"
    )
    assert "streaming_cancel" in new_kinds, (
        "turn N+1 must fire streaming_cancel — head was in-flight when the linter failed"
    )
    strip_log = next(f for k, f in recorder.events[pre_strip_events:] if k == "citation_strip")
    assert f"[recall:{record_a.record_id}]" in strip_log["raw_text"]
    assert ("recall", record_a.record_id) in strip_log["missing"] or [
        "recall",
        record_a.record_id,
    ] in strip_log["missing"], "strip log must name the fabricated prior-turn recall id"
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

    # Speed-pipe yields the clean-prose chunk immediately; citation_strip
    # + silence-pad cancel enforce the "no uncited reply spoken" contract.
    assert chunks == ["that was clean"]
    kinds = [k for k, _ in recorder.events]
    assert "citation_strip" in kinds
    strip_log = next(f for k, f in recorder.events if k == "citation_strip")
    assert strip_log["reason"] == "no_citations"
    assert "streaming_cancel" in kinds
    playback.push.assert_called()
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

    # Chunks ARE yielded under bypass, but citation atoms are still TTS-only
    # stripped so MOSS does not read bracket receipts aloud.
    assert chunks == ["unverified reply"]
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

    # Speed-pipe yields the TTS-clean chunk; silence-pad cancel kills further
    # audio on the citation_failure path regardless of event class.
    assert chunks == ["junk"]
    kinds = [k for k, _ in recorder.events]
    assert "streaming_cancel" in kinds
    playback.push.assert_called()
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
    agent, gen, _recorder, state, _, tracker, _playback = _build_agent_wired(
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
            [f"that [ev:KICK_SWAP@45.2] hit — like [recall:{record_a.record_id}] last set"]
        )
    )
    ev1 = Event(type="TRACK_CHANGE", state=state, extra={})
    agent.set_next_event(ev1)
    chunks_n = _drive(agent)

    assert chunks_n, "turn N must emit (chunks non-empty)"
    assert f"[recall:{record_a.record_id}]" not in chunks_n[0], (
        "TTS must not read recall callback atoms aloud"
    )
    assert agent._last_recall_callback_at == 100.0, (
        "turn N must still arm recall cooldown from the grounded visible/logged callback"
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
